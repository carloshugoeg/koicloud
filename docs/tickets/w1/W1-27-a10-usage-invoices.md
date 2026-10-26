---
id: W1-27
workstream: W1
persona: Carlos
estado: en-curso
rama: w1-a10-usage-invoices
epica: "E7-03, E7-04, E9-01, E9-02"
sprint: S4
pr:
depends_on:
---

# [W1-27] A10 — Uso y facturas en web, CLI y MCP

Issue #96 amendment A10 (low). Paridad de uso e historial de facturas en las tres superficies.

## Qué se ve

- Web `/app/uso`: matriz de uso del mes (KPI + desglose por pond desde `GET /usage`) e historial de facturas desde `GET /invoices`, más el papel de la factura del mes seleccionado.
- CLI: `koicloud usage` (ya existe) y `koicloud invoice list` → tabla o `-o json` del historial.
- MCP: tool de lectura `get_usage(month?)` registrada y listada en `/mcp` `read_only_tools`.

## Entradas ya decididas (no se cambian)

- API ya congelada: `GET /usage`, `GET /invoices`, `GET /invoices/{id}`, `GET /invoices/{id}/pdf`.
- Comandos: `app.commands.usage.get_usage`, `app.commands.billing.list_invoices`.
- Shape de uso: `{month, total_instance_hours, total_storage_gb_hours, ponds:[…]}`. Sin serie diaria nueva (haría falta CCR).
- Shape de lista de facturas: `{invoices, next_cursor}` con `InvoiceOut`.
- MCP: patrón de `list_subscriptions` / `get_connection` en `apps/api/app/mcp/tools/`; el *example* de `MCPInfoResponse` ya incluye `get_usage`.
- CLI: patrón de `subscription list` / `usage` en `apps/cli`.
- Web: feature `apps/web/src/features/uso/**`; datos vía hooks existentes; sin editar `schema.d.ts` ni `client.ts`.
- Textos UI en español; sin `dark:`; tokens de `index.css`.

## Criterios de aceptación

1. `GET /mcp` lista `get_usage` en `read_only_tools` y la tool responde el shape de `UsageResponse`.
2. El test que afirmaba la ausencia de `get_usage` queda actualizado (ahora la exige).
3. `koicloud invoice list` llama `GET /invoices` y muestra tabla o JSON; hay prueba MockTransport.
4. `koicloud usage` sigue verde.
5. `/app/uso` muestra historial de facturas (lista) además del papel del mes; estados cargando / vacío / error.
6. Sin cambios de OpenAPI paths/schemas ni regeneración de contratos.
7. Pruebas API/CLI/web relevantes pasan; capturas desktop + 375px de `/app/uso` en el PR.

## No tocar

- `packages/contracts/openapi.json` y `apps/web/src/api/schema.d.ts` (no regenerar).
- Firmas de `app/commands/*`.
- NIT, pricing, suscripciones admin, stop/start de ponds (otros amendments HIGH/LOW).
- Migraciones Alembic.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.
No inventes endpoints, campos, tablas ni códigos de error. Si el comando ya existe, llámalo.

## Referencia

Imitá el PR de MCP lectura ([#86](https://github.com/carloshugoeg/koicloud/pull/86)) y CLI resto ([#84](https://github.com/carloshugoeg/koicloud/pull/84)): misma estructura de archivos y estilo de pruebas.
