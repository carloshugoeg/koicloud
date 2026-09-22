---
id: W4-03
workstream: W4
persona: Diego
estado: abierto
rama: w4-cli-sql
epica: "E5-02"
sprint: S3
pr:
---

# [W4-03] CLI `sql run` (lectura y `--write`) e historial

## Qué se ve

Comandos CLI para correr SQL y consultar historial. El resultado visible es tabla legible en modo lectura y propuesta separada cuando se usa `--write`.

## Entradas ya decididas (no se cambian)

- Comandos: `sql run --pond <name> -q "..."` y `sql history --pond <name>`.
- API: `POST /ponds/{id}/sql` y `GET /ponds/{id}/sql/history`.
- El modo por defecto es `read`; `--write` exige confirmación.
- Errores fijos: `sql_readonly_violation` y `sql_timeout`.
- La salida humana y JSON comparte formatter común; no se clona por comando.

## Criterios de aceptación

1. Un `SELECT` imprime columnas, filas y duración de forma legible.
2. `--write` nunca ejecuta inline: primero propone.
3. `sql history` lista consultas recientes con señal de truncamiento cuando corresponda.
4. Hay pruebas para read feliz, propose write y timeout.

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
