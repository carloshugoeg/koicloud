# W2 — Web · Jason

Plan de tickets del workstream. Todos los tickets de este workstream ya existen como archivos
`W2-nn-<slug>.md` con `estado: abierto` y las seis secciones. `00-INDEX.md` no es un ticket y
el agente lo ignora.

| ID | Título | Rama | Estado |
|---|---|---|---|
| W2-01 | Registro, login y verificación de correo | `w2-auth-pantallas` | hecho ([PR #1](https://github.com/carloshugoeg/koicloud/pull/1)) |
| W2-02 | Recuperación de contraseña | `w2-recuperar-password` | abierto |
| W2-03 | Catálogo de planes y contratación | `w2-planes-checkout` | abierto |
| W2-04 | Dashboard de ponds (lista y estados) | `w2-dashboard-ponds` | abierto |
| W2-05 | Crear pond (diálogo de configuración) | `w2-crear-pond` | abierto |
| W2-06 | Detalle del pond y cadena de conexión | `w2-detalle-pond` | abierto |
| W2-07 | Consola SQL (editor y tabla de resultados) | `w2-consola-sql` | abierto |
| W2-08 | Respaldos: lista y restauración | `w2-respaldos` | abierto |
| W2-09 | Uso del mes e historial de facturas | `w2-uso-y-facturas` | abierto |
| W2-10 | Panel administrador (tres tablas) | `w2-panel-admin` | abierto |
| W2-11 | Acceso agente: revelar y rotar | `w2-acceso-agente` | abierto |
| W2-12 | Layout, tema, estados vacíos y responsive a 360 px | `w2-tema-y-estados` | abierto |

**Dos fuentes por pantalla, y no se confunden:** la arquitectura de información (qué campos,
qué tablas, qué pasos) sale de los mockups de `docs/entrega-2/mockups/`; la piel (color,
tipografía, densidad, movimiento) sale de `docs/visual-guidelines.md` y manda siempre.

**Fuera de `apps/web/` no se toca nada.** Tampoco `src/api/client.ts`,
`src/api/schema.d.ts`, `src/lib/auth-store.ts` ni `src/components/ui/*` (salvo tema).
`src/app/router.tsx` ya registra las rutas de Fase 0. Implementá la página del ticket.
No pidas CCR por una ruta que ya está. Podés editar `docs/tickets/w2/**`.
