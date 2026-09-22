---
id: W4-10
workstream: W4
persona: Diego
estado: abierto
rama: w4-manual-usuario
epica: "E10-05"
sprint: S5
pr:
---

# [W4-10] Manual de usuario (PDF)

## Qué se ve

Manual de usuario con capturas reales de la Web. Lo visible es un documento en español que recorre el flujo de producto y puede exportarse a PDF sin maquetar desde cero.

## Entradas ya decididas (no se cambian)

- Rutas propias: `docs/manual-usuario.md` y `docs/manual-usuario/img/`.
- Secciones fijas: registro, login, contratación, ponds, SQL, backups, uso y agente.
- Debe llevar una captura por flujo principal.
- El copy tiene que reflejar pantallas reales y no mockups futuros.
- Depende de que W2 ya tenga las superficies listas para capturar.

## Criterios de aceptación

1. El manual cubre todos los flujos principales con al menos una captura por flujo.
2. El texto está en español y coincide con la UI real.
3. Se exporta a PDF por el mecanismo acordado del repo (pandoc/Makefile).
4. W2 revisa las capturas y marca cualquier desfase antes de cerrar.

## No tocar

- `apps/api/**`.
- `apps/cli/**`.
- `apps/node-agent/**`.
- `infra/**` y `.github/workflows/deploy.yml` salvo que el ticket lo mencione explícitamente.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes comandos, flags, payloads, tools ni atajos al flujo de confirmación.
- Si las pantallas de W2 todavía no existen o no son estables, bloqueá y no uses mockups como si fueran evidencia final.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.
