# Mockups de pantallas principales — cómo se leen

**Proyecto:** KoiCloud (DBaaS académico, PostgreSQL 16 en Docker)
**Equipo KoiCloud:** Hugo Escobar · Jason Gutiérrez · Jousé Menendez · Diego Joachin
**Archivo principal:** [`pantallas-principales.html`](./pantallas-principales.html) — ábrelo en cualquier navegador, no necesita servidor ni build.

Este paquete cumple dos funciones distintas y conviene no confundirlas: fija el **piso** (lo que cada pantalla tiene que mostrar) y fija el **techo** (hasta dónde puede llegar la apariencia). Una es obligación, la otra es permiso.

---

## Piso — la obligación

El piso es la **arquitectura de información**: qué pantallas existen, qué campos entran, qué campos salen y qué pasos tiene cada flujo. No se negocia y no sale de este documento: sale del alcance sellado y de los contratos.

| Qué | Dónde manda |
|---|---|
| Qué se compromete el semestre | [`../alcance.md`](../alcance.md) — sellado |
| Endpoints, códigos de error, `propose → confirm` | [`../../architecture/api-surface.md`](../../architecture/api-surface.md) |
| Tablas, enums, máquinas de estado | [`../../architecture/data-model.md`](../../architecture/data-model.md) |
| Qué épica cubre cada pantalla | [`../../architecture/feature-breakdown.md`](../../architecture/feature-breakdown.md) |

Concretamente, el piso de cada pantalla del HTML son los bloques **`CAMPOS DE SALIDA`** al pie de cada sección. Están ahí porque el error más común al construir una pantalla es recibir un campo y no mostrarlo: si `last_error` llega en la respuesta y el usuario no lo ve, el panel es opaco y el problema que el proyecto dice resolver sigue vivo.

Tres reglas del piso que aplican a **todas** las pantallas:

1. **Todo listado lleva sus tres estados:** cargando (skeleton), vacío con salida, error con reintento. La sección transversal `Estados y 404` los muestra armados.
2. **Ningún estado se comunica solo por color:** siempre texto + glifo (`●` en línea, `◐` en proceso, `▲` atención, `✕` falla).
3. **La suspensión es de la cuenta, no del pond:** banner global en todo `/app`, nunca un badge de pond.

---

## Techo — el permiso

El techo es la **piel**: color, tipografía, espaciado, densidad, movimiento y marca. Manda [`../../visual-guidelines.md`](../../visual-guidelines.md), y este HTML es su demostración ejecutable. El norte es *un reporte anual de 1983 que resulta ser un panel de control*: papel hueso, tinta casi negra, retículas duras, turquesa que estructura, y un koi en pixel art como única concesión emocional.

**Si una pantalla del producto se ve así, está terminada. Si se ve mejor, mejor.** El techo no es un máximo de calidad; es el mínimo estético acordado y la prueba de que el sistema visual alcanza para armar el producto completo sin inventar nada por pantalla.

Lo que el techo fija de forma no negociable:

- **Tema claro único.** No hay modo oscuro, ni toggle, ni clase `.dark`, ni los colores `#0F6E6E` / `#F26B1D` del harness anterior.
- **Fuentes:** Fraunces (display, nunca por debajo de 20 px), Instrument Sans (UI — **no** Inter), IBM Plex Mono (técnico).
- **Cero hex literales** fuera del bloque `:root`. Todo color sale de un token.
- **Tres tokens no son colores de texto:** `turquoise-500` (2.89), `koi` (3.20) y `ink-faint` (3.82) sobre hueso. Rellenos, trazos, marcas de eje y titulares ≥24 px — nunca párrafo.
- **El koi solo donde la guía lo permite** (§7.3): landing, auth, vacío, `provisioning`/`restoring`, arranque de sesión y 404. Nunca sobre datos, nunca en administración, consola SQL ni facturación.

Para pegarle el techo a un agente de Cursor que vaya a escribir `apps/web/**`, usa el bloque listo: [`../../visual-guidelines-agent-prompt.md`](../../visual-guidelines-agent-prompt.md).

---

## Pantallas incluidas

Dieciséis secciones. La primera no es una pantalla del producto: es el sistema visual del que se arman las otras.

