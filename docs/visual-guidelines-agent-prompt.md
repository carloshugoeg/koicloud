# Bloque para agente de Cursor — piel visual de KoiCloud

Para Jason (W2). Copia el bloque de abajo **completo** y pégalo en el agente de Cursor que trabaje en `apps/web/**`. Es autosuficiente: no requiere que el agente lea otros documentos.

Dos formas de usarlo:

- **Por sesión** — pégalo como primer mensaje del chat, antes de pedir la pantalla.
- **Permanente (recomendado)** — guárdalo como `.cursor/rules/visual.mdc` en el repo con este encabezado, y aplica a todo el frontend:

```
---
description: Piel visual de KoiCloud (obligatoria en apps/web)
globs: apps/web/**
alwaysApply: true
---
```

La versión larga y razonada vive en [`visual-guidelines.md`](./visual-guidelines.md). Si algo de abajo contradice a ese documento, manda ese documento.

**Cambio de septiembre — el estanque subió de resolución.** El koi ya no es un sprite de 32×32 con paleta turquesa: es pixel art hi-bit con agua azul profunda, siguiendo los refs 05 y 06 de Carlos. El arte ya está producido en `media/koi/` (planchas de agua, hoja de nado de 64×64, marcas de 32 y 16), así que el agente **no** genera arte: lo copia a `public/koi/`. Si ya pegaste la versión anterior de este bloque en un repo o en `.cursor/rules/visual.mdc`, reemplázala.

---

````text
# PIEL VISUAL DE KOICLOUD — REGLAS OBLIGATORIAS

Trabajas en `apps/web` (React + TypeScript + Vite + Tailwind + shadcn/ui) de KoiCloud,
un DBaaS académico de PostgreSQL. Cada instancia de base de datos se llama "pond".
Estas reglas mandan sobre cualquier valor por defecto de shadcn, de Tailwind o tuyo.

## NORTE
"Un reporte anual de 1983 que resulta ser un panel de control."
Tres adjetivos que resuelven dudas: IMPRESO, DENSO, SERENO.
Papel hueso en vez de blanco. Hairlines en vez de sombras. Retícula dura.
Cifras grandes con orgullo. Color escaso y con significado.
Única concesión emocional: un estanque de koi en pixel art.

## TEMA
TEMA CLARO ÚNICO. No existe modo oscuro. Nunca escribas clases `dark:`,
ni la clase `.dark`, ni un toggle de tema. Si un requisito viejo pide dark mode,
está anulado.

## TOKENS — va en `src/index.css`. NUNCA un hex literal en un componente.

:root {
  /* papel */
  --bone:#F2ECDC; --bone-raised:#FBF7EC; --bone-sunk:#E8E0CC; --paper:#FFFCF4;
  /* tinta */
  --ink:#14211F; --ink-muted:#4C5B58; --ink-faint:#6B7A74;
  /* líneas */
  --line:#D8CFB8; --line-control:#8C8778;
  /* turquesa */
  --turquoise-100:#C6E9E4; --turquoise-300:#79CFC6; --turquoise-500:#0E9C8E;
  --turquoise-700:#0A6D64; --turquoise-900:#06413C;
  /* verde */
  --green-100:#DDEAC9; --green-500:#5B9A45; --green-700:#376B2C; --green-900:#1F4420;
  /* acentos */
  --koi:#E2552B; --koi-soft:#F3A183; --marigold:#E3A72C; --lagoon:#5C6FB1;
  /* estado */
  --ok:#376B2C; --warn:#8A5A0A; --danger:#A81F2B;
  /* espacio base 4, ritmo 8 */
  --space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px;
  --space-5:24px; --space-6:32px; --space-7:48px; --space-8:64px;
  /* radios casi rectos */
  --radius-xs:0px; --radius-sm:2px; --radius-md:4px; --radius-lg:6px;
  /* elevación: offset duro de imprenta, jamás blur suave */
  --shadow-print:3px 3px 0 rgba(20,33,31,.10);
  --shadow-dialog:6px 6px 0 rgba(20,33,31,.14);
  --shadow-focus:0 0 0 2px var(--bone), 0 0 0 4px var(--turquoise-700);
  /* movimiento */
  --dur-instant:80ms; --dur-fast:140ms; --dur-slow:240ms;
  --ease:cubic-bezier(.2,0,.1,1); --ease-out:cubic-bezier(0,0,.2,1);
  /* shell */
  --sidebar-w:264px; --header-h:56px; --content-max:1280px; --row-h:40px;
}

