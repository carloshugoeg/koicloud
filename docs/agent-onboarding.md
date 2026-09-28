# Cómo arrancar con tu agente en KoiCloud

Esto es lo único que tenés que leer antes de escribir tu primera línea de código. No hace
falta que leas el pack de arquitectura: el repositorio se lo explica solo a tu agente.

La idea del montaje es simple. Todo el contexto —quién sos, qué te toca, qué no podés
tocar, cómo se prueba, cómo se firma— vive **dentro del repositorio**, en `AGENTS.md` y en
`docs/tickets/`. Vos abrís el repo, decís tu nombre, y el agente hace el resto.

| Persona | Workstream | Herramienta |
|---|---|---|
| Carlos | W1 — núcleo y data plane | Cursor |
| Jason | W2 — web | Antigravity |
| Jousé | W3 — cuentas y dinero | Antigravity |
| Diego | W4 — superficies y operación | Antigravity |

---

## 1. Preparación, una sola vez por máquina

```bash
git clone https://github.com/carloshugoeg/koicloud.git
cd koicloud

# Tu identidad: cada quien firma su propio trabajo con su cuenta real de GitHub.
git config user.name  "Nombre Apellido"
git config user.email "correo-de-tu-cuenta-de-github"
git config --get user.email     # verificá que salga el tuyo

make up && make migrate && make seed
```

Sobre el correo: usá el de tu cuenta de GitHub, o su `noreply`
(`ID+handle@users.noreply.github.com`, lo encontrás en *Settings → Emails*) si preferís no
publicarlo. Cuenta igual para la atribución y para tu gráfico de contribuciones.

**«Equipo KoiCloud» es el nombre del equipo, no una identidad de git.** Aparece en el
README, en los documentos de entrega y en la interfaz; nunca como autor de un commit.
Cada commit lleva el nombre de quien lo hizo.

---

## 2. Si usás Antigravity (Jason, Jousé, Diego)

1. Abrí la carpeta del repositorio como workspace (*File → Open Folder*).
2. Confirmá que las reglas del repo están cargadas: en el panel del agente, `…` →
   **Customizations → Rules**. Deberías ver las reglas de `.agents/rules/`:
   `00-harness` en **Always On**, y `10-api`, `20-web`, `30-node-agent`, `40-cli-mcp` y
   `visual` en **Glob**.
   Si aparecen pero sin activación, fijala a mano ahí mismo: es un clic por regla y se hace
   una sola vez. Si no aparecen, revisá que abriste la raíz del repo y no una subcarpeta.
3. Abrí un chat nuevo y escribí:

```
Soy Jason. ¿Qué me toca y ejecútalo?
```

Antigravity también lee `AGENTS.md` y `GEMINI.md` de la raíz. Las reglas de `.agents/rules/`
están porque el IDE no siempre garantiza esa lectura: entre las dos vías, siempre llega.

---

## 3. Si usás Cursor (Carlos)

1. Abrí la carpeta del repositorio.
2. Cursor lee `AGENTS.md` completo por su cuenta y carga `.cursor/rules/` sin configuración.
3. Abrí un chat nuevo y escribí lo mismo:

```
Soy Carlos. ¿Qué me toca y ejecútalo?
```

Un detalle solo de Cursor: los agentes en la nube crean ramas con prefijo `cursor/`. Nuestra
convención es `wN-slug` (ver [`branch-naming.md`](./branch-naming.md)). La regla
`00-harness.mdc` ya se lo dice al agente; si igual te crea una rama `cursor/…`, pedile que
la renombre antes del PR.

---

## 4. El prompt de arranque

Es siempre el mismo, en cualquiera de las dos herramientas:

```
Soy {nombre}. ¿Qué me toca y ejecútalo?
```

Si querés ser explícito, o el agente se despistó en una conversación larga, la versión
larga dice lo mismo con más señales:

```
Soy {nombre}. Leé AGENTS.md completo, decime qué ticket me toca según
docs/tickets/, y ejecutalo siguiendo el protocolo de AGENTS.md §1.
```

No hace falta pegar el ticket, ni la guía visual, ni el pack de arquitectura. Todo eso ya
está en el repositorio y el agente sabe cuándo abrirlo. Pegar cosas de más es la forma más
rápida de que el agente se confunda sobre cuál es la fuente de verdad.

