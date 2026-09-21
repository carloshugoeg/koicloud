# Riesgos, modos de falla y plan de demo

Este documento reúne los modos en que KoiCloud puede fallar durante el semestre y la demo final, con la mitigación concreta. También describe el guion de la demo y el fallback determinista que reemplaza al LLM si éste se cae. Finalmente enumera qué se recorta si el semestre se atrasa.

---

## 1. Matriz de riesgos

| # | Riesgo | Probabilidad | Impacto | Detección | Mitigación |
|---|--------|--------------|---------|-----------|------------|
| R-01 | Coordinación entre cuatro personas | Alta | Alto | Retrasos en tickets críticos, PRs sin merge | Ownership por CODEOWNERS; workstreams paralelos con mocks/stubs desde Fase 0; escalamiento automático por bloqueo > 24 h |
| R-02 | Sobreingeniería residual (auto-heal, spend caps, sandbox público) | Media | Alto | PRs que intentan meter fuera de alcance | Revisor automático + `AGENTS.md` §4-14 + `vision-and-constraints.md` |
| R-03 | VPS caído el día de la demo | Baja | Muy alto | `GET /health` responde 5xx o timeout | (a) Video de respaldo grabado en el ensayo final; (b) modo `AGENT_MODE=mock` en laptop del expositor con el mismo flujo |
| R-04 | LLM del MCP falla o corta | Media | Alto | El chat de Claude/Cursor no responde en 15 s | Script `scripts/demo-mcp-replay.py` reproduce la conversación happy-path invocando tools directamente. Ver §4 |
| R-05 | Red inestable en el aula (WiFi de universidad) | Media | Medio | Latencias visibles, timeouts | Presentar desde tethering móvil como fallback; tener el video de respaldo |
| R-06 | Disco lleno en el VPS (backups + logs) | Media | Medio | `disk_full` en logs; `df -h` <10 % libre | Runbook `docs/runbooks/free-disk.md`; retención 30 d dailies + purge manual pre-demo |
| R-07 | Docker deja contenedores zombis | Baja | Medio | `koi-pond-*` en `Exited` con datos huérfanos | Runbook `docs/runbooks/reap-ponds.md`; script `scripts/cleanup-orphans.sh` |
| R-08 | El servidor Postgres interno pierde datos por error de migración | Baja | Muy alto | Deploy falla, `/ready` responde 503 | `alembic downgrade` guiado por runbook; respaldo diario de la base interna |
| R-09 | `GH_TOKEN` expira / rate-limit de GitHub | Baja | Bajo | `gh` responde 401/403 | Fallback: Mac worker autenticado como `carloshugoeg`. Ver `../github-publish.md` |
| R-10 | Revisor automático (Anthropic o Bugbot) cae | Baja | Bajo | Job `ai-review` no publica veredicto | Se marca el PR como “manual review” y W1 revisa a mano; el PR no se fusiona hasta que un humano apruebe |
| R-11 | El servidor MCP presenta bugs con montaje in-process | Media | Medio | Endpoints `/mcp` responden 500 en dev | Plan B: correr FastMCP como proceso separado detrás de Caddy `/mcp`; ADR-013 del harness previo documenta el cambio |
| R-12 | Fricción con `SET TRANSACTION READ ONLY` en pond con extensiones raras | Baja | Bajo | `run_sql` mode=read falla en ciertos casos | Restringir la consola a Postgres base sin extensiones (fuera de alcance de todos modos) |
| R-13 | Falta de tiempo de un integrante | Media | Alto | Semana con < 20 % de PRs mergeados | Recorte guiado por §6; W1 redistribuye tickets |
| R-14 | Confusión sobre alcance con el catedrático | Baja | Medio | Feedback pide algo fuera de alcance | Referirse a `alcance.md` y `vision-and-constraints.md`; abrir CCR si el equipo decide extender |
| R-15 | Costos de LLM en revisor automático se disparan | Baja | Bajo | Bill de Anthropic > presupuesto | Cambiar a Cursor Bugbot (incluido en el plan Ultra) o a revisión manual |

---

## 2. Modos de falla del runtime — resumen operativo

