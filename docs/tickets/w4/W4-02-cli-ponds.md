---
id: W4-02
workstream: W4
persona: Diego
estado: abierto
rama: w4-cli-ponds
epica: "E9-01"
sprint: S2
pr:
---

# [W4-02] CLI `pond get/create/connection/delete`

## Qué se ve

Comandos CLI para consultar y mutar ponds sin saltarse el contrato de confirmación. Lo visible es salida humana estable y propuesta destructiva cuando toca mutar.

## Entradas ya decididas (no se cambian)

- Comandos: `pond get`, `pond create`, `pond connection`, `pond delete`.
- API: `GET /ponds/by-name/{name}`, `POST /ponds`, `GET /ponds/{id}/connection`, `DELETE /ponds/{id}`.
- Las mutaciones siempre pasan por `confirmation_required`; no se auto-confirman.
- Create devuelve `202 {pond, job}` y delete resume el backup `pre_delete` antes de borrar.
- El formato `-o json` reutiliza el helper común cuando exista; no se reimplementa por comando.
- Sin sesión: exit `1` y el mensaje de `api-surface.md` §5.

## Criterios de aceptación

1. `pond get` y `pond connection` imprimen campos del contrato sin alias nuevos.
2. `pond create` propone y muestra token/summary sin ejecutar un segundo paso implícito.
3. `pond delete` propone una acción destructiva que menciona el backup previo.
4. Hay pruebas para lookup por nombre, propose feliz y salida JSON cuando el helper común exista.

## No tocar

- `apps/cli/koicloud_cli/client.py` y `config.py` salvo la API pública ya congelada por W1.
- `apps/api/app/commands/**`.
- `apps/node-agent/**`.
- `apps/api/app/mcp/{server.py,gate.py,prompt.py}` y cualquier tool mutante.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes comandos, flags, payloads, tools ni atajos al flujo de confirmación.
- Si el helper común de `-o json` aún no existe, esperá a W4-05 en vez de duplicarlo dentro de este ticket.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.
