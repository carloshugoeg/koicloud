#!/usr/bin/env bash
# ¿Qué me toca? — resuelve nombre → workstream → siguiente ticket abierto.
#
#   bash scripts/what-do-i-do.sh Jason
#
# Imprime el ticket de número más bajo con `estado: abierto` en docs/tickets/<wN>/,
# su rama y sus rutas prohibidas. No modifica nada. La regla completa está en
# AGENTS.md §1 y en docs/tickets/README.md.

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
    rutas="apps/web/** — y nada fuera de ahí" ;;
  jous*)
    ws=w3; persona="Jousé"; area="cuentas y dinero"
    rutas="apps/api/app/modules/{auth,users,billing,notifications,admin}/**" ;;
  diego*)
    ws=w4; persona="Diego"; area="superficies y operación"
    rutas="apps/api/app/modules/sql_console/**, apps/api/app/mcp/** (solo tools de lectura), apps/cli/**, infra/**, load/**, manuales" ;;
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

ticket=""
for f in $(ls -1 "$dir" | grep -E '^W[0-9]-[0-9]+-.*\.md$' | sort); do
  if grep -qE '^estado:[[:space:]]*abierto[[:space:]]*$' "$dir/$f"; then
    ticket="$dir/$f"
    break
  fi
done

echo "Persona:    $persona"
ws_upper="$(printf '%s' "$ws" | tr '[:lower:]' '[:upper:]')"
echo "Workstream: $ws_upper — $area"
echo "Tickets:    docs/tickets/$ws/"
echo "Puede tocar: $rutas"
echo

if [ -z "$ticket" ]; then
  echo "No hay ningún ticket con \`estado: abierto\` en docs/tickets/$ws/."
  echo "Mirá docs/tickets/$ws/00-INDEX.md para el plan del workstream, y pedí que escriban"
  echo "el siguiente ticket. No empieces trabajo sin ticket."
  exit 0
fi

rel="${ticket#"$ROOT"/}"
titulo="$(grep -m1 '^# ' "$ticket" | sed 's/^# //')"
rama="$(grep -m1 '^rama:' "$ticket" | sed 's/^rama:[[:space:]]*//')"

echo "Te toca:  $titulo"
echo "Archivo:  $rel"
echo "Rama:     $rama"
echo
echo "Siguiente paso, en este orden:"
echo "  1. Leé AGENTS.md completo."
echo "  2. Leé $rel completo y verificá que trae las seis secciones."
echo "     Si falta una, o pide tocar algo congelado o ajeno: respondé"
echo "     'BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>' y pará."
echo "  3. Leé solo las secciones de docs/architecture/ que el ticket cita."
if [ "$ws" = "w2" ]; then
  echo "     Además, por ser W2: docs/visual-guidelines.md (la piel es obligatoria)."
fi
echo "  4. git checkout -b $rama"
echo "  5. Verificá tu identidad de git: git config --get user.email"
echo "  6. Escribí un plan de 5 a 15 líneas y esperá el 'dale'."
echo "  7. Implementá, corré 'make check-<área>' y abrí el PR con la plantilla llena."
