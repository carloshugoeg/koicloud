---------------------------- MODULE PondLifecycle ----------------------------
(* One pond, its lifecycle jobs and its SQL console.
   Code: apps/api (POST /ponds, /stop, /start, /retry, /backups, /restore,
   DELETE /ponds/{id}, POST /ponds/{id}/sql), apps/node-agent/agent/handlers/*,
   apps/web/src/features/ponds/pond-lifecycle-actions.tsx, pond-state.ts.
   One API request or one job completion = one atomic step. *)
EXTENDS Naturals

VARIABLES
  obs,        \* observed_state shown to the user (pond-state.ts + transitional r3 states)
  jobs,       \* lifecycle jobs in flight for this pond
  wasDeleted, \* ghost: the pond reached "deleted" at some point
  lastSql     \* "none" | "ok" | "rejected" (409 pond_not_running) | "ran_while_not_running"

vars == <<obs, jobs, wasDeleted, lastSql>>

Transitional == {"provisioning", "stopping", "starting", "backing_up", "restoring", "deleting"}

Init == obs = "none" /\ jobs = 0 /\ wasDeleted = FALSE /\ lastSql = "none"

\* API accepts a lifecycle request only from the right state with no job in flight (409 pond_busy otherwise).
Accept(from, to) == obs \in from /\ jobs = 0 /\ obs' = to /\ jobs' = jobs + 1 /\ UNCHANGED <<wasDeleted, lastSql>>
Finish(from, to) == obs = from /\ jobs >= 1 /\ obs' = to /\ jobs' = jobs - 1 /\ UNCHANGED <<wasDeleted, lastSql>>

YouCreate        == Accept({"none"}, "provisioning")
ProvisionOk      == Finish("provisioning", "running")
ProvisionFails   == Finish("provisioning", "failed")
YouRetry         == Accept({"failed"}, "provisioning")
YouStop          == Accept({"running"}, "stopping")
StopOk           == Finish("stopping", "stopped")
StopFails        == Finish("stopping", "failed")
YouStart         == Accept({"stopped"}, "starting")
StartOk          == Finish("starting", "running")
StartFails       == Finish("starting", "failed")
YouBackup        == Accept({"running"}, "backing_up")
BackupDone       == Finish("backing_up", "running")   \* failed backup row; pond stays running
YouRestore       == Accept({"running", "stopped", "failed"}, "restoring")  \* backups/service.py:67 has no observed-state guard
RestoreOk        == Finish("restoring", "running")
RestoreFails     == Finish("restoring", "failed")
YouDelete        == Accept({"running", "stopped", "failed"}, "deleting")
DeleteOk         == obs = "deleting" /\ jobs = 1 /\ obs' = "deleted" /\ jobs' = 0
                    /\ wasDeleted' = TRUE /\ UNCHANGED lastSql
\* Any lifecycle click while busy or in the wrong state: 409, nothing changes.
YouClickWhileBusy == obs # "none" /\ jobs = 1 /\ UNCHANGED vars
\* SQL console read/write: runs only on running pond; else 409 pond_not_running (r2 A4).
YouRunSql == obs \notin {"none", "deleted"} /\ UNCHANGED <<obs, jobs, wasDeleted>>
             /\ lastSql' = IF obs = "running" THEN "ok" ELSE "rejected"
Done == obs = "deleted" /\ UNCHANGED vars

Next == YouCreate \/ ProvisionOk \/ ProvisionFails \/ YouRetry \/ YouStop \/ StopOk \/ StopFails
     \/ YouStart \/ StartOk \/ StartFails \/ YouBackup \/ BackupDone \/ YouRestore \/ RestoreOk
     \/ RestoreFails \/ YouDelete \/ DeleteOk \/ YouClickWhileBusy \/ YouRunSql \/ Done

Spec == Init /\ [][Next]_vars

\* ---- Invariants ----
TypeOK == jobs \in 0..1
OneInFlightOp == jobs <= 1 /\ ((obs \in Transitional) <=> (jobs = 1))
NoStartOnDeleted == wasDeleted => obs = "deleted"
ConsoleOnlyWhenRunning == lastSql # "ran_while_not_running"
=============================================================================
