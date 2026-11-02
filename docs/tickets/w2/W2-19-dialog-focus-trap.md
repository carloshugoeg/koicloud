---
id: W2-19
workstream: W2
persona: Jason
estado: hecho
rama: w2-dialog-focus-trap
epica: E2-03
sprint: S5
pr: "https://github.com/carloshugoeg/koicloud/pull/178"
depends_on: W2-18
---

# [W2-19] El foco permanece dentro de los diálogos de contratación y factura

## Qué se ve

En Uso y facturación, con el diálogo de contratación abierto, Tab y Shift+Tab recorren solo los controles de ese diálogo. Lo mismo con el diálogo de factura. El foco no pasa a la página de atrás.

Escape sigue cerrando solo el diálogo abierto y deja el foco en Elegir plan. El selector de plan permanece abierto.

## Entradas ya decididas (no se cambian)

- Pantalla `/app/uso`, diálogo de contratación y diálogo de factura en `CheckoutModal`.
- Textos «Elegir plan» y «Cambiar de plan».
- Escape del diálogo ya está en fase de captura y devuelve el foco al botón que lo abrió (W2-18).
- Un solo mecanismo de trampa de foco, compartido. Sin una trampa distinta por diálogo.
- Sin endpoints nuevos y sin cambios de OpenAPI.

## Criterios de aceptación

1. Tab y Shift+Tab ciclan dentro del diálogo de contratación en 375, 768 y 1440. Pruebas `checkout dialog cycles Tab and Shift+Tab at 375`, `at 768` y `at 1440`.
2. Tab y Shift+Tab ciclan dentro del diálogo de factura en los tres anchos. Pruebas `invoice dialog cycles Tab and Shift+Tab at 375`, `at 768` y `at 1440`.
3. Escape cierra solo el diálogo de contratación y el foco vuelve a Elegir plan. Prueba `escape closes only the checkout dialog and returns focus to Elegir plan`.

## No tocar

- `packages/contracts/**`, `apps/web/src/api/schema.d.ts`, `apps/api/app/commands/**`.
- `e2e/journey/tests/dialog-focus-trap.spec.ts` después del commit de prueba. El arreglo no lo edita.
- El comportamiento de Escape de `plan-section.tsx` (W2-18).
- Consola SQL, administración y el resto de facturación.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

- Issue #175.
- `apps/web/src/features/billing/plan-section.tsx`
- `e2e/journey/tests/dialog-focus-trap.spec.ts`
- W2-18, PR #174.
