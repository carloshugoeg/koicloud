# Interconexiones — flujos concretos

Este documento describe *cómo* interactúan los componentes de KoiCloud en los escenarios que un examinador (o un teammate nuevo) pediría ver primero. Los diagramas están embebidos como Mermaid; las fuentes también existen en [`diagrams/`](./diagrams/).

Los componentes y sus contratos ya están fijados en [`system-architecture.md`](./system-architecture.md) y [`api-surface.md`](./api-surface.md). Aquí solo se muestra la coreografía.

---

## 1. Mapa general de flujos

```mermaid
flowchart LR
    subgraph Users["Usuarios y agentes"]
        U((Cliente humano))
        L((Usuario CLI))
        M((Agente MCP))
        A((Administrador))
        NA((node-agent))
    end
    subgraph Flows["Flujos cubiertos aquí"]
        F1["§2 Crear pond desde Web"]
        F2["§3 Mutar desde CLI con confirmación"]
        F3["§4 Mutar desde MCP con NL"]
        F4["§5 Ciclo job/queue en el data plane"]
        F5["§6 Heartbeat + reconciler mínimo"]
        F6["§7 Consola SQL desde Web/CLI/MCP"]
        F7["§8 Respaldo diario + restore"]
        F8["§9 Medición → uso mensual"]
        F9["§10 Admin: suspender usuario"]
        F10["§11 Deploy en el VPS"]
    end
    U --> F1
    L --> F2
    M --> F3
    NA --> F4
    NA --> F5
    U --> F6
    L --> F6
    M --> F6
    NA --> F7
    NA --> F8
    A --> F9
```

Cada sección siguiente entrega el diagrama de secuencia y la lista de artefactos que cambian (registros SQL, archivos, jobs).

---

## 2. Crear pond desde la Web

**Actores:** Cliente humano, API, `commands.create_pond`, BD interna, node-agent, Docker.

```mermaid
sequenceDiagram
    autonumber
    actor U as Cliente (Web)
    participant SPA as SPA React
    participant API as API FastAPI
    participant CMD as commands.create_pond
    participant DB as PostgreSQL interno
    participant NA as node-agent
    participant D as Docker

    U->>SPA: llena "Crear pond" (name)
    SPA->>API: POST /api/v1/ponds {name}<br/>Authorization: Bearer JWT<br/>Idempotency-Key: <ui-uuid>
    API->>CMD: create_pond(ctx=user, name)
    CMD->>DB: SELECT suscripción activa · cuota del plan
    CMD->>DB: SELECT nodes.next_free_port()
    CMD->>DB: INSERT ponds(desired=running)<br/>INSERT pond_status(observed=pending)<br/>INSERT jobs(create_pond, queued)
    CMD-->>API: {pond_id, job_id, status=provisioning}
    API-->>SPA: 202 Accepted · body con pond
    SPA-->>U: muestra "Aprovisionando…" y refresca cada 3 s

    NA->>API: POST /internal/v1/jobs/claim<br/>X-Node-Token
    API->>DB: SELECT … FOR UPDATE SKIP LOCKED<br/>UPDATE jobs SET status=running
    API-->>NA: payload create_pond {pond_id, port, mem, cpu, password}
    NA->>D: docker run postgres:16-alpine<br/>-p host_port:5432 --memory --cpus<br/>--name koi-pond-<short> --restart=no<br/>-e POSTGRES_PASSWORD=<random>
    D-->>NA: contenedor arriba
    NA->>NA: espera pg_isready (≤ 60 s)
    NA->>API: POST /internal/v1/jobs/{id}/complete {succeeded, host, port}
    API->>DB: UPDATE jobs succeeded<br/>UPDATE pond_status.observed=running · last_seen_at=now()

    U->>SPA: click "Ver conexión"
    SPA->>API: GET /api/v1/ponds/{id}/connection
    API-->>SPA: {host, port, user=koi, password, uri}
    SPA-->>U: muestra URI copiable
```

**Cambios de estado esperados:**

| Momento | `ponds.desired_state` | `pond_status.observed_state` | `jobs(create_pond).status` |
|---------|------------------------|-------------------------------|-----------------------------|
| Post-INSERT | `running` | `pending` | `queued` |
| Post-claim | `running` | `pending` | `running` |
| Post-complete | `running` | `running` | `succeeded` |

**Errores clásicos:**

- `plan_required` (401 no; **409 conflict**): usuario sin suscripción activa.
- `quota_exceeded` (409): supera `max_ponds` del plan.
- `node_unavailable` (503): sin nodo `alive` para hospedar. En un solo nodo, ocurre si el node-agent no envió heartbeat en > 60 s.