| Componente | Falla | Efecto | Estrategia |
|------------|-------|--------|------------|
| API | proceso muere | 502 en `/api`; MCP también fuera (comparten proceso) | `docker compose restart api`; systemd unit de Docker garantiza restart |
| Worker | proceso muere | Respaldos no se programan; reconciler no corre | `docker compose restart worker` |
| node-agent | systemd unit stopped | `pond_status.last_seen_at` viejo; nuevos jobs quedan `queued` | `systemctl start koicloud-agent`; runbook `docs/runbooks/restart-agent.md` |
| BD interna | crash | Toda API en 5xx | `docker compose restart db`; si corrupción, restaurar del dump diario |
| Pond | contenedor `Exited` | Cliente pierde conexión | Reconciler mínimo reencola `start_pond` si `desired=running` |
| Caddy | crash o cert vencido | Sin TLS o 502 | `docker compose restart caddy`; runbook `docs/runbooks/caddy.md` |
| Correo (Resend) | API fuera / cuota | Verificación de email falla | Endpoint sigue respondiendo 200; email cae a `EMAIL_PROVIDER=console` y se muestra en logs. Runbook para retry |
| Deploy pipeline | falla en `alembic upgrade` | Deploy queda a medias | `/ready` responde 503; equipo corre `alembic downgrade` según runbook |

---

## 3. Guion de la demo final (feliz-path)

Duración objetivo: **12 minutos** de demo + 3 min de preguntas. Se ensaya tres veces antes de exposición.

### 3.1 Pre-demo (5 min antes)

1. Verificar `curl -s https://<KOICLOUD_DOMAIN>/api/v1/health` → 200.
2. Verificar `docker ps` en el VPS: `api`, `worker`, `db`, `caddy`, `koi-pond-demo01` corriendo.
3. Tener abierto Claude Desktop con el MCP server configurado (URL slug + password del usuario demo).
4. Tener abierto un terminal con `koicloud` CLI y otro con `psql` listo.
5. Tener el video de respaldo en `~/demo-koicloud-backup.mp4` y una terminal con `AGENT_MODE=mock` corriendo `docker compose up` localmente.

### 3.2 Guion (12 min)

| Minuto | Acción | Respuesta esperada |
|--------|--------|--------------------|
| 0:00 | Introducción: “KoiCloud, DBaaS académico. Tres superficies sobre una API” | Slide 1: diagrama de componentes |
| 1:00 | En la Web, registrarse con `demo@equipokoicloud.dev` (o login si ya existe) | Redirect a dashboard |
| 2:00 | Contratar plan Micro con pago simulado | Ver factura + IVA |
| 3:00 | Crear pond `inventario-demo` | Estado `provisioning` → `running` en ~30 s |
| 4:00 | Ver conexión → copiar URI → `psql "<uri>" -c "CREATE TABLE items(id serial, nombre text);"` | Devuelve `CREATE TABLE` |
| 5:00 | En consola SQL web: `SELECT * FROM items;` | 0 filas + duración |
| 6:00 | Desde CLI: `koicloud pond list` → tabla; `koicloud pond delete inventario-demo` | `confirmation_required` + resumen |
| 7:00 | `koicloud confirm <token>` | `202 deleting` |
| 7:30 | Recrear con `koicloud pond create inventario-demo --yes-token` (paso propose+confirm inline) | Provisiona de nuevo |
| 8:00 | Cambiar a Claude Desktop; “dame un pond nuevo llamado inventario-natural” | Claude propone tool_call → summary |
| 8:30 | “Confírmalo” → Claude invoca `confirm_action(token)` | Pond creado |
| 9:30 | En Claude: “corré `SELECT now()` contra inventario-natural” | run_sql read → devuelve timestamp |
| 10:30 | En Claude: “eliminá inventario-natural con backup previo” → propose → confirm | Delete encolado |
| 11:00 | Cerrar mostrando: mismo backend, tres canales, doble confirmación | Slide de cierre |

### 3.3 Frases prohibidas durante la demo

- “Auto-curación garantizada” (no se ofrece).
- “Nuestro OAuth 2.1” (no existe).
- “Producción-ready” (es académico).
- “SLA” (no hay).
- “Sandbox público” (no hay).

En su lugar: “demostración académica”, “gate mínima para el aula”, “V2 fuera de alcance”, “showcase de tres superficies sobre una API”.

---

## 4. Fallback determinista (LLM no responde o red mala)

