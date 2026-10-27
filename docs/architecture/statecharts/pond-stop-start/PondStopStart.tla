---- MODULE PondStopStart ----
\* CCR 131 pond stop/start. Five UI phases only: running, stopping, stopped,
\* starting, error. Recovery from error is POST /retry by failed job type
\* (stop→stopping, start|create→starting). No pending / En cola / provisioning
\* in this chart. Wrong-state POSTs stay put with 409 pond_busy (documented
\* beside the chart; no phase change).

EXTENDS Naturals

VARIABLE phase, last_fail
vars == <<phase, last_fail>>

phases == {
  "running",
  "stopping",
  "stopped",
  "starting",
  "error"
}

fails == {"none", "stop", "start", "create"}

TypeOK ==
    /\ phase \in phases
    /\ last_fail \in fails

Init ==
    /\ phase = "running"
    /\ last_fail = "none"

PostStop ==
    /\ phase = "running"
    /\ phase' = "stopping"
    /\ UNCHANGED last_fail

StopOk ==
    /\ phase = "stopping"
    /\ phase' = "stopped"
    /\ last_fail' = "none"

StopFailed ==
    /\ phase = "stopping"
    /\ phase' = "error"
    /\ last_fail' = "stop"

PostStart ==
    /\ phase = "stopped"
    /\ phase' = "starting"
    /\ UNCHANGED last_fail

StartOk ==
    /\ phase = "starting"
    /\ phase' = "running"
    /\ last_fail' = "none"

StartFailed ==
    /\ phase = "starting"
    /\ phase' = "error"
    /\ last_fail' = "start"

CreateFailed ==
    /\ phase = "starting"
    /\ phase' = "error"
    /\ last_fail' = "create"

RetryStop ==
    /\ phase = "error"
    /\ last_fail = "stop"
    /\ phase' = "stopping"
    /\ UNCHANGED last_fail

RetryStart ==
    /\ phase = "error"
    /\ last_fail \in {"start", "create"}
    /\ phase' = "starting"
    /\ UNCHANGED last_fail

\* Seed a create-failure so RetryStart[create] is reachable (hidden in view).
SeedCreateError ==
    /\ phase = "running"
    /\ last_fail = "none"
    /\ phase' = "error"
    /\ last_fail' = "create"

Idle ==
    /\ phase \in {"running", "stopped"}
    /\ UNCHANGED vars

Next ==
    \/ PostStop
    \/ StopOk
    \/ StopFailed
    \/ PostStart
    \/ StartOk
    \/ StartFailed
    \/ CreateFailed
    \/ RetryStop
    \/ RetryStart
    \/ SeedCreateError
    \/ Idle

Spec == Init /\ [][Next]_vars

NoTeleportStop == ~(phase = "running" /\ phase' = "stopped")
NoTeleportStart == ~(phase = "stopped" /\ phase' = "running")
====