---

## 3. CLI: mutación con doble confirmación

**Escenario:** el usuario quiere eliminar `inventario-mvp` desde su terminal.

```mermaid
sequenceDiagram
    autonumber
    actor L as Usuario CLI
    participant CLI as koicloud CLI
    participant API as API FastAPI
    participant CONF as commands.propose_action
    participant CMD as commands.delete_pond
    participant DB as PostgreSQL interno

    L->>CLI: koicloud pond delete inventario-mvp
    CLI->>API: DELETE /api/v1/ponds/by-name/inventario-mvp<br/>Authorization: Bearer JWT<br/>X-KOI-Surface: cli
    API->>CONF: propose(actor=user, action=delete_pond, target=pond_id)
    CONF->>DB: INSERT pending_confirmations<br/>(token_hash, action, payload, expires_at=+5m, user_id)
    CONF-->>API: {confirmation_token, summary}
    API-->>CLI: 409 confirmation_required<br/>{token, summary, expires_at}
    CLI-->>L: imprime resumen humano<br/>"Se eliminará inventario-mvp (respaldo previo). Confirmá con:<br/>  koicloud confirm <token>"

    L->>CLI: koicloud confirm <token>
    CLI->>API: POST /api/v1/confirm/{token}
    API->>CONF: consume(token) → payload
    CONF->>CMD: delete_pond(ctx=user, pond_id)
    CMD->>DB: UPDATE ponds SET desired_state='deleted'<br/>INSERT jobs(backup_pond kind=pre_delete)<br/>INSERT jobs(delete_pond) depende del anterior
    CMD-->>API: {pond_id, status=deleting, jobs=[…]}
    API-->>CLI: 202 Accepted
    CLI-->>L: "Eliminación encolada"
```

**Notas:**

- El header `X-KOI-Surface: cli` (opcional) fuerza el modo confirmar; sin él, la API detecta mutación y siempre exige confirm salvo cuando el request incluye `X-KOI-Confirm-Token: <token>` directamente en un solo paso (útil para scripts).
- `koicloud confirm <token>` es un comando genérico; funciona para cualquier acción propuesta.
- Alternativa scriptable: `koicloud pond delete inventario-mvp --yes` que dispara el propose y consume el token en la misma sesión (dos requests HTTP, un solo comando).

---

## 4. MCP: NL → tools → confirm

**Escenario:** en Claude Desktop, el usuario escribe “dame un pond nuevo llamado `inventario-demo`”.

```mermaid
sequenceDiagram
    autonumber
    actor Chat as Claude/Cursor chat
    participant MCP as FastMCP (/mcp)
    participant API as API FastAPI
    participant CONF as commands.propose_action
    participant CMD as commands.create_pond
    participant DB as PostgreSQL interno

    Chat->>MCP: prompt: "dame un pond nuevo llamado inventario-demo"
    Note over Chat,MCP: el gate URL+password ya validó la sesión MCP
    Chat->>MCP: tool_call create_pond {name: "inventario-demo"}
    MCP->>API: internal call: commands.propose_action(actor=user via agent, action=create_pond, payload={name})
    API->>CONF: propose(...)
    CONF->>DB: INSERT pending_confirmations
    CONF-->>API: {token, summary}
    API-->>MCP: {status:"confirmation_required", token, summary}
    MCP-->>Chat: respuesta: "Voy a crear el pond inventario-demo (plan micro). Necesito que confirmes con confirm_action(token=…)"

    Chat->>MCP: tool_call confirm_action {token}
    MCP->>API: internal call: commands.confirm(token)
    API->>CONF: consume(token) → payload
    CONF->>CMD: create_pond(ctx, payload)
    CMD->>DB: INSERT ponds + status + jobs
    CMD-->>API: {pond_id, job_id, status=provisioning}
    API-->>MCP: {status:"queued", pond:{id, status:"provisioning"}}
    MCP-->>Chat: respuesta: "OK, encolado. Pod id abc123. Chequea con get_pond({name:'inventario-demo'})"
```

**Reglas de diseño MCP:**

- Toda tool mutante devuelve `{status:"confirmation_required", token, summary}` en su primera invocación; el LLM debe leer el `summary` y decidir si presenta el resumen al humano.
- El **prompt sistema** que se envía al LLM cliente (definido en el server MCP) le explica que:
  1. Nunca invente el token.
  2. Muestre el `summary` al humano antes de sugerir `confirm_action`.
  3. Trate `read_only=true` en tools como `list_ponds` y `run_sql (SELECT)` para no pedir confirmación innecesaria.
