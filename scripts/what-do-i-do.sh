#!/usr/bin/env bash
# ¿Qué me toca? — resuelve nombre → workstream → siguiente ticket listo.
#
#   bash scripts/what-do-i-do.sh Jason
#
# Toma el ticket de número más bajo con `estado: abierto` cuyos `depends_on`
# estén `hecho` o `cerrado`. Si el más bajo espera un prerrequisito, imprime
# ESPERA (no BLOQUEADO / CCR). No modifica nada.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TICKETS="$ROOT/docs/tickets"

if [ $# -lt 1 ]; then
  echo "Uso: bash scripts/what-do-i-do.sh <nombre>"
  echo "Nombres: Carlos · Jason · Jousé · Diego"
  exit 2
fi

nombre_lower="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"

case "$nombre_lower" in
  carlos*|hugo*)
    ws=w1; persona="Carlos"; area="núcleo y data plane"
    rutas="todas (W1 puede tocar cualquier ruta)" ;;
  jason*)
    ws=w2; persona="Jason"; area="web"
    rutas="apps/web/** y docs/tickets/w2/**" ;;
  jous*)
    ws=w3; persona="Jousé"; area="cuentas y dinero"
    rutas="apps/api/app/modules/{auth,users,billing,notifications,admin}/** y docs/tickets/w3/**" ;;
  diego*)
    ws=w4; persona="Diego"; area="superficies y operación"
    rutas="apps/cli/**, mcp lectura, sql_console, infra, load, manuales y docs/tickets/w4/**" ;;
  *)
    echo "No conozco a «$1». Nombres válidos: Carlos · Jason · Jousé · Diego."
    echo "Si eres nuevo en el equipo, pide que te agreguen a AGENTS.md §1 y a docs/WORKSTREAMS.md."
    exit 2 ;;
esac

dir="$TICKETS/$ws"
if [ ! -d "$dir" ]; then
  echo "No existe $dir. ¿Estás en la raíz del repo?"
  exit 1
fi

next_out="$(python3 "$ROOT/scripts/ticket_prereqs.py" next "$1")"
kind="$(printf '%s\n' "$next_out" | sed -n '1p')"
kind="${kind:-NONE}"

echo "Persona:    $persona"
ws_upper="$(printf '%s' "$ws" | tr '[:lower:]' '[:upper:]')"
echo "Workstream: $ws_upper — $area"
echo "Tickets:    docs/tickets/$ws/"
echo "Puede tocar: $rutas"
echo

if [ "$kind" = "NONE" ]; then
  echo "No hay ningún ticket con \`estado: abierto\` en docs/tickets/$ws/."
  echo "Mirá docs/tickets/$ws/00-INDEX.md para el plan del workstream, y pedí que escriban"
  echo "el siguiente ticket. No empieces trabajo sin ticket."
  exit 0
fi

if [ "$kind" = "ESPERA" ]; then
  echo "ESPERA: el ticket más bajo todavía depende de otro que no está hecho/cerrado."
  echo "No abras CCR. No declares BLOQUEADO. Hacé fetch de main cuando aterrice el prerrequisito."
  echo
  printf '%s\n' "$next_out" | sed -n '2,$s/^/  - /p'
  exit 0
fi

rel="$kind"
ticket="$ROOT/$rel"
titulo="$(grep -m1 '^# ' "$ticket" | sed 's/^# //')"
rama="$(printf '%s\n' "$next_out" | sed -n '3p')"
deps="$(printf '%s\n' "$next_out" | sed -n '4p')"

echo "Te toca:  $titulo"
echo "Archivo:  $rel"
echo "Rama:     $rama"
if [ -n "$deps" ]; then
  echo "Depends:  $deps (ya hecho/cerrado)"
fi
echo
echo "Siguiente paso, en este orden:"
echo "  1. Leé AGENTS.md completo (sobre todo §1 paso 3: cuándo BLOQUEADO vs ESPERA vs llamar)."
echo "  2. Leé $rel completo y verificá que trae las seis secciones."
echo "     BLOQUEADO solo si hay que *editar* un contrato congelado o un archivo ajeno."
echo "     Si el comando ya existe en app/commands, llamalo. No es BLOQUEADO."
echo "  3. Leé solo las secciones de docs/architecture/ que el ticket cita."
if [ "$ws" = "w2" ]; then
  echo "     Además, por ser W2: docs/visual-guidelines.md (la piel es obligatoria)."
fi
echo "  4. git checkout -b $rama"
echo "  5. Verificá tu identidad de git: git config --get user.email"
echo "  6. Escribí un plan de 5 a 15 líneas y esperá el 'dale'."
echo "  7. Implementá, corré 'make check-<área>' y abrí el PR con la plantilla llena."
