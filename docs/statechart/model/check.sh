#!/usr/bin/env bash
# Re-run the KoiCloud pond/journey TLA+ models with plain TLC.
# Needs Java 11+ and tla2tools.jar (TLA2TOOLS env var, default ./tla2tools.jar; v1.8.0).
# Exit 0 only if PondLifecycle and UserJourneyFixed hold and UserJourneyAsIs still shows its known findings.
set -uo pipefail
cd "$(dirname "$0")"
JAR="${TLA2TOOLS:-./tla2tools.jar}"
[ -f "$JAR" ] || curl -fsSL -o "$JAR" https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar
tlc() { java -XX:+UseParallelGC -cp "$JAR" tlc2.TLC -metadir "${TMPDIR:-/tmp}/koi-tlc-$$" -noGenerateSpecTE -workers 1 -deadlock -continue -config "$2" "$1" 2>&1; }
fail=0
for run in "PondLifecycle.tla PondLifecycle.cfg" "UserJourney.tla UserJourneyFixed.cfg" "System.tla SystemFixed.cfg"; do
  set -- $run; out=$(tlc "$1" "$2")
  if echo "$out" | grep -q "No error has been found"; then echo "PASS $2"; else echo "FAIL $2"; echo "$out" | grep -E "violated|Error" | sort -u; fail=1; fi
done
echo "AS-IS findings on main (expected until #96 r6 ships):"
for inv in TabsFixedOrder HistoryScoped ReloadKeepsSession PlansViaBilling NoChargeBadCard LogoutRevokesAccess; do
  printf 'CONSTANT Fixed = FALSE\nSPECIFICATION Spec\nINVARIANT %s\n' "$inv" > /tmp/koi-asis.cfg
  if tlc UserJourney.tla /tmp/koi-asis.cfg | grep -q "is violated"; then echo "  BREAKS $inv"; else echo "  holds  $inv"; fi
done
echo "AS-IS cross-subsystem findings on main:"
for inv in NoPondApiWhenLoggedOut NoPondApiWhenSuspended AgentScopeWithinOwner DeletedPondHasNoJobs DeletedPondAccruesNoUsage; do
  printf 'CONSTANT Fixed = FALSE\nSPECIFICATION Spec\nINVARIANT %s\n' "$inv" > /tmp/koi-asis.cfg
  if tlc System.tla /tmp/koi-asis.cfg | grep -q "is violated"; then echo "  BREAKS $inv"; else echo "  holds  $inv"; fi
done
exit $fail