- El fallback determinista (§7 de [`risks-and-demo-plan.md`](./risks-and-demo-plan.md)) reproduce esta conversación con un cliente MCP local sin modelo.

---

## 5. Ciclo job/queue en el data plane

Vista general del bucle que sostiene toda operación con contenedores.

```mermaid
sequenceDiagram
    autonumber
    participant W as Worker (scheduler)
    participant DB as PostgreSQL interno
    participant NA as node-agent
    participant D as Docker
    participant CMD as commands.*

    Note over CMD: alguien insertó un job (queued)
    NA->>API: POST /internal/v1/jobs/claim<br/>X-Node-Token
    API->>DB: SELECT … FROM jobs<br/>WHERE status='queued' AND node_id in (mine, null)<br/>ORDER BY created_at LIMIT 1<br/>FOR UPDATE SKIP LOCKED
    API->>DB: UPDATE jobs SET status='running', claimed_at=now()
    API-->>NA: payload job
    NA->>D: handler.execute(payload)
    alt éxito
        NA->>API: POST /internal/v1/jobs/{id}/complete {succeeded, result}
        API->>DB: UPDATE jobs succeeded · UPDATE pond_status observed_state
    else fallo
        NA->>API: POST /internal/v1/jobs/{id}/complete {failed, error}
        API->>DB: UPDATE jobs failed · attempts+=1<br/>pond_status.last_error=<msg>
        API->>DB: (worker/reconciler) reencola si desired ≠ observed<br/>y attempts < 3
    end

    W->>DB: cada 30 s: SELECT jobs con status='running' AND claimed_at < now()-2m<br/>→ marca 'lost' → attempts+=1 → reencola
```

**Invariantes:**

- Un pond tiene a lo sumo **un job activo** (`queued` + `running`). Se hace cumplir con:
  ```sql
  CREATE UNIQUE INDEX jobs_one_active
    ON jobs (pond_id) WHERE status IN ('queued','running');
  ```
- `attempts` topa en 3; después el job queda `failed` y el reconciler no lo reintenta hasta intervención humana (`POST /api/v1/ponds/{id}/retry`).
- El scheduler diario **crea** jobs (respaldos, cierres de facturación); nunca los ejecuta.

---

## 6. Heartbeat + reconciler mínimo

```mermaid
sequenceDiagram
    autonumber
    participant NA as node-agent
    participant API as API FastAPI
    participant DB as PostgreSQL interno
    participant W as Worker (reconciler)

    loop cada 15 s
        NA->>API: POST /internal/v1/heartbeat<br/>{containers: [{name, state, uptime}], samples:[…]}
        API->>DB: UPDATE nodes SET last_seen_at=now()
        API->>DB: UPDATE pond_status SET observed_state=..., last_seen_at=now() por cada koi-pond-*
    end

    loop cada 30 s
        W->>DB: SELECT ponds.desired_state, pond_status.observed_state<br/>WHERE desired ≠ observed AND no hay job activo
        alt caso remediable
            W->>DB: INSERT jobs(<corrección>)
        else
            W->>DB: no-op
        end
        W->>DB: mata jobs zombis (running > 2 min sin claim reciente)
    end
```

**Alcance real del reconciler:**

- **Sí hace:** reintenta `create_pond` si el node-agent muere durante el arranque; reencola `start_pond` si el observado quedó `stopped` con `desired=running`; libera jobs `lost`.
- **No hace:** simular caos, matar y revivir automáticamente contenedores por gracia, medir uptime público, ni presumir SLA de recuperación. La demo no muestra `docker kill` como feature.

---

## 7. Consola SQL desde Web, CLI y MCP

**Camino común:** todos pasan por `commands.run_sql(ctx, pond_id, query, mode)`.

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario (Web/CLI/MCP)
    participant CLIENT as Adaptador (SPA / CLI / tool MCP)
    participant API as API FastAPI
    participant CMD as commands.run_sql
    participant PG as PostgreSQL del pond
    participant DB as PostgreSQL interno

    U->>CLIENT: escribe SELECT o UPDATE
    alt lectura
        CLIENT->>API: POST /api/v1/ponds/{id}/sql {query, mode:"read"}
    else escritura
        CLIENT->>API: POST /api/v1/ponds/{id}/sql {query, mode:"write"}<br/>(desde CLI/MCP → primero propose → confirm)
    end
    API->>CMD: run_sql(ctx, pond_id, query, mode)
    CMD->>DB: SELECT connection info (uri desencriptada)
    CMD->>PG: BEGIN;<br/>SET statement_timeout=10s;<br/>alt mode==read: SET TRANSACTION READ ONLY end;<br/>execute(query)
    PG-->>CMD: filas / row_count
    CMD->>PG: COMMIT o ROLLBACK
    CMD->>DB: INSERT sql_history (user, pond, query truncada, duration, rows, mode)
    CMD-->>API: {columns, rows[≤1000], row_count, duration_ms}
    API-->>CLIENT: respuesta
    CLIENT-->>U: tabla + duración
