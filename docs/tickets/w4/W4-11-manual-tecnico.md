---
id: W4-11
workstream: W4
persona: Diego
estado: en-curso
rama: w4-manual-tecnico
epica: "E10-05"
sprint: S3
pr:
---

# [W4-11] Manual técnico (PDF)

## Qué se ve

Manual técnico a partir del pack de arquitectura. Lo visible es un documento operativo que explica instalación, variables, despliegue, MCP y CLI sin redefinir contratos.

## Entradas ya decididas (no se cambian)

- Ruta propia: `docs/manual-tecnico.md`.
- Fuentes: `docs/architecture/**`.
- Secciones fijas: instalación, variables de entorno, deploy, MCP y CLI.
- Debe enlazar diagramas y documentos fuente en vez de copiarlos a mano.
- La verificación final es en una máquina limpia.

## Criterios de aceptación

1. Los pasos de setup se pueden seguir en limpio sin prerequisitos ocultos.
2. El manual enlaza diagramas y docs de arquitectura relevantes.
3. Se exporta a PDF sin romper tablas o bloques de código.
4. La verificación por un tercero deja detectados faltantes de env vars o pasos.

## No tocar

- `apps/api/**`.
- `apps/cli/**`.
- `apps/node-agent/**`.
- `infra/**` y `.github/workflows/deploy.yml` salvo que el ticket lo mencione explícitamente.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes comandos, flags, payloads, tools ni atajos al flujo de confirmación.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.
