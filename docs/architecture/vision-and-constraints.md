# Visión y restricciones

Este documento fija la intención del proyecto, el alcance sellado y las restricciones inamovibles del semestre. Cualquier decisión posterior en el pack debe caber aquí; si no cabe, se cambia esto primero (con acuerdo del equipo) o se descarta la decisión.

---

## 1. Problema real que resolvemos

Un estudiante o desarrollador que necesita PostgreSQL para un proyecto de curso paga o instala servidores que no sabe administrar. Los productos comerciales exigen tarjeta internacional y su tier gratuito caduca rápido. Ejecutar SQL contra esa base requiere otra herramienta más.

**KoiCloud** entrega una experiencia mínima de DBaaS pensada para el aula: alta con correo, catálogo con pago simulado, una instancia PostgreSQL 16 gestionada (un *pond*), consola SQL en el navegador, respaldo diario, y — como *showcase* técnico — la misma capacidad expuesta por **CLI** y por **MCP** para que un IDE con Claude/Cursor pueda operar cuentas y ponds en lenguaje natural, con confirmación en dos pasos.

**Lo que sí demostramos:**

1. Autogestión completa de una instancia Postgres real (crear → conectar → consultar → respaldar → eliminar).
2. Modelo de negocio simulado defendible (planes, pago simulado, factura con IVA desglosado, historial).
3. Una **sola API** de control plane que sostiene tres superficies (Web, CLI, MCP) sin duplicar reglas.
4. Un patrón concreto de **mutaciones seguras desde agentes** (propose → confirmation token → confirm), suficiente para el aula y honesto sobre lo que no cubre.

**Lo que no vendemos como resultado del semestre:**

- Auto-curación como promesa de producto (podemos mostrar un reconciler pero no lo llamamos “self-healing platform”).
- Seguridad completa de agentes (OAuth 2.1, scopes finos, spend caps, auditoría forense, 2FA). Eso es V2.
- Validación empírica de las hipótesis de precio o factura local (requiere usuarios reales pagando).

---

## 2. Alcance sellado (fuente única: `../entrega-2/alcance.md`)

Copia condensada para conveniencia; en caso de discrepancia manda `../entrega-2/alcance.md`.

**Dentro:**

1. Cuentas: registro, verificación de correo, recuperación de contraseña, JWT + refresh; roles Cliente y Administrador.
2. Suscripciones: catálogo Sandbox/Micro/Pro, contratación simulada, historial, renovación, cancelación.
3. Provisioning real de PostgreSQL 16 en Docker (crear, consultar estado, obtener URI, eliminar).
4. Configuración básica al crear: nombre del pond, versión 16, plan heredado.
5. Consola SQL en el navegador (lectura por defecto; escritura con confirmación).
6. Respaldos diarios y restauración bajo demanda (`pg_dump` / `pg_restore`).
7. Vista simple de uso: horas de instancia y almacenamiento.
8. Panel de administración: usuarios, suscripciones, ponds.
9. Arquitectura monolito modular (FastAPI) + node-agent + cola en PostgreSQL; un solo VPS.
10. Web + CLI + MCP como fachadas delgadas sobre la misma API.
11. **Doble confirmación** en mutaciones/destrucciones desde CLI y MCP (propose → token → confirm).
12. **Gate mínima de agente:** URL + password revelable en el panel web (demo de aula).
13. **Demo MCP fiable:** guion happy-path + fallback determinista si el LLM en vivo falla.

**Fuera:**

- IaC declarativa (`cloud.yaml`, `koicloud apply`) como producto.
- Seguridad completa de agentes = **V2** (OAuth 2.1, API keys con scopes, spend caps, auditoría, 2FA).
- Auto-curación garantizada / demo de caos.
- Validación de hipótesis de negocio (precio, NIT).
- Otros motores (MySQL, MongoDB), branching, réplicas, pooler, extensiones.
- Organizaciones / equipos / invitaciones.
- Cobro real, pasarelas, facturación electrónica ante SAT, SLA.
- Alta disponibilidad, multi-nodo, migración de instancias.
- Roles Soporte / Operador; status page pública; sandbox público sin registro.

---

## 3. Restricciones del semestre (inamovibles)

Cualquier decisión que ignore estas restricciones se rechaza sin discusión en revisión.

