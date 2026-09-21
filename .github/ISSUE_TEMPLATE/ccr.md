---
name: CCR — Contract Change Request
about: Único mecanismo para cambiar algo congelado (contratos, tablas, firmas, dependencias)
title: "[CCR] "
labels: ["ccr"]
assignees: []
---

<!--
Abrí un CCR cuando tu ticket no se puede cumplir sin cambiar algo congelado:
rutas o schemas del OpenAPI, códigos de error del catálogo, firmas de app/commands/*,
tablas, columnas, enums, máquinas de estado, o una dependencia que el ticket no nombra.

Mientras el CCR no esté aprobado, tu respuesta correcta es
"BLOQUEADO: requiere CCR porque …". No implementes "mientras tanto".
-->

## Qué cambia

<!-- Una frase. Ej.: "Pond necesita el campo `last_error` en GET /ponds/{id}". -->

## Por qué el ticket no se puede cumplir sin esto

<!-- Ticket afectado y qué criterio de aceptación queda imposible. -->

## Propuesta exacta

<!--
El diff concreto sobre docs/architecture/api-surface.md o data-model.md:
campo, tipo, obligatoriedad, valor por defecto, código de error, migración necesaria.
-->

```diff
```

## Impacto en otros workstreams

<!-- Quién más consume esto: Web, CLI, MCP, node-agent. "Ninguno" si no hay. -->

## ¿Requiere migración?

- [ ] Sí — entonces **no** puede ser CCR exprés, y la migración la escribe W1
- [ ] No

## Alternativa que ya descartaste

<!-- Qué intentaste resolver dentro del contrato actual y por qué no alcanza. -->

---

**Resolución de W1** <!-- la llena W1 -->

- [ ] Aprobado · [ ] Aprobado con cambios · [ ] Rechazado con alternativa

<!--
Si se aprueba: el dueño del módulo (o W1 si toca migraciones) hace el PR de contrato,
actualiza api-surface.md / data-model.md, regenera openapi.json y schema.d.ts con
`make contracts`, agrega una línea a packages/contracts/CHANGELOG.md y actualiza los
tickets afectados.
-->
