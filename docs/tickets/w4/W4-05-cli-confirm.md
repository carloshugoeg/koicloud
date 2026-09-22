---
id: W4-05
workstream: W4
persona: Diego
estado: abierto
rama: w4-cli-confirm
epica: "E9-01"
sprint: S3
pr:
---

# [W4-05] CLI `confirm` / `confirm cancel` y salida `-o json`

## Qué se ve

Capa CLI para consumir o descartar `pending_confirmations`, más el formatter compartido de salida JSON. Lo visible es la ejecución del segundo paso y una salida machine-readable consistente.

## Entradas ya decididas (no se cambian)

- Comandos: `koicloud confirm <token>` y `koicloud confirm cancel <token>`.
- API: `POST /confirm/{token}` y `DELETE /confirm/{token}`.
- La respuesta `409 confirmation_required` ya viene sellada por el backend con `token`, `summary`, `expires_at` y `cli_example`.
- TTL fijo del token: 5 minutos; errores `confirmation_not_found` y `confirmation_expired`.
- Este ticket define el formatter compartido de `-o json` para los demás comandos.

## Criterios de aceptación

1. `confirm` ejecuta la acción pendiente y muestra la respuesta efectiva del backend.
2. `confirm cancel` descarta el token y responde éxito sin mutar más nada.
3. `-o json` devuelve salida estable y machine-readable sin renombrar keys.
4. Errores de token vencido o inexistente salen por el catálogo y con código de salida no cero.

## No tocar

- `apps/cli/koicloud_cli/client.py` y `config.py` salvo la API pública ya congelada por W1.
- `apps/api/app/commands/**`.
- `apps/node-agent/**`.
- `apps/api/app/mcp/{server.py,gate.py,prompt.py}` y cualquier tool mutante.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes comandos, flags, payloads, tools ni atajos al flujo de confirmación.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.
