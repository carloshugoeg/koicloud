---
id: W4-04
workstream: W4
persona: Diego
estado: abierto
rama: w4-cli-resto
epica: "E9-01, E7-04"
sprint: S3
pr:
depends_on: W4-01
---

# [W4-04] CLI `subscription`, `backup`, `agent`, `usage`

## Qué se ve

Resto de la superficie CLI fuera de ponds y SQL: suscripciones, backups, acceso agente y uso mensual. Lo visible es paridad con `api-surface.md` §5 sin atajos locales.

## Entradas ya decididas (no se cambian)

- Comandos: `subscription list/subscribe/cancel`, `backup list/restore`, `agent show/rotate`, `usage`.
- Todos mapean exactamente a `api-surface.md` §5.
- Las mutaciones (`subscribe`, `cancel`, `restore`, `rotate`) usan confirmación; las lecturas no.
- `agent show` nunca imprime password; `usage` consume `GET /usage`.
- El soporte `-o json` sale del helper común de W4-05.
- Sin sesión: exit `1` y el mensaje de `api-surface.md` §5.

## Criterios de aceptación

1. Cada comando llama al endpoint documentado, sin endpoints “de conveniencia”.
2. Las lecturas imprimen tablas legibles solo con campos del contrato.
3. Las mutaciones se detienen en `confirmation_required` y muestran el summary.
4. Hay pruebas con `respx`/`MockTransport` para al menos una lectura y una mutación por grupo.

## No tocar

- `apps/cli/koicloud_cli/client.py` y `config.py` salvo la API pública ya congelada por W1.
- `apps/api/app/commands/**`.
- `apps/node-agent/**`.
- `apps/api/app/mcp/{server.py,gate.py,prompt.py}` y cualquier tool mutante.

## Si algo falta

Respondé `BLOQUEADO` solo si hay que inventar un flag o un endpoint.
`-o json` es de W4-05. Este ticket imprime texto. No dupliques el formatter.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.
