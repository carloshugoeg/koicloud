# Cómo se contribuye a KoiCloud

Corto a propósito. Las reglas completas que siguen los agentes están en
[`AGENTS.md`](./AGENTS.md); el reparto y el Definition of Done, en
[`docs/WORKSTREAMS.md`](./docs/WORKSTREAMS.md).

## 1. Antes de empezar

```bash
git config user.name  "Nombre Apellido"
git config user.email "correo-de-tu-cuenta-de-github"
make up && make migrate && make seed
```

La identidad de git es **tu cuenta real de GitHub**: cada quien firma su trabajo. «Equipo
KoiCloud» es el nombre público del equipo, no un autor de git. Los correos y handles del
equipo están en `docs/WORKSTREAMS.md` §3.

## 2. El ciclo

1. **Ticket.** El trabajo sale de `docs/tickets/<wN>/`, no de una conversación.
   Atajo: `bash scripts/what-do-i-do.sh <tu nombre>`.
2. **Rama.** `git checkout -b wN-<slug>`, con el slug que trae el ticket
   (`w2-detalle-pond`). Sin prefijo `cursor/`, sin sufijos aleatorios.
3. **Plan antes de código.** Si trabajás con un agente, pedile un plan de 5 a 15 líneas y
   aprobalo antes de que escriba nada.
4. **Implementá solo dentro de tu workstream.** Si necesitás algo de otra zona, abrí un
   issue con `ticket.md`; si necesitás cambiar un contrato, uno con `ccr.md`. Nunca lo
   cambies por tu cuenta.
5. **`make check-<área>`** en verde, con la salida real pegada en el PR.
6. **PR** con la plantilla completa, título `[W2-06] Detalle del pond` y un solo ticket
   dentro, ≤ 500 líneas netas.

## 3. Commits

Conventional Commits en inglés, con scope de módulo:

```
feat(ponds): show connection string on detail page
fix(billing): round IVA to two decimals
```

**Nunca** añadas `Co-authored-by: Cursor / Antigravity / Gemini / Claude`, ni líneas del
tipo «Generated with…», ni firmas de agente. Si tu herramienta las agrega sola, quitalas
antes de commitear. `Co-authored-by:` se usa solo cuando otro compañero humano trabajó de
verdad en ese commit, con su cuenta real.

## 4. Lo que se rechaza sin discusión

Tocar archivos de otro workstream · cambiar un contrato congelado sin CCR · migraciones
fuera de W1 · dependencias que el ticket no nombra · secretos en el repo · desactivar
pruebas · un PR sin pruebas o sin la salida de `make check` · en `apps/web`, cualquier cosa
que rompa `docs/visual-guidelines.md` (modo oscuro, `Inter`, hex literales) · usar GitHub
MCP en lugar de `gh`.

## 5. Publicación

Todo con `gh` (`gh pr create`, `gh pr comment`, `gh pr review`). Nunca herramientas de
GitHub MCP. Si `gh` no está autenticado, pará y avisá: no abras un login interactivo dentro
de una sesión de agente.
