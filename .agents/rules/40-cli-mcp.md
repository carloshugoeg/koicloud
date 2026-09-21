---
trigger: glob
globs: apps/cli/**,apps/api/app/mcp/**
description: Convenciones de la CLI y del servidor MCP (superficies delgadas)
---

Las dos superficies son **adaptadores**: traducen una intención a una llamada HTTP y
formatean la respuesta. Cero reglas de negocio.

- **CLI (`apps/cli`):** cada comando usa el cliente ya escrito (`client.py`, manejo de tokens
  y helper de confirm). No hables con la base de datos, no calcules nada, no guardes estado
  fuera de `~/.config/koicloud/config.json`. Cada comando nuevo copia el patrón del comando
  de referencia (`koicloud pond list`), actualiza `--help` y trae prueba con
  `httpx.MockTransport`. Salida legible por defecto y `-o json` cuando el ticket lo pida.
- **MCP (`apps/api/app/mcp`):** cada tool **≤ 25 líneas** y llama a un comando de
  `app/commands/` o a `propose/confirm`. Nada de lógica dentro de la tool.
- **El montaje de `/mcp`, el gate (slug + password) y las tools mutantes son de W1.**
  W4 implementa solo tools de **lectura**, copiando las dos de referencia.
- **`propose → confirm` es contrato y no se optimiza:** la primera llamada de una mutación
  responde `409 confirmation_required` con `token`, `summary` en español y `expires_at`
  (5 min). La ejecución solo ocurre con `POST /confirm/{token}`
  (`koicloud confirm <token>` · `confirm_action(token)`).
  Muestra el `summary` del backend **tal cual** y espera al humano. Nunca encadenes propose y
  confirm en el mismo turno, nunca fabriques ni adivines un token, nunca «pre-confirmes».
- **Errores:** traduce el `code` del catálogo a un mensaje en español; no imprimas trazas.
- Antes del PR: `make check-cli` (y `make check-api` si tocaste `app/mcp/`).
