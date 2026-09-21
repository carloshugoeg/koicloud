<!-- Título del PR: [W2-06] Detalle del pond y cadena de conexión -->

## Ticket

- ID: `W?-??`
- Workstream: `W?`
- Rama: `w?-slug`
- Archivo del ticket: `docs/tickets/w?/W?-??-slug.md`

## Qué cambia

<!-- 3 a 8 líneas. Qué hace ahora el sistema que antes no hacía. Sin narrar el proceso. -->

## Criterios de aceptación cubiertos

<!-- Copiá cada criterio del ticket y decí cómo se verifica: prueba con nombre, o evidencia manual. -->

| CA | Cómo se verifica |
|---|---|
| (1) | `tests/…::test_…` |
| (2) | manual: … |

## Cómo probé el caso feliz a mano

<!-- Comandos exactos (curl / make / clics en la Web) y qué se vio. Obligatorio. -->

```
```

## Salida de `make check-<área>`

<!-- Pegá la salida real completa, sin editarla. Obligatorio. -->

```
```

## Decisiones tomadas

<!-- Ambigüedades que resolviste y por qué. "Ninguna" si no hubo. -->

## Dependencias nuevas

<!-- Nombre, versión y motivo. "Ninguna" si no hay. Requiere aprobación de W1. -->

## Checklist

- [ ] Todos los archivos cambiados están dentro de las rutas de mi workstream
- [ ] No cambié nada congelado (OpenAPI, firmas de `commands/`, tablas, enums) — o este PR
      implementa un CCR aprobado: `#___`
- [ ] Pruebas nuevas para cada endpoint, regla o pantalla que toqué
- [ ] Sin `any`/`Any`, `type: ignore`, `noqa` ni `eslint-disable` sin justificación
- [ ] Sin `print`/`console.log`, código comentado ni TODO sin issue
- [ ] Sin lógica de negocio en routers, tools MCP, comandos CLI ni componentes React
- [ ] Textos de UI y correo en español; código en inglés
- [ ] Commits con Conventional Commits y scope de módulo
- [ ] **Los commits van con mi cuenta real de GitHub** (`git config --get user.email`)
- [ ] **Ningún trailer de herramienta** (`Co-authored-by: Cursor/Antigravity/Gemini/Claude`,
      «Generated with…») en ningún commit de esta rama
- [ ] ≤ 500 líneas netas (sin generados, lockfiles ni fixtures)
- [ ] Actualicé el `estado` del archivo del ticket

### Solo si toqué `apps/web`

- [ ] Lista de verificación de piel de `docs/visual-guidelines.md` §11.2 marcada
- [ ] Captura del estado feliz adjunta
- [ ] Sin `dark:`, sin `.dark`, sin `Inter`, sin hex literales fuera de `index.css`
- [ ] Los tres estados del listado presentes (cargando, vacío, error) y usable a 360 px
