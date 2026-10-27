---- MODULE PondStopStart ----
\* CCR 131 pond stop/start. UI phases: running, stopping, stopped,
\* starting, error, provisioning. Recovery from error is POST /retry,
\* which requeues the last failed job type (stop→stopping, start→starting,
\* create→provisioning). Wrong-state and in-flight POSTs stay put and
\* answer 409 pond_busy (documented beside the chart; no phase change).

EXTENDS Naturals

VARIABLE phase, last_fail
vars == <<phase, last_fail>>

phases == {
  "running",
  "stopping",
  "stopped",
  "starting",
  "error",
  "provisioning"
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

RetryStop ==
    /\ phase = "error"
    /\ last_fail = "stop"
    /\ phase' = "stopping"
    /\ UNCHANGED last_fail

RetryStart ==
    /\ phase = "error"
    /\ last_fail = "start"
    /\ phase' = "starting"
    /\ UNCHANGED last_fail

RetryCreate ==
    /\ phase = "error"
    /\ last_fail = "create"
    /\ phase' = "provisioning"
    /\ UNCHANGED last_fail

ProvisionOk ==
    /\ phase = "provisioning"
    /\ phase' = "running"
    /\ last_fail' = "none"

ProvisionFailed ==
    /\ phase = "provisioning"
    /\ phase' = "error"
    /\ last_fail' = "create"

\* Seed provisioning so create-fail → retry create is reachable from Init.
BeginProvision ==
    /\ phase = "running"
    /\ last_fail = "none"
    /\ phase' = "provisioning"
    /\ UNCHANGED last_fail

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
    \/ RetryStop
    \/ RetryStart
    \/ RetryCreate
    \/ ProvisionOk
    \/ ProvisionFailed
    \/ BeginProvision
    \/ Idle

Spec == Init /\ [][Next]_vars

\* Reachable happy path never jumps over stopping/starting.
NoTeleportStop == ~(phase = "running" /\ phase' = "stopped")
NoTeleportStart == ~(phase = "stopped" /\ phase' = "running")
====