Puente shadcn (mapea, no reemplaces):
  --background:var(--bone);        --foreground:var(--ink);
  --card:var(--bone-raised);       --popover:var(--bone-raised);
  --primary:var(--turquoise-700);  --primary-foreground:var(--bone-raised);
  --secondary:var(--bone-sunk);    --muted:var(--bone-sunk);
  --muted-foreground:var(--ink-muted);
  --accent:var(--turquoise-100);   --accent-foreground:var(--turquoise-900);
  --destructive:var(--danger);     --destructive-foreground:var(--bone-raised);
  --border:var(--line);            --input:var(--line-control);
  --ring:var(--turquoise-700);     --radius:var(--radius-sm);
  --chart-1:var(--turquoise-700);  --chart-2:var(--koi);  --chart-3:var(--green-500);
  --chart-4:var(--marigold);       --chart-5:var(--lagoon);

## CONTRASTE — reglas duras, ya medidas

TEXTO PERMITIDO SOBRE HUESO:
  ink (14.05) · ink-muted (6.05) · turquoise-700 (5.26) · green-700 (5.39)
  warn (5.02) · danger (6.15)
NO SON COLOR DE TEXTO DE PÁRRAFO — solo relleno, trazo, icono o ≥24 px:
  turquoise-500 (2.89) · koi (3.20) · ink-faint (3.82) · lagoon (4.08)
Botón primario = texto `bone-raised` sobre `turquoise-700` (5.80). Correcto, úsalo.
Badges: texto `ink` sobre turquoise-100 / green-100 / koi-soft / marigold (≥7.7). Correcto.
`line` (1.32) es decorativa: jamás como borde de control ni anillo de foco.
`line-control` (3.04) es el borde de inputs y checkboxes.
Foco: siempre `--shadow-focus`. Nunca `outline:none` sin reemplazo.
Nunca comuniques un estado solo con color: texto + glifo (● en línea, ◐ en proceso,
▲ atención, ✕ falla).

## TIPOGRAFÍA — tres familias, Fontsource, autohospedadas

pnpm add @fontsource-variable/fraunces @fontsource/instrument-sans @fontsource/ibm-plex-mono

  --font-display:"Fraunces","Source Serif 4",Georgia,serif;
  --font-sans:"Instrument Sans","Helvetica Neue",system-ui,sans-serif;
  --font-mono:"IBM Plex Mono",ui-monospace,monospace;

PROHIBIDO Inter, Roboto, Arial y Helvetica como fuente de UI. La UI es Instrument Sans.
Fraunces NUNCA por debajo de 20 px; ajústala con
  font-variation-settings:"SOFT" 0,"WONK" 0,"opsz" 48; letter-spacing:-.02em;
(tono reporte, no tono boda). Un título de tarjeta chico usa Instrument Sans 600.

Escala (tamaño/interlínea · familia · peso):
  display-xl 56/60 Fraunces 600 — hero de landing, solo ahí
  display-l  40/44 Fraunces 600 — cifra KPI grande
  display-m  28/34 Fraunces 600 — título de página
  display-s  20/26 Fraunces 600 — título de tarjeta y de diálogo
  body-l     16/24 Instrument 400
  body-m     14/20 Instrument 400 — DEFECTO DE LA APP
  body-s     13/18 Instrument 400 — ayudas y metadatos
  label      12/16 Instrument 500 — etiqueta de campo, encabezado de columna
  overline   11/14 Instrument 600, +.08em, VERSALITAS — grupo de lateral, banda
  mono-m     13/20 IBM Plex Mono — SQL, URI, resultados
  mono-s     12/18 IBM Plex Mono — IDs, tokens, timestamps

