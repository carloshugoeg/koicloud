---
id: W2-18
workstream: W2
persona: Jason
estado: abierto
rama: w2-plan-picker-escape
epica: E2-03
sprint: S5
pr:
depends_on: W2-15
---

# [W2-18] Escape del selector de plan devuelve el foco

## Qué se ve

En Uso y facturación, con el selector de plan abierto y el foco en un botón Elegir plan, Escape cierra el selector y deja el foco en Cambiar de plan.

Si el diálogo de contratación o el de factura está abierto, Escape cierra solo ese diálogo y deja el foco en Elegir plan. El selector sigue abierto.

## Entradas ya decididas (no se cambian)

- Pantalla `/app/uso`, componente `PlanSection`, catálogo `PlansPage`.
- Textos «Cambiar de plan» y «Elegir plan Micro».
- El selector ya se cierra con Escape. Este ticket exige además el foco.
- El diálogo de checkout ya cierra con Escape en fase de captura y devuelve el foco al botón que lo abrió.
- Sin endpoints nuevos y sin cambios de OpenAPI.

## Criterios de aceptación

1. Con el foco en Elegir plan, Escape deja `aria-expanded="false"` en Cambiar de plan y el foco en ese botón. Prueba `returns focus to Cambiar de plan when Escape is pressed on Elegir plan`.
2. Escape dentro del diálogo de contratación cierra solo el diálogo, deja el selector abierto y el foco en Elegir plan. Prueba `returns focus to Elegir plan when Escape closes the checkout dialog from its first control`. La factura sigue cubierta por la prueba de factura que ya está en `billing-a11y.test.tsx`.
3. La pantalla no hace scroll horizontal a 375, 768 ni 1440.

## No tocar

- `packages/contracts/**`, `apps/web/src/api/schema.d.ts`, `apps/api/app/commands/**`.
- Las pruebas de `billing-a11y.test.tsx` después del commit de prueba. El arreglo no las edita.
- Consola SQL, administración y el resto de facturación.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

- `apps/web/src/features/billing/billing-a11y.test.tsx`
- PR #137, gate r23, que dejó el Escape del diálogo en Elegir plan.