| # | Sección | Épica | Qué demuestra |
|---|---|---|---|
| — | Sistema visual | — | Tokens, escala tipográfica, botones, badges de estado, densidad y reglas del estanque |
| 0 | Landing y catálogo público | E2-01 | Hero de 56 px, panel del estanque, planes con nombre/descripción/precio/vigencia |
| 1 | Registro, verificación, sesión, restablecimiento | E1-01…04 | Cuatro pantallas con el mismo esqueleto; errores de auth en su sitio |
| 2 | Catálogo de planes y contratación | E2-01, E2-02 | Tabla comparativa densa + checkout con aviso de pago simulado e historial |
| 3 | Dashboard de ponds | E3-02 | Cuatro KPI, rejilla del estanque, tabla con estado observado y último error |
| 4 | Crear pond | E3-01 | Diálogo de 560 px: nombre validado en vivo, motor 16, plan heredado |
| 5 | Detalle del pond · resumen | E3-03, E3-05 | Seis pestañas, KPI de límites con micro-barra, koi nadando en `provisioning` |
| 5b | Cadena de conexión | E3-03 | URI enmascarada, copiar por campo, snippets `psql` / `.env` / Node / Python |
| 6 | Consola SQL | E5-01…05 | Árbol de esquema, editor, resultados, barra de estado, **modo escritura** e historial |
| 7 | Respaldos y restauración | E6-01…04 | Tipo/estado/tamaño/sha256/expira + restauración con confirmación textual |
| 8 | Uso del mes y facturación | E7-03, E2-03 | Matriz de puntos por día, barras apiladas por pond, factura con IVA desglosado |
| 9 | Panel administrador | E8-01…04 | Usuarios, ponds del sistema, bitácora, suspensión con `confirm_email`. Cero koi |
| 10 | Acceso agente · URL y contraseña | E9-05 | URL `/mcp`, contraseña de una sola vez, configuración en Claude Code y Cursor |
| 11 | Confirmación `propose → confirm` | E9-04 | El diálogo de la demo + las transcripciones equivalentes de CLI y MCP |
| 12 | Cuenta y perfil | E1-05 | Nombre, NIT (`CF` si no hay), contraseña, eliminar cuenta. Sin toggle de tema |
| — | Estados, suspensión y 404 | — | Los tres estados de un listado, toasts, banner de suspensión, arranque y 404 |

**Pantallas que no se construyen** porque están fuera del alcance sellado: página pública de estado, panel de flota, sandbox sin registro, explorador de costos avanzado, llaves de agente con scopes y topes, bandeja de aprobaciones.

---

## Renders

Un PNG por pantalla, más la hoja completa y el PDF, en [`../renders/mockups/`](../renders/mockups/). Se generan con Chrome headless a `deviceScaleFactor: 2` y con las animaciones congeladas, para que el koi no salga a medio movimiento.

```
00-sistema-visual.png     08-consola-sql.png
01-landing.png            09-respaldos.png
02-auth.png               10-uso-y-factura.png
03-planes-checkout.png    11-admin.png
04-dashboard-ponds.png    12-acceso-agente.png
05-crear-pond.png         13-confirmacion.png
06-detalle-pond.png       14-cuenta.png
07-conexion.png           15-estados-y-404.png

pantallas-completas.png   mockups.pdf
```

Para regenerarlos basta abrir el HTML e imprimir a PDF (`@media print` ya corta una pantalla por página), o repetir la captura por sección con cualquier herramienta de Chrome DevTools Protocol.

---

## El estanque es arte real (ya no un stand-in)

El koi de 32×32 de un solo cuadro quedó derogado. Lo que se ve en la landing, en auth, en el
vacío, en el arranque de sesión, en el 404 y en la tira de `provisioning` es el arte hi-bit
producido a partir de los refs 05 y 06 de Carlos:

| Pieza | Nativo | En pantalla | Archivo |
|---|---|---|---|
| Agua del hero (tesela) | 120×80 | 480×320 a ×4 | `assets/pond-water-hero.png` |
| Agua de auth (tesela) | 100×130 | 400×520 a ×4 | `assets/pond-water-auth.png` |
| Agua de panel: vacío, arranque, 404 | 80×50 | 320×200 a ×4 | `assets/pond-water-panel.png` |
| Agua de la tira de `provisioning` | 48×16 | 192×64 a ×4 | `assets/pond-water-strip.png` |
| Koi: 8 cuadros de nado + 4 de giro | 768×64 | 64×64 por cuadro | `assets/koi-sheet-64.png` |
| Marca del logotipo | 32×32 | 32×32 | `assets/koi-mark-32.png` |

Los mismos PNG viven en `media/koi/` (con `preview/` a ×4 para mirarlos de cerca) y los
genera `internal/koi-hibit-gen.py`. La especificación está en `visual-guidelines.md` §7.

La hoja sigue siendo **un solo archivo que se abre con doble clic**: los seis PNG van
incrustados en base64 dentro del bloque `KOI-ASSETS` del CSS. Ese bloque lo escribe el
generador, no se edita a mano — `python3 internal/koi-hibit-gen.py --embed` lo rehace.

## Una cosa provisional, a propósito

**Las fuentes vienen por CDN solo en esta hoja,** para que el archivo se abra en cualquier
navegador sin instalar nada. En el producto van autohospedadas con Fontsource
(`visual-guidelines.md` §4): el VPS debe funcionar sin red externa. No afecta el piso ni el
techo, y está marcado en el pie del HTML.