Toda cifra en tabla, KPI, precio o métrica: `font-variant-numeric:tabular-nums`
y alineada a la derecha. Párrafos largos a `max-width:64ch`.

## LAYOUT

Shell: lateral 264 px (`bone-sunk`, borde derecho 1 px `line`) + header 56 px
(`bone`, borde inferior 1 px `line`) + contenido con padding 32 px, máx. 1280 px,
grid de 12 columnas y gutter de 24 px.
Ítem de lateral: 36 px de alto, radio 2. ACTIVO = fondo `turquoise-100`,
texto `turquoise-900`, barra izquierda de 3 px `turquoise-700`. HOVER = fondo `bone`.
Grupos de lateral con encabezado `overline`. Contadores a la derecha.
<1024 px la lateral colapsa a 72 px de iconos; <768 px pasa a `Sheet`.
Usable a 360 px sin scroll horizontal.

Tarjeta: `bone-raised`, borde 1 px `line`, radio 4, padding 20 px, SIN SOMBRA.
Tarjeta KPI: etiqueta `label` arriba → cifra `display-l` Fraunces tabular → delta
con glifo (▲ green-700 / ▼ danger / — ink-muted). Rejilla 4 / 2 / 1.

Banda de sección (el gesto del reporte anual): regla superior de 3 px + `overline`
debajo. Rota el color entre secciones: turquoise-700 → green-700 → marigold → lagoon.

Tabla: fila 40 px, padding 12 px, `body-m`, radio 0. Encabezado `bone-sunk` con
`label` `ink-muted` y borde inferior 1 px `line-control`. Divisores 1 px `line`.
SIN ZEBRA. Hover de fila `bone-raised`. Números a la derecha, tabulares.
Micro-barra inline: 4 px, fondo `bone-sunk`, relleno `turquoise-500`;
`marigold` >80 %, `danger` >95 %.

Formulario: etiqueta arriba, ayuda debajo, error en `danger` con glifo.
Input 36 px, fondo `paper`, borde 1 px `line-control`, radio 2.
Foco: `--shadow-focus` y borde `turquoise-700`. Máx. 560 px de ancho.

## BOTONES

  primario           fondo turquoise-700, texto bone-raised, sin borde
  secundario         fondo bone-raised, texto ink, borde 1 px line-control
  fantasma           transparente, texto turquoise-700
  destructivo        fondo danger, texto bone-raised
  destructivo suave  fondo bone-raised, texto danger, borde 1 px danger

Alto 36 px (sm 30, lg 44), radio 2, padding 16 px, peso 500.
UNA sola acción primaria por región. Cargando = spinner 14 px + gerundio ("Creando…").
EL KOI NO ES COLOR DE BOTÓN. Nunca un CTA naranja.

## ESTADOS DEL POND (badge: radio 2, padding 2/8, `label`, glifo + texto, texto `ink`)

  pending       "En cola"            fondo bone-sunk      ◌
  provisioning  "Aprovisionando…"    fondo turquoise-100  ◐   (aquí nada el koi)
  running       "En línea"           fondo green-100      ●
  restoring     "Restaurando…"       fondo turquoise-100  ◐   (aquí nada el koi)
  stopped       "Detenido"           fondo bone-sunk      ■
  deleting      "Eliminando…"        fondo koi-soft       ◐
  deleted       "Eliminado"          fondo bone-sunk      ✕   (fila atenuada)
  failed        "Con fallas"         fondo #F6D9D9        ✕   (texto danger)

La suspensión es de la CUENTA, no del pond: banner global `danger` en `/app`.

## CÓDIGO, CONEXIÓN Y SQL