`scripts/demo-mcp-replay.py` (W4) es un CLI local que emula la conversación del §3.2 minutos 8:00-10:30 sin necesitar un LLM. Su diseño:

1. Se conecta al endpoint `/mcp` con la misma URL slug + password (o al proceso local con `AGENT_MODE=mock`).
2. Ejecuta secuencia hardcodeada:
   - `create_pond({name:"inventario-natural"})` → recibe token → imprime summary.
   - `confirm_action({token})` → imprime respuesta.
   - `run_sql({pond_name:"inventario-natural", query:"SELECT now()", mode:"read"})` → imprime tabla.
   - `delete_pond({name:"inventario-natural"})` → summary.
   - `confirm_action({token})` → imprime respuesta.
3. Entre paso y paso, imprime a stdout como si un chat mostrara el intercambio (con `--simulate-chat`).

**Regla:** el fallback se ensaya en cada uno de los tres ensayos previos, no solo se supone que funciona. Si el LLM cae en la demo real:

1. El presentador dice: “vamos a mostrar el mismo flujo con el cliente local para no depender de la red”.
2. Ejecuta `python scripts/demo-mcp-replay.py --simulate-chat`.
3. Enseña que la respuesta es idéntica a la que hubiera dado Claude/Cursor.

El punto pedagógico se mantiene: **la API es la misma, el LLM solo es un cliente**.

---

## 5. Video de respaldo

Se graba una toma completa del guion en el último ensayo, en el mismo VPS que se usará en la demo. Se guarda en:

- Laptop del expositor: `~/demo-koicloud-backup.mp4`.
- Cuenta compartida del equipo (Drive/Nextcloud).
- Store del proyecto (`media/demo-final-backup.mp4` cuando exista).

Si tanto VPS como red fallan, el expositor reproduce el video y comenta cada segmento en vivo.

---

## 6. Plan de recorte (si el semestre se atrasa)

Orden estricto para recortar. Detalle en [`feature-breakdown.md`](./feature-breakdown.md) §8; aquí la disciplina:

1. **Semana antes del avance 80 %:** si `run_sql` en MCP no funciona bien, quitarlo de MCP (queda en Web + CLI). Ajustar guion.
2. **Semana antes del avance 80 %:** si `restore_backup` en CLI/MCP no funciona, quitarlo de esos canales (queda en Web).
3. **Semana antes del avance final:** si la renovación diaria falla en cron, dejarla como acción manual desde admin.
4. **Semana antes del avance final:** si k6 no está listo, sustituir por prueba manual con `ab` documentada.
5. **Últimos 3 días:** si el sandbox público / la vista de uso / la bitácora básica no compilan, quitarlas del guion — nadie las pide.

**Nunca se recorta:**

- Auth completa (E1-01…E1-05).
- Contratar Micro con factura (E2-01, E2-02, E2-03).
- Crear/eliminar pond real (E3-01, E3-04).
- Consola SQL Web read (E5-01).
- CLI mutación con confirm (E9-01, E9-04).
- MCP mutación con confirm (E9-02, E9-04).
- Guion + fallback (E9-06, E9-07).

Si algo del “nunca se recorta” está en riesgo, W1 escala al catedrático **el mismo día**.

---

## 7. Ensayos previos a la demo (calendario)

| Ensayo | Cuándo | Objetivo |
|--------|--------|----------|
| E1 | 7 días antes | Ensayo completo con VPS real; medir tiempos; anotar defectos |
| E2 | 3 días antes | Ensayo con video de respaldo; ensayar fallback MCP; anotar cortes |
| E3 | 1 día antes | Ensayo con red del aula (o simulada); grabar video final |

Cada ensayo produce un ticket `w1/demo-fix-<n>-<slug>` con los defectos encontrados. Ningún ensayo puede tener defectos abiertos en la ruta crítica cuando llega el día de la demo.

---

## 8. Postmortem del semestre (posterior a la entrega)

Después de la entrega final, el equipo escribe:

- `docs/postmortem.md` con: qué funcionó, qué no, qué recortaríamos primero si volviéramos a empezar.
- Actualiza `docs/architecture/vision-and-constraints.md` con lo que aprendimos sobre alcance (para futuros equipos o V2).

No se hacen commits al alcance durante el semestre — el postmortem es la única puerta de aprendizaje formalizado.