---

## 5. Qué va a pasar (y en qué momento te toca a vos)

1. **Te identifica.** Nombre → workstream → tu carpeta de tickets.
2. **Busca tu ticket:** el de número más bajo con `estado: abierto` en `docs/tickets/<wN>/`.
   Podés verlo vos mismo con `bash scripts/what-do-i-do.sh Jason`.
3. **Revisa que el ticket esté completo.** `BLOQUEADO` solo si hay que *editar* un
   contrato congelado o un archivo ajeno. Si el comando ya existe, el agente lo llama.
   Si `depends_on` no aterrizó, contesta `ESPERA` (no CCR). Un `BLOQUEADO` porque
   `users` vive en `core/` es un ticket mal leído, no un muro real.
4. **Crea la rama** `wN-slug` que el propio ticket declara.
5. **Te muestra un plan de 5 a 15 líneas:** qué archivos va a tocar, qué hace cada uno, qué
   pruebas va a escribir. ← **Acá te toca a vos.** Leelo. Si los archivos están dentro de tu
   zona y el plan cubre los criterios de aceptación, respondé `dale`. Si ves un archivo que
   no debería tocar, decíselo antes de que escriba nada. Es una sola confirmación, no una
   negociación; y te ahorra el PR que hay que rehacer entero.
6. **Implementa, corre `make check-<área>` y abre el PR** con la plantilla llena.

---

## 6. Las respuestas que vas a ver seguido

**«BLOQUEADO: requiere CCR porque …»** — tu ticket necesita cambiar algo congelado (un
endpoint, un campo, una tabla, la firma de un comando). No le insistas ni le pidas que lo
resuelva igual: abrí el issue con la plantilla `ccr.md` y avisale a Carlos. Un contrato que
cambia sin avisar rompe el trabajo de otras dos personas.

**«BLOQUEADO: requiere ticket para W1 porque …»** — necesitás *editar* un archivo de
otro. Se pide, no se escribe. Llamar `register_user` no es editar W1.

**«ESPERA: depends on W1-XX»** — el prerrequisito no está `hecho`/`cerrado`. No abras
CCR. Hacé `git pull origin main` cuando aterrice.

**«No hay ningún ticket con `estado: abierto`»** — no hay trabajo escrito para vos todavía.
Mirá `docs/tickets/<wN>/00-INDEX.md` para ver el plan de tu workstream y pedí el siguiente
ticket. **No empieces trabajo sin ticket**: sin criterios de aceptación no hay forma de que
el PR pase revisión.

---

## 7. Cinco cosas que no hay que hacer

1. **No le pidas que invente** un endpoint, un campo, una tabla, un código de error o una
   pantalla que no esté en el ticket. Si falta, la respuesta correcta es `BLOQUEADO`.
2. **No lo dejes tocar archivos fuera de tu workstream.** CI lo rechaza igual, pero es una
   hora perdida. Las rutas de cada quien están en `docs/WORKSTREAMS.md`.
3. **No aceptes un PR sin la salida real de `make check`.** Si el agente la resume o la
   inventa, pedísela otra vez corrida de verdad.
4. **No dejes que agregue dependencias** que el ticket no nombra.
5. **No dejes trailers de herramienta en los commits.** Nada de `Co-authored-by: Cursor`,
   `Co-authored-by: Gemini`, «Generated with…». Si tu herramienta los agrega sola, pedile
   que los quite antes de commitear y revisá con `git log -1 --format=%B`.

---

## 8. Antes de abrir el PR

Corré esto y leé lo que sale:

```bash
make check-web        # o check-api · check-agent · check-cli, según tu área
git log --format='%an <%ae>' origin/main..HEAD | sort -u    # ¿sos vos?
git log origin/main..HEAD | grep -i 'co-authored-by\|generated with'   # no debería salir nada
```

Después llená la plantilla de PR completa: ticket, qué cambia, criterios de aceptación
cubiertos, cómo probaste el caso feliz a mano, la salida real de `make check`, decisiones y
dependencias. Un PR = un ticket, ≤ 500 líneas netas.

Y lo último, que no lo revisa ninguna máquina: **tenés que poder explicar qué hace tu código
y por qué así, sin leer**. La exposición final evalúa exactamente eso, y un PR que su dueño
no puede explicar es un PR que no está terminado.