Bloque de código: fondo `paper`, borde 1 px `line`, radio 4, IBM Plex Mono 13/20,
padding 16 px.
Cadena de conexión: contraseña enmascarada (••••••••) con botón "Mostrar"; no la
pongas en el DOM antes de que el usuario pulse. Copiar por campo; al copiar, el icono
cambia a ✓ `green-700` por 1.2 s.
CodeMirror SQL: keyword turquoise-700 500 · string green-700 · number lagoon ·
comment ink-faint cursiva · function ink 500. Fondo `paper`, gutter `bone-sunk`,
línea activa `bone`, selección `turquoise-100`.
MODO ESCRITURA: borde del editor 2 px `koi` + banda superior `koi-soft` con texto
`ink`: "Modo escritura: las sentencias modifican datos reales." Es el ÚNICO lugar
donde el koi rodea una región completa.
Resultados: tabla densa sobre `paper`, `NULL` en `ink-faint` cursiva, truncado
avisado en `warn`, duración y filas en mono-s.

## GRÁFICOS (Recharts)

Tendencia → MATRIZ DE PUNTOS (punto de 3 px cada 4 px), no área sólida.
Serie principal turquoise-700; superpuesta koi.
Barras apiladas: turquoise-900 → 700 → 500 → 300 de abajo arriba, rectas, gap 2 px.
Rejilla del estanque: una celda cuadrada de 14 px por pond, coloreada por estado.
Ejes: línea `line`, etiquetas `ink-faint` 11 px, sin rejilla vertical, rejilla
horizontal punteada. Tooltip `bone-raised` + borde `line-control` + `--shadow-print`.
Toda serie con etiqueta directa o leyenda con glifo, nunca solo color.

## DIÁLOGOS Y ESTADOS DE DATOS

Diálogo: `bone-raised`, borde 1 px `line-control`, radio 4, `--shadow-dialog`,
velo rgba(20,33,31,.32). Destructivo: exige escribir el nombre del recurso.
Diálogo propose→confirm (lo más importante de la demo): banda `marigold`, el
`summary` del backend en `body-l`, token en mono-s, expiración como cuenta regresiva
mm:ss en `warn`.
Toast (sonner): `bone-raised`, borde izquierdo 3 px del color semántico,
`--shadow-print`, radio 2.
TODO listado necesita sus tres estados: skeleton `bone-sunk` con barrido de 1.2 s ·
vacío con estanque + título + un CTA · error con banda `danger` 3 px, mensaje
traducido, botón Reintentar y el `code` crudo en mono-s.

## EL KOI

EL ARTE YA EXISTE. No lo generes: copia los PNG de `media/koi/` a `public/koi/`.
Es pixel art hi-bit, no el sprite de 32×32 de la versión anterior (derogado).
Paleta cerrada del estanque, 14 colores, SOLO dentro del arte:
agua #0D334F #103E56 #124B5C #135063 #164F63 · onda #316075 #3F7587 ·
nenúfares #1C7260 #258E5D #2BAC5B #39DC5A · koi #9FBDB8 #D8E5E3 #C05442.
El `--koi` #E2552B sigue siendo el naranja de la INTERFAZ y nunca entra al arte.

