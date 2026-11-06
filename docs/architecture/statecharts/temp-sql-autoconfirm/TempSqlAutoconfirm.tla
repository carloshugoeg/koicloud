---- MODULE TempSqlAutoconfirm ----
\* Demo S4 (#205): temporary pond-access actors auto-confirm safe writes
\* through run_sql, while dangerous statements, privilege changes, long
\* queries, and rate-limit breaches stay denied. Non-temp actors keep the
\* propose → confirm round-trip.

EXTENDS Integers

VARIABLES
  actor,          \* temp | account
  statement,      \* safe_write | dangerous | privilege | long_running | read
  phase,          \* idle | confirm | running | success | blocked | timed_out | rate_limited
  rateCount,      \* calls already spent in the current window
  lastOutcome     \* none | executed | confirmation_required | blocked | timed_out | rate_limited

vars == <<actor, statement, phase, rateCount, lastOutcome>>

Actors == {"temp", "account"}
Statements == {"safe_write", "dangerous", "privilege", "long_running", "read"}
Phases == {"idle", "confirm", "running", "success", "blocked", "timed_out", "rate_limited"}
Outcomes == {"none", "executed", "confirmation_required", "blocked", "timed_out", "rate_limited"}

MaxRate == 2

TypeOK ==
  /\ actor \in Actors
  /\ statement \in Statements
  /\ phase \in Phases
  /\ rateCount \in 0..MaxRate
  /\ lastOutcome \in Outcomes

Init ==
  /\ actor = "temp"
  /\ statement = "safe_write"
  /\ phase = "idle"
  /\ rateCount = 0
  /\ lastOutcome = "none"

\* Presenter switches which kind of actor will call run_sql next.
PickTemp ==
  /\ phase = "idle"
  /\ actor' = "temp"
  /\ UNCHANGED <<statement, phase, rateCount, lastOutcome>>

PickAccount ==
  /\ phase = "idle"
  /\ actor' = "account"
  /\ UNCHANGED <<statement, phase, rateCount, lastOutcome>>

\* Choose the statement the actor is about to send.
\* Clear lastOutcome so a prior Success does not stain the new pick.
PickSafeWrite ==
  /\ phase = "idle"
  /\ statement' = "safe_write"
  /\ lastOutcome' = "none"
  /\ UNCHANGED <<actor, phase, rateCount>>

PickDangerous ==
  /\ phase = "idle"
  /\ statement' = "dangerous"
  /\ lastOutcome' = "none"
  /\ UNCHANGED <<actor, phase, rateCount>>

PickPrivilege ==
  /\ phase = "idle"
  /\ statement' = "privilege"
  /\ lastOutcome' = "none"
  /\ UNCHANGED <<actor, phase, rateCount>>

PickLongRunning ==
  /\ phase = "idle"
  /\ statement' = "long_running"
  /\ lastOutcome' = "none"
  /\ UNCHANGED <<actor, phase, rateCount>>

PickRead ==
  /\ phase = "idle"
  /\ statement' = "read"
  /\ lastOutcome' = "none"
  /\ UNCHANGED <<actor, phase, rateCount>>

\* Window resets between demo bursts.
ResetRateWindow ==
  /\ phase = "idle"
  /\ rateCount' = 0
  /\ UNCHANGED <<actor, statement, phase, lastOutcome>>

\* Account actor writing: propose only (confirmation_required).
ProposeConfirm ==
  /\ phase = "idle"
  /\ actor = "account"
  /\ statement = "safe_write"
  /\ phase' = "confirm"
  /\ lastOutcome' = "confirmation_required"
  /\ UNCHANGED <<actor, statement, rateCount>>

\* Human confirms the pending write.
ConfirmWrite ==
  /\ phase = "confirm"
  /\ phase' = "running"
  /\ UNCHANGED <<actor, statement, rateCount, lastOutcome>>

\* Cancel or Esc leaves the write unsent.
CancelConfirm ==
  /\ phase = "confirm"
  /\ phase' = "idle"
  /\ lastOutcome' = "none"
  /\ UNCHANGED <<actor, statement, rateCount>>

\* Temp actor: rate limit blocks before execution.
HitRateLimit ==
  /\ phase = "idle"
  /\ actor = "temp"
  /\ rateCount = MaxRate
  /\ phase' = "rate_limited"
  /\ lastOutcome' = "rate_limited"
  /\ UNCHANGED <<actor, statement, rateCount>>

\* Temp actor: dangerous statement rejected, never runs.
BlockDangerous ==
  /\ phase = "idle"
  /\ actor = "temp"
  /\ statement = "dangerous"
  /\ rateCount < MaxRate
  /\ phase' = "blocked"
  /\ lastOutcome' = "blocked"
  /\ rateCount' = rateCount + 1
  /\ UNCHANGED <<actor, statement>>

\* Temp actor: GRANT/REVOKE/ALTER ROLE rejected, never runs.
BlockPrivilege ==
  /\ phase = "idle"
  /\ actor = "temp"
  /\ statement = "privilege"
  /\ rateCount < MaxRate
  /\ phase' = "blocked"
  /\ lastOutcome' = "blocked"
  /\ rateCount' = rateCount + 1
  /\ UNCHANGED <<actor, statement>>

\* Temp actor: safe write auto-confirms and starts running.
AutoRunSafeWrite ==
  /\ phase = "idle"
  /\ actor = "temp"
  /\ statement = "safe_write"
  /\ rateCount < MaxRate
  /\ phase' = "running"
  /\ rateCount' = rateCount + 1
  /\ lastOutcome' = "none"
  /\ UNCHANGED <<actor, statement>>

\* Temp actor: long-running SQL starts then times out.
AutoRunLong ==
  /\ phase = "idle"
  /\ actor = "temp"
  /\ statement = "long_running"
  /\ rateCount < MaxRate
  /\ phase' = "running"
  /\ rateCount' = rateCount + 1
  /\ lastOutcome' = "none"
  /\ UNCHANGED <<actor, statement>>

\* Reads never need confirm (either actor).
RunRead ==
  /\ phase = "idle"
  /\ statement = "read"
  /\ actor = "temp" => rateCount < MaxRate
  /\ phase' = "running"
  /\ rateCount' = IF actor = "temp" THEN rateCount + 1 ELSE rateCount
  /\ lastOutcome' = "none"
  /\ UNCHANGED <<actor, statement>>

\* Account actor may also attempt a blocked statement via confirm path;
\* model them as blocked at propose time for clarity of the chart.
AccountBlockDangerous ==
  /\ phase = "idle"
  /\ actor = "account"
  /\ statement \in {"dangerous", "privilege"}
  /\ phase' = "blocked"
  /\ lastOutcome' = "blocked"
  /\ UNCHANGED <<actor, statement, rateCount>>

Succeed ==
  /\ phase = "running"
  /\ statement \in {"safe_write", "read"}
  /\ phase' = "success"
  /\ lastOutcome' = "executed"
  /\ UNCHANGED <<actor, statement, rateCount>>

Timeout ==
  /\ phase = "running"
  /\ statement = "long_running"
  /\ phase' = "timed_out"
  /\ lastOutcome' = "timed_out"
  /\ UNCHANGED <<actor, statement, rateCount>>

\* Return to idle after a terminal outcome so the demo can retry.
Ack ==
  /\ phase \in {"success", "blocked", "timed_out", "rate_limited"}
  /\ phase' = "idle"
  /\ UNCHANGED <<actor, statement, rateCount, lastOutcome>>

Done ==
  /\ phase = "idle"
  /\ UNCHANGED vars

Next ==
  \/ PickTemp
  \/ PickAccount
  \/ PickSafeWrite
  \/ PickDangerous
  \/ PickPrivilege
  \/ PickLongRunning
  \/ PickRead
  \/ ResetRateWindow
  \/ ProposeConfirm
  \/ ConfirmWrite
  \/ CancelConfirm
  \/ HitRateLimit
  \/ BlockDangerous
  \/ BlockPrivilege
  \/ AutoRunSafeWrite
  \/ AutoRunLong
  \/ RunRead
  \/ AccountBlockDangerous
  \/ Succeed
  \/ Timeout
  \/ Ack
  \/ Done

Spec == Init /\ [][Next]_vars

\* --- Invariants the demo and the tests must keep ---

\* Account safe writes reach Running only after confirmation_required.
AccountRunningImpliesPriorConfirm ==
  (actor = "account" /\ statement = "safe_write" /\ phase = "running")
    => lastOutcome = "confirmation_required"

\* Dangerous never executes.
DangerousNeverExecutes ==
  ~(statement = "dangerous" /\ lastOutcome = "executed")

\* Privilege changes never execute.
PrivilegeNeverExecutes ==
  ~(statement = "privilege" /\ lastOutcome = "executed")

\* Temp safe write never stalls on confirmation_required.
TempSafeWriteNeverConfirms ==
  ~(actor = "temp" /\ statement = "safe_write" /\ lastOutcome = "confirmation_required")

\* Rate-limited outcome never coexists with executed for that same call.
RateLimitMeansNotExecuted ==
  ~(lastOutcome = "rate_limited" /\ phase = "success")

\* Long-running under temp ends as timed_out, not success.
LongRunningNeverSucceeds ==
  ~(statement = "long_running" /\ lastOutcome = "executed")

====