| # | Restricción | Implicación técnica |
|---|-------------|---------------------|
| R-01 | Cuatro personas del Equipo KoiCloud, cada una con acompañamiento de Cursor Ultra | El repo se parte en **cuatro workstreams** con ownership por CODEOWNERS; no se usan patrones que exijan sincronía diaria (broker distribuido, integraciones entre servicios) |
| R-02 | Un solo VPS Linux con Docker | Nada de Kubernetes, service mesh, secret manager en la nube, brokers externos |
| R-03 | Presupuesto cero para infraestructura extra | Cola en PostgreSQL (`SKIP LOCKED`), correo de desarrollo por consola, TLS con Caddy, backups en disco local del VPS |
| R-04 | El catedrático evaluará la arquitectura contra el conocimiento del equipo | Stack conocido: FastAPI + React + Docker + PostgreSQL. Se descartan Kafka, Kubernetes, gRPC, GraphQL, event sourcing |
| R-05 | La demo final se ensaya tres veces antes de exposición | Todo camino crítico tiene modo `mock` o script determinista de respaldo (LLM offline, VPS caído, red inestable) |
| R-06 | Publicación por `gh` CLI únicamente (nunca GitHub MCP) | `AGENTS.md` prohíbe llamar herramientas de GitHub MCP; `gh` autenticado con `GH_TOKEN` o Mac worker |
| R-07 | Cada commit se atribuye a la **cuenta de GitHub real** de quien hizo el trabajo; el curso evalúa la contribución individual | Cada quien fija `user.name` y `user.email` por repositorio con su propia cuenta (registro en [`../WORKSTREAMS.md`](../WORKSTREAMS.md) §3); no hay identidad de git compartida. «Equipo KoiCloud» es la voz pública en README, PDF y UI, no un autor. `Co-authored-by` solo para humanos reales; los asistentes de IA no se acreditan nunca (sin trailers de Cursor, Antigravity, Gemini ni Claude). Lo verifica el job `authorship` de CI |
| R-08 | No se implementa aunque sobre tiempo lo que la Entrega 2 declaró fuera de alcance | Si sobra tiempo, se refuerza el guion de demo, se cierran deudas técnicas y se pulen manuales — no se abre alcance |

---

## 4. No-goals explícitos (por qué **no** los perseguimos)

Los siguientes son ideas atractivas que otros equipos podrían implementar; nosotros no. La razón por la que no son parte del proyecto está fijada aquí para que ningún agente los proponga a mitad del semestre.

| No-goal | Por qué no |
|---------|-----------|
| “Plataforma agéntica” con OAuth 2.1 y spend caps | Es un producto de seguridad completo; su alcance rompe el semestre. Se marca **V2** y se sustituye por gate + doble confirmación |
| Auto-curación vendida como feature | Requiere pruebas de caos reproducibles y un SLA; ambos exceden la evaluación del curso. Podemos tener reconciler mínimo interno sin llamarlo así |
| Multi-nodo / alta disponibilidad | Fuera del enunciado; añade Kubernetes o coordinación distribuida. La demo cabe en un VPS |
| Facturación real (Stripe/PayPal/SAT) | Requiere cuentas comerciales, KYC y compliance. Pago **simulado** ya cumple el enunciado |
| Múltiples motores (MySQL, MongoDB) | Duplica el data plane (drivers Docker, backups, consola) sin aportar nada al aprendizaje |
| Editor SQL con schema explorer, autocompletado, EXPLAIN | Sobrecarga el frontend; alcance sellado dice “consola SQL básica” |
| Panel público de status con uptime | No lo pide el enunciado; añade otro dominio de datos (incidentes) y otra pantalla |
| Sandbox público sin registro | Puede explorarse si sobra tiempo, pero **no está comprometido**; abre superficie sin auth |

---

## 5. Qué “deslumbra” en la demo (sin fantasía)

La demo final es el momento donde el catedrático decide si la arquitectura vale. Estos tres momentos son los que impresionan sin exagerar lo que hicimos:

### 5.1 Web → pond real en menos de 90 segundos

“Crear pond” en la Web arranca un contenedor PostgreSQL real en el VPS. Se copia la URI y se conecta desde `psql` local. Es la prueba viviente de que **existe un data plane** y no un mock.

### 5.2 CLI mutante con confirmación en dos pasos

Desde una terminal cualquiera: `koicloud pond delete <name>`. El CLI recibe `confirmation_required` + `confirmation_token` + resumen. El estudiante lo confirma con `koicloud confirm <token>`. La API ejecuta. Muestra que el **mismo comando** que hace la Web puede invocarse desde una terminal, pero **no de forma accidental**.

### 5.3 MCP → lenguaje natural con confirmación

Se conecta un IDE (Claude Desktop o Cursor) al servidor MCP de KoiCloud usando URL + password revelados en el panel. El estudiante escribe “dame un pond nuevo llamado `inventario-demo`”. El agente propone la creación; el sistema pide confirmación; el estudiante escribe “confírmalo”. El agente confirma. La demo enseña que **la misma API sostiene tres clientes** sin duplicar reglas ni fingir seguridad de nivel producción.

Si el LLM en vivo falla, el fallback determinista descrito en [`risks-and-demo-plan.md`](./risks-and-demo-plan.md) §Fallback MCP reproduce el mismo flujo con una grabación local.

---

## 6. Postura sobre lo que ganamos y lo que no

- **Ganamos** al mostrar tres superficies sobre una sola API — es una arquitectura defendible que la mayoría de equipos del curso no intenta.
- **Ganamos** al no fingir un producto de seguridad para agentes: declaramos gate mínima, dejamos V2 explícita.
- **No ganamos** intentando llenar el semestre con features que no piden. La calidad del proyecto se juzga por lo que **funciona en la demo** más lo que **está bien documentado**.

Esta postura es el criterio de aceptación del pack completo. Si un documento posterior contradice esta postura, ese documento se corrige.