```

**Reglas:**

- **Web:** SELECT y UPDATE se muestran igual, pero para UPDATE la Web pide una confirmación local (modal “escribe el nombre del pond”). No usa `pending_confirmations` porque el usuario está en el navegador y el dueño de la sesión ya es él.
- **CLI y MCP:** cualquier query `mode="write"` **exige** `pending_confirmations` en dos pasos. El detector de modo va en la CLI/MCP (parse ligero) y también en el backend (defensa en profundidad: si un cliente jura “read” y la query es un `DELETE`, la API lo rechaza).
- **Conexión efímera:** `asyncpg.connect()` por consulta; sin pool persistente hacia ponds (evita contaminación de sesión entre requests).
- **Tope de filas:** el resultado se trunca a 1000 filas y se marca `truncated=true` en la respuesta.

---

## 8. Respaldo diario + restore

```mermaid
sequenceDiagram
    autonumber
    participant SCH as Worker (scheduler diario 02:00 local)
    participant DB as PostgreSQL interno
    participant NA as node-agent
    participant PG as PostgreSQL del pond
    participant FS as /var/lib/koicloud/backups
    actor U as Cliente (opcional)
    participant CMD as commands.restore_backup

    loop por cada pond activo
        SCH->>DB: INSERT jobs(backup_pond kind=daily, pond_id)
    end

    NA->>API: claim → payload backup_pond
    NA->>PG: pg_dump -Fc -f <tmp>
    NA->>FS: mv <tmp> /backups/<pond>/YYYYMMDD.dump
    NA->>API: complete succeeded {path, size}
    API->>DB: INSERT backups (pond_id, kind=daily, path, size, sha256)

    Note over U,CMD: Restore bajo demanda
    U->>API: POST /api/v1/ponds/{id}/restore {backup_id}<br/>(Web: modal · CLI/MCP: propose+confirm)
    API->>CMD: restore_backup(ctx, backup_id)
    CMD->>DB: INSERT jobs(restore_pond kind=on_demand, backup_id)
    NA->>API: claim → payload restore_pond
    NA->>PG: DROP SCHEMA app CASCADE;<br/>pg_restore -c -d app <backup.dump>
    NA->>API: complete succeeded
    API->>DB: UPDATE ponds.last_restore_at
```

**Notas:**

- Backups viven en disco local del VPS con retención definida (30 días para daily, ilimitado para `pre_delete` hasta compactar manualmente).
- El drop + restore borra datos actuales; en Web se pide confirmación tipando el nombre del pond, en CLI/MCP se aplica `pending_confirmations`.
- `sha256` del dump se registra al completar para auditoría mínima.

---

## 9. Medición → uso mensual

```mermaid
sequenceDiagram
    autonumber
    participant NA as node-agent (sampler)
    participant API as API FastAPI
    participant DB as PostgreSQL interno
    participant SCH as Worker (nocturno)
    actor U as Cliente

    loop cada 5 min por pond
        NA->>API: POST /internal/v1/samples<br/>{pond_id, size_bytes, container_state}
        API->>DB: INSERT pond_samples
    end

    Note over SCH,DB: 00:15 local
    SCH->>DB: agrega pond_samples del día por pond<br/>→ INSERT usage_daily (instance_hours, storage_gb_hours)

    U->>API: GET /api/v1/usage?month=YYYY-MM
    API-->>U: resumen: por pond y total
