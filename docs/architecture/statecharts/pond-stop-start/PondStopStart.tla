---- MODULE PondStopStart ----
\* CCR 131 pond stop/start. UI phases: running, stopping, stopped,
\* starting, error, provisioning. Wrong-state and in-flight POSTs stay
\* put and answer 409 pond_busy (documented beside the chart; no phase change).

EXTENDS Naturals

VARIABLE phase
vars == <<phase>>

phases == {
  "running",
  "stopping",
  "stopped",
  "starting",
  "error",
  "provisioning"
}

TypeOK == phase \in phases

Init == phase = "running"

PostStop ==
    /\ phase = "running"
    /\ phase' = "stopping"

StopOk ==
    /\ phase = "stopping"
    /\ phase' = "stopped"

StopFailed ==
    /\ phase = "stopping"
    /\ phase' = "error"

PostStart ==
    /\ phase \in {"stopped", "error"}
    /\ phase' = "starting"

StartOk ==
    /\ phase = "starting"
    /\ phase' = "running"

StartFailed ==
    /\ phase = "starting"
    /\ phase' = "error"

Retry ==
    /\ phase = "error"
    /\ phase' = "provisioning"

ProvisionOk ==
    /\ phase = "provisioning"
    /\ phase' = "running"

ProvisionFailed ==
    /\ phase = "provisioning"
    /\ phase' = "error"

\* Terminal sink so CHECK_DEADLOCK does not flag stopped/running forever.
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
    \/ Retry
    \/ ProvisionOk
    \/ ProvisionFailed
    \/ Idle

Spec == Init /\ [][Next]_vars

\* Reachable happy path never jumps over stopping/starting.
NoTeleportStop == ~(phase = "running" /\ phase' = "stopped")
NoTeleportStart == ~(phase = "stopped" /\ phase' = "running")
====
