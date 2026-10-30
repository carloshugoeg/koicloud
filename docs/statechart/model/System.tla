------------------------------- MODULE System -------------------------------
(* Level-1 cross-subsystem model: auth/session, admin suspend, agent access,
   ponds (coarse) + provisioning jobs, metering/billing.
   Fixed = FALSE models origin/main @ 72015b5; Fixed = TRUE the intended contract.
   jwt is the access token. refresh is the refresh token.
   Logout clears both. A pond call with the old access token does not succeed.
   Code: apps/api/app/core/auth.py:get_current_user (stateless JWT, status hard-coded ACTIVE),
   core/config.py access_token_ttl_minutes=15, commands/auth.py (login/refresh reject SUSPENDED;
   logout revokes the refresh row and the presented access jti),
   commands/admin.py:suspend_user (sets status only), modules/agent_access/service.py:authenticate
   (no user status check), modules/ponds/service.py, modules/metering/service.py:compute_day_metrics
   (tail after last sample counts as running), workers/reconciler.py. *)
EXTENDS Naturals
CONSTANT Fixed

VARIABLES session, jwt, refresh, status, agentOn, pond, jobs, lastSampleRunning,
          loggedOutCall, suspendedCall, agentBeyondOwner, usageAfterDelete
vars == <<session, jwt, refresh, status, agentOn, pond, jobs, lastSampleRunning,
          loggedOutCall, suspendedCall, agentBeyondOwner, usageAfterDelete>>
ghosts == <<loggedOutCall, suspendedCall, agentBeyondOwner, usageAfterDelete>>
infra == <<pond, jobs, lastSampleRunning>>

Init == session = "out" /\ jwt = FALSE /\ refresh = FALSE /\ status = "active" /\ agentOn = FALSE
     /\ pond = "none" /\ jobs = 0 /\ lastSampleRunning = FALSE
     /\ loggedOutCall = FALSE /\ suspendedCall = FALSE /\ agentBeyondOwner = FALSE /\ usageAfterDelete = FALSE

\* ---- Auth / session ----
UserLogsIn   == session = "out" /\ status = "active" /\ session' = "in" /\ jwt' = TRUE /\ refresh' = TRUE
                /\ UNCHANGED <<status, agentOn, infra, ghosts>>
UserLogsOut  == session = "in" /\ session' = "out" /\ refresh' = FALSE /\ jwt' = FALSE
                /\ UNCHANGED <<status, agentOn, infra, ghosts>>
TokenExpires == jwt /\ jwt' = FALSE /\ UNCHANGED <<session, refresh, status, agentOn, infra, ghosts>>
\* ---- Admin ----
AdminSuspends == status = "active" /\ status' = "suspended"
                 /\ (IF Fixed THEN session' = "out" /\ jwt' = FALSE /\ UNCHANGED refresh
                     ELSE UNCHANGED <<session, jwt, refresh>>)
                 /\ UNCHANGED <<agentOn, infra, ghosts>>
AdminReactivates == status = "suspended" /\ status' = "active" /\ UNCHANGED <<session, jwt, refresh, agentOn, infra, ghosts>>
\* ---- Agent access ----
UserTogglesAgent == session = "in" /\ agentOn' = ~agentOn /\ UNCHANGED <<session, jwt, refresh, status, infra, ghosts>>

\* ---- Pond API, reached by the web user (bearer JWT) or by the agent (slug + password) ----
UserApiOk  == jwt /\ (Fixed => status = "active")
AgentApiOk == agentOn /\ (Fixed => status = "active")
OwnerCould == status = "active"
CallEffects(ok, byAgent) ==
  /\ loggedOutCall'    = (loggedOutCall \/ (ok /\ ~byAgent /\ session = "out"))
  /\ suspendedCall'    = (suspendedCall \/ (ok /\ status = "suspended"))
  /\ agentBeyondOwner' = (agentBeyondOwner \/ (ok /\ byAgent /\ ~OwnerCould))
  /\ UNCHANGED usageAfterDelete

CreatesPond(byAgent) == pond = "none" /\ (IF byAgent THEN AgentApiOk ELSE UserApiOk)
   /\ pond' = "provisioning" /\ jobs' = 1 /\ UNCHANGED <<lastSampleRunning, session, jwt, refresh, status, agentOn>>
   /\ CallEffects(TRUE, byAgent)
DeletesPond(byAgent) == pond \in {"running", "stopped", "failed"} /\ jobs = 0 /\ (IF byAgent THEN AgentApiOk ELSE UserApiOk)
   /\ pond' = "deleting" /\ jobs' = 1 /\ UNCHANGED <<lastSampleRunning, session, jwt, refresh, status, agentOn>>
   /\ CallEffects(TRUE, byAgent)
ReadsPond(byAgent) == pond # "none" /\ (IF byAgent THEN AgentApiOk ELSE UserApiOk)
   /\ UNCHANGED <<infra, session, jwt, refresh, status, agentOn>> /\ CallEffects(TRUE, byAgent)
\* ---- Provisioning workers (node-agent jobs, reconciler) ----
ProvisionEnds == pond = "provisioning" /\ jobs = 1 /\ jobs' = 0 /\ pond' \in {"running", "failed"}
   /\ UNCHANGED <<lastSampleRunning, session, jwt, refresh, status, agentOn, ghosts>>
StopStart == jobs = 0 /\ pond \in {"running", "stopped"} /\ pond' = (IF pond = "running" THEN "stopped" ELSE "running")
   /\ UNCHANGED <<jobs, lastSampleRunning, session, jwt, refresh, status, agentOn, ghosts>>
DeleteEnds == pond = "deleting" /\ jobs = 1 /\ pond' = "deleted" /\ jobs' = 0
   /\ UNCHANGED <<lastSampleRunning, session, jwt, refresh, status, agentOn, ghosts>>
\* ---- Metering: node sampler + daily aggregation ----
NodeSamples == pond \in {"running", "stopped", "failed", "provisioning"}
   /\ lastSampleRunning' = (pond = "running") /\ UNCHANGED <<pond, jobs, session, jwt, refresh, status, agentOn, ghosts>>
DayAggregated == pond = "deleted"
   /\ usageAfterDelete' = (usageAfterDelete \/ (~Fixed /\ lastSampleRunning))
   /\ UNCHANGED <<pond, jobs, lastSampleRunning, session, jwt, refresh, status, agentOn, loggedOutCall, suspendedCall, agentBeyondOwner>>

Next == UserLogsIn \/ UserLogsOut \/ TokenExpires \/ AdminSuspends \/ AdminReactivates \/ UserTogglesAgent
     \/ (\E a \in BOOLEAN : CreatesPond(a) \/ DeletesPond(a) \/ ReadsPond(a))
     \/ ProvisionEnds \/ StopStart \/ DeleteEnds \/ NodeSamples \/ DayAggregated
Spec == Init /\ [][Next]_vars

\* ---- Cross-subsystem invariants ----
NoPondApiWhenLoggedOut  == ~loggedOutCall
NoPondApiWhenSuspended  == ~suspendedCall
AgentScopeWithinOwner   == ~agentBeyondOwner
DeletedPondHasNoJobs    == pond = "deleted" => jobs = 0
DeletedPondAccruesNoUsage == ~usageAfterDelete
=============================================================================