```

**Precisiones:**

- `instance_hours` se calcula como suma de intervalos en que `container_state = running`. Si el agente pierde muestras (caído), la ventana perdida se toma como `running` (asunción documentada) para no penalizar al usuario por fallos nuestros.
- `storage_gb_hours` es el promedio de `size_bytes` en el día × 24h. Es una estimación, no una métrica de billing real.
- No se factura en el semestre; la vista se muestra como demostración.

---

## 10. Admin: suspender usuario

```mermaid
sequenceDiagram
    autonumber
    actor A as Administrador
    participant SPA as Web /admin
    participant API as API FastAPI
    participant CMD as commands.suspend_user
    participant DB as PostgreSQL interno

    A->>SPA: click "Suspender" en un usuario
    SPA->>SPA: modal "escribe SUSPENDER para confirmar"
    SPA->>API: POST /api/v1/admin/users/{id}/suspend<br/>Authorization: Bearer JWT (rol admin)
    API->>CMD: suspend_user(ctx=admin, user_id, reason)
    CMD->>DB: UPDATE users SET status='suspended'
    CMD->>DB: DELETE FROM refresh_tokens WHERE user_id=…
    CMD->>DB: INSERT audit_events (actor=admin, target=user, action=suspend)
    CMD-->>API: {user_id, status:'suspended'}
    API-->>SPA: 200 OK
    SPA-->>A: notifica "Usuario suspendido"
```

**Efecto:**

- El usuario pierde sesión inmediata; próximo login recibe `403 account_suspended`.
- Sus ponds **no** se eliminan (evita destrucción irreversible por error de admin); el reconciler no los toca. El pond queda accesible por su URI pero no puede aprovisionar más.

---

## 11. Deploy en el VPS

```mermaid
sequenceDiagram
    autonumber
    participant GH as GitHub Actions (deploy.yml)
    participant VPS as VPS Linux
    participant COMP as docker compose
    participant SYS as systemd
    participant API as api container

    Note over GH: push a main con cambios en apps/**, packages/contracts/**, infra/**
    GH->>VPS: ssh + infra/scripts/deploy.sh
    VPS->>VPS: git fetch --ff-only origin main
    VPS->>COMP: docker compose -f infra/docker-compose.prod.yml pull
    VPS->>COMP: docker compose up -d --build api worker caddy
    VPS->>API: alembic upgrade head
    VPS->>VPS: rsync dist/ /srv/koicloud/web/
    alt cambió apps/node-agent
        VPS->>SYS: systemctl restart koicloud-agent
    end
    GH->>API: curl https://.../health hasta 200 (60 s)
```

**Reglas operativas:**

- El deploy es idempotente: si el mismo commit se despliega dos veces, no rompe nada.
- `alembic upgrade head` **no** se revierte automáticamente. Si una migración es incompatible, el deploy queda en `500` en `/health` y el equipo interviene con `alembic downgrade` manual guiado por runbook.
- El reinicio del node-agent es raro; solo cuando cambió su código. El systemd unit ya trae `Restart=on-failure` con `RestartSec=5`.

---

## 12. Vista consolidada: quién habla con quién

| Origen | Destino | Canal | Auth | Frecuencia típica |
|--------|---------|-------|------|-------------------|
| Web SPA | API `/api/v1/*` | HTTPS JSON | JWT | por interacción |
| CLI | API `/api/v1/*` | HTTPS JSON | JWT | por comando |
| IDE MCP | API `/mcp` | Streamable HTTP MCP | URL slug + password (Basic) | por conversación |
| API/MCP | commands | in-process | — | cada request |
| commands | modules | in-process | — | cada request |
| commands | pond `:15xxx` | asyncpg | password del pond | por consulta SQL |
| Worker | modules | in-process | — | cada 15/30/60 s / diario |
| node-agent | API `/internal/v1/*` | HTTPS (loopback) | X-Node-Token | 15 s heartbeat · on-demand claim/complete |
| Deploy runner | VPS | SSH | llave del secreto `VPS_SSH_KEY` | por deploy |

---

## 13. Puntos donde el sistema puede fallar (y qué mostrar)

Detalle completo en [`risks-and-demo-plan.md`](./risks-and-demo-plan.md). Aquí solo el resumen operativo:

| Falla | Efecto visible | Mitigación en demo |
|-------|----------------|-------------------|
| node-agent caído | `pond_status.last_seen_at` viejo → `unhealthy`; nuevos jobs quedan `queued` | En demo, `AGENT_MODE=mock` en local o video de respaldo |
| LLM del MCP no responde | El chat se cuelga | Fallback: `scripts/demo-mcp-replay.py` reproduce la conversación con tools locales |
| VPS caído | Web no carga | Video de respaldo grabado en el ensayo final; readme del guion cita el minuto |
| Docker sin espacio | `create_pond` falla con `disk_full` | Runbook `docs/runbooks/free-disk.md`; `df -h` en el guion |
| CI rojo justo antes de exposición | Deploy bloqueado | Prohibido deployar en verde-parcial: se usa el último deploy verde |

Todos estos escenarios están cubiertos por el guion o por un fallback grabado — nunca se improvisa.
