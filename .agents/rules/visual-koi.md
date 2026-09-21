---
trigger: glob
globs: apps/web/**
description: Estanque, movimiento y verificación de la piel visual
---

Continúa `visual.mdc`. Misma piel, misma obligación.

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
