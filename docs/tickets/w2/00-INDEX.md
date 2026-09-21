# W2 — Web · Jason

Plan de tickets del workstream. Un ticket se trabaja **solo** cuando existe su archivo
`W2-nn-<slug>.md` con `estado: abierto` y las seis secciones. Mientras diga *por escribir*,
no existe todavía. `00-INDEX.md` no es un ticket y el agente lo ignora.

| ID | Título | Rama | Estado |
|---|---|---|---|
| W2-01 | Registro, login y verificación de correo | `w2-auth-pantallas` | por escribir |
| W2-02 | Recuperación de contraseña | `w2-recuperar-password` | por escribir |
| W2-03 | Catálogo de planes y contratación | `w2-planes-checkout` | por escribir |
| W2-04 | Dashboard de ponds (lista y estados) | `w2-dashboard-ponds` | por escribir |
| W2-05 | Crear pond (diálogo de configuración) | `w2-crear-pond` | por escribir |
| W2-06 | Detalle del pond y cadena de conexión | `w2-detalle-pond` | **abierto** |
| W2-07 | Consola SQL (editor y tabla de resultados) | `w2-consola-sql` | por escribir |
| W2-08 | Respaldos: lista y restauración | `w2-respaldos` | por escribir |
| W2-09 | Uso del mes e historial de facturas | `w2-uso-y-facturas` | por escribir |
| W2-10 | Panel administrador (tres tablas) | `w2-panel-admin` | por escribir |
| W2-11 | Acceso agente: revelar y rotar | `w2-acceso-agente` | por escribir |
| W2-12 | Layout, tema, estados vacíos y responsive a 360 px | `w2-tema-y-estados` | por escribir |

**Dos fuentes por pantalla, y no se confunden:** la arquitectura de información (qué campos,
qué tablas, qué pasos) sale de los mockups de `docs/entrega-2/mockups/`; la piel (color,
tipografía, densidad, movimiento) sale de `docs/visual-guidelines.md` y manda siempre.

**Fuera de `apps/web/` no se toca nada.** Tampoco `src/api/client.ts`,
`src/api/schema.d.ts`, `src/lib/auth-store.ts`, `src/app/router.tsx` ni
`src/components/ui/*` (salvo tema).
