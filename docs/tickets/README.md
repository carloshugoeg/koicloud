# Tickets — cómo se archivan y cómo se resuelve «¿qué me toca?»

Los tickets del sprint viven **aquí, en el repositorio**, no en la cabeza de nadie ni en un
chat. Eso es lo que permite que un agente conteste «¿qué me toca?» sin que le expliquen el
proyecto cada vez.

GitHub Issues y el tablero siguen existiendo: son la vista pública del avance. El archivo de
este directorio es la **fuente que lee el agente**, y el issue enlaza a él.

---

## 1. Dónde está cada ticket

```
docs/tickets/
├── README.md          ← este archivo
├── w1/                ← Carlos (núcleo y data plane)
├── w2/                ← Jason (web)
├── w3/                ← Jousé (cuentas y dinero)
└── w4/                ← Diego (superficies y operación)
```

Un archivo por ticket: `docs/tickets/<wN>/<ID>-<slug>.md`
→ `docs/tickets/w2/W2-06-detalle-pond.md`.

El **slug es también el nombre de la rama**: `w2-detalle-pond`. No hay que inventarlo.

---

## 2. Frontmatter obligatorio

```yaml
---
id: W2-06
workstream: W2
persona: Jason
estado: abierto          # abierto | en-curso | en-revision | hecho | bloqueado | cerrado
rama: w2-detalle-pond
epica: E3-03             # id de docs/architecture/feature-breakdown.md §1
sprint: S2
pr:                      # se llena con la URL al abrir el PR
depends_on:              # IDs hechos/cerrados, o vacío. Ej: W1-15
---
```

Ciclo del campo `estado`:

| Estado | Qué significa | Quién lo cambia |
|---|---|---|
| `abierto` | Escrito, revisado y listo para trabajarse | quien escribe el ticket |
| `en-curso` | Alguien tiene rama abierta sobre él | el agente, en el primer commit |
| `en-revision` | PR abierto, esperando CI y revisión | el agente, al abrir el PR |
| `hecho` | PR fusionado en `main` | quien fusiona |
| `cerrado` | Trabajo ya en `main` (ticket escrito después) | W1 |
| `bloqueado` | Espera un CCR o un ticket de otro workstream | el agente, con la razón en el cuerpo |

`depends_on:` es una lista de IDs separados por espacio. `what-do-i-do.sh` y
`scripts/ticket_prereqs.py` saltean el ticket hasta que esos IDs estén `hecho` o
`cerrado`. Eso se responde `ESPERA`, no `BLOQUEADO` ni CCR.

El cambio de estado se commitea **en la misma rama del ticket**; es la única edición fuera
de tu workstream que está permitida, y solo sobre tu propio archivo de ticket.

---

## 3. Las seis secciones (un ticket sin las seis no se trabaja)

1. **Qué se ve** — el resultado observable. Qué muestra la pantalla, qué responde el
   endpoint, qué imprime el comando. Con referencia al mockup o al ejemplo del contrato.
2. **Entradas ya decididas (no se cambian)** — ruta exacta, hooks o firmas que ya existen,
   tipos, códigos de error a manejar, textos. Todo lo que el agente **no** debe decidir.
3. **Criterios de aceptación** — numerados y verificables uno por uno. Cada uno debe poder
   comprobarse con una prueba automática o con un paso manual concreto.
4. **No tocar** — lista explícita de archivos y rutas prohibidas para este ticket.
5. **Si algo falta** — el texto genérico se queda. `BLOQUEADO` **solo** si hay que
   *editar* un contrato congelado o un archivo ajeno. Si el comando ya existe,
   el agente lo llama. Si `depends_on` no aterrizó, responde `ESPERA`.
6. **Referencia** — el PR de ejemplo a imitar en estructura de archivos y estilo de pruebas.

En *Entradas* o *Criterios*, si el resultado persistido lo hace un comando de W1,
escribí «Depends on W1-XX landed. Call `nombre_del_comando` only.» No pidas que
W3 o W2 toquen `core/` para cumplir un CA de persistencia.

Si al escribir un ticket hay que explicar *por qué* algo funciona así, el ticket todavía no
está listo para delegarse: descríbelo por *qué debe verse*, no por cómo razonar.

Plantilla lista para copiar: [`W0-00-plantilla.md`](./W0-00-plantilla.md).

---

## 4. Cómo resuelve el agente «¿qué me toca?»

1. Traduce el nombre a workstream con la tabla de `AGENTS.md` §1.
2. Lista `docs/tickets/<wN>/*.md` y toma el de **número más bajo con `estado: abierto`**
   cuyos `depends_on` estén `hecho` o `cerrado`.
3. Si ese ticket no trae las seis secciones, o exige *editar* algo congelado o ajeno,
   responde `BLOQUEADO: …` y se detiene. Si solo espera un prerrequisito, responde
   `ESPERA` y se detiene. **No rellena huecos con suposiciones.** Llamar un comando
   que ya existe no es un hueco.
4. Si está completo y listo: crea la rama `<rama>` del frontmatter, marca
   `estado: en-curso`, escribe un plan de 5–15 líneas y espera el «dale».

Atajo equivalente, para que nadie tenga que leer el directorio a mano:

```bash
bash scripts/what-do-i-do.sh Jason
```

Imprime el ticket que sigue, su rama y sus rutas prohibidas.

---

## 5. Quién escribe los tickets

Los escribe W1 **antes** de que empiece el sprint, no sobre la marcha. Un ticket que se
escribe tarde cuesta más caro que uno que se escribe bien: el agente que lo recibe incompleto
inventa endpoints, inventa campos y produce un PR que hay que rehacer entero.

Si necesitas algo de la zona de otro workstream, no lo escribas tú: abre un issue con la
plantilla `ticket.md` pidiéndolo, o un `ccr.md` si lo que hace falta es cambiar un contrato.