Koi: hoja de 64×64, 12 cuadros en 768×64 — 0–7 nado, 8–11 giro. Kohaku (cuerpo
#D8E5E3, tres manchas #C05442, aletas #9FBDB8), sin contorno. Nada de SVG con
filtros ni Lottie.
Agua: planchas PNG que teselan en los dos ejes, con nenúfares y flores dentro —
`pond-water-hero` 120×80, `pond-water-auth` 100×130, `pond-water-panel` 80×50,
`pond-water-strip` 48×16. El agua NO se dibuja con CSS.
Marca: `koi-mark-32` (logotipo) y `koi-mark-16` (favicon), con contorno 1 px
#0D334F — sobre hueso el cuerpo blanco se pierde sin él.

ESCALA: 1 píxel nativo = 4 px CSS. ESCALADO SOLO EN ENTEROS (×1 ×2 ×3 ×4) con
`image-rendering:pixelated`. Ningún panel del estanque por debajo de 40 píxeles
nativos de alto; para tamaños chicos usa la marca, no una reducción del sprite.

  @keyframes koi-swim    { to { background-position-x:-512px; } }   /* 8 × 64 px */
  @keyframes koi-swim-x2 { to { background-position-x:-1024px; } }
  .koi { width:64px; height:64px;
         background:url("/koi/koi-sheet.png") 0 0/768px 64px;
         image-rendering:pixelated;
         animation:koi-swim .8s steps(8) infinite, koi-drift 26s var(--ease) infinite; }

Nado a 10–12 fps. Cada escala necesita su propio keyframe: el ×2 recorre 1024 px.
Deriva no lineal, con pausas y giro `scaleX(-1)` en los extremos.
Varios koi: desfasa con `animation-delay` negativo distinto por instancia.
El agua se mueve panorámicamente exactamente el ancho de un mosaico por ciclo
(72–110 s, lineal), así el bucle no salta.
Los koi nadan en agua abierta: no los pongas encima de un nenúfar de la plancha.

DÓNDE APARECE:
  landing hero        panel 100 %×320 px, 3 koi (uno ×2), deriva 24–30 s
  auth                panel izquierdo 40 %, 1 koi ×2, deriva 30 s
  estado vacío        estanque 240×160, 1 koi, deriva 18 s
  provisioning/restoring  koi 64×64 en tira de 192×64 dentro de la tarjeta, bucle 4.5 s
  arranque de sesión  estanque quieto 160×120
  404                 estanque 320×200, koi ×2
  favicon / logo      koi-mark-16 / koi-mark-32, estáticos

PROHIBIDO: koi detrás de datos, texto o tablas · más de un estanque por pantalla ·
koi en administración, consola SQL, facturación o cualquier tabla · koi como
indicador real de estado (el badge es la verdad) · koi rotado, con opacidad,
con sombra o con degradado encima · escalado no entero.

@media (prefers-reduced-motion:reduce) — el koi se congela en el cuadro 0, el agua
se detiene, y toda animación/transición baja a 0.01 ms. Requisito, no extra.

## MOVIMIENTO GENERAL
La interfaz de datos es casi inmóvil. Hover 80 ms. Popover y expansión 140 ms,
solo opacidad + 4 px. Diálogo 240 ms. Cambio de estado por polling: destello de
600 ms de la fila hacia `turquoise-100` y de vuelta; nunca reordenes la tabla sola.
PROHIBIDO: parallax, animación al scroll, rebote, contadores animados, transiciones
de página, spinners de página completa.

## TEXTO
Español neutro, tuteo. "el pond", "tu pond" (masculino). Frases cortas, sin jerga
sin traducir, sin mayúsculas gritadas, sin emoji en la interfaz. Iconos solo de
`lucide`, trazo 1.5 px, 16 px en línea y 20 px en botones.

## ANTES DE DAR POR TERMINADO — verifica todo esto
- [ ] Cero hex literales fuera de `index.css`; cero `bg-[#…]` o `text-[#…]`.
- [ ] Ninguna clase `dark:`, ningún `.dark`, ningún toggle de tema.
- [ ] Ningún uso de Inter / Roboto / Arial. UI = Instrument Sans.
- [ ] Fraunces solo a ≥20 px.
- [ ] `tabular-nums` en toda cifra de tabla y KPI, alineada a la derecha.
- [ ] `turquoise-500`, `koi`, `ink-faint` y `lagoon` no se usan como texto de párrafo.
- [ ] Foco visible con `--shadow-focus` en todo elemento interactivo.
- [ ] Ningún estado comunicado solo por color.
- [ ] Cargando, vacío y error presentes en cada listado.
- [ ] Máximo un estanque por pantalla; ningún koi sobre datos.
- [ ] El arte del estanque viene de `public/koi/`, a escala entera y con `image-rendering:pixelated`.
- [ ] Los 14 colores del estanque no se usan como color de UI, y `--koi` no entra al arte.
- [ ] Usable a 360 px sin scroll horizontal.

Si una instrucción mía choca con estas reglas, dímelo antes de escribir el código.
````
