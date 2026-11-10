---- MODULE TempSqlConfirm ----
\* Bound temporary MCP SQL confirmation (TEMP-CONFIRM / issue #203 follow-on).
\* Proposal lifecycle: NoProposal → Pending → Consumed.
\* Credential independently Live / Expired / Revoked.
\* Identity is PondToken.id (session). Shared secret holders are the same principal.
\* Exact SQL + pond + action bind via digest match. Claim is at-most-once.

EXTENDS Integers

VARIABLES
  cred,           \* live | expired | revoked
  proposal,       \* none | pending | consumed
  claimed,        \* TRUE after durable consume (spent even if SQL fails)
  admitted,       \* TRUE only after final credential admission under lock
  executed,       \* TRUE when SQL succeeded
  lastResult,     \* ok | denied | none
  denial          \* none | cross_session | cross_pond | bad_digest | bad_action
                  \* | expired_cred | revoked_cred | proposal_expired | replay
                  \* | owner_row | revoke_before_admit

vars == <<cred, proposal, claimed, admitted, executed, lastResult, denial>>

Creds == {"live", "expired", "revoked"}
Proposals == {"none", "pending", "consumed"}
Results == {"ok", "denied", "none"}
Denials == {"none", "cross_session", "cross_pond", "bad_digest", "bad_action",
            "expired_cred", "revoked_cred", "proposal_expired", "replay",
            "owner_row", "revoke_before_admit"}

TypeOK ==
  /\ cred \in Creds
  /\ proposal \in Proposals
  /\ claimed \in BOOLEAN
  /\ admitted \in BOOLEAN
  /\ executed \in BOOLEAN
  /\ lastResult \in Results
  /\ denial \in Denials

Init ==
  /\ cred = "live"
  /\ proposal = "none"
  /\ claimed = FALSE
  /\ admitted = FALSE
  /\ executed = FALSE
  /\ lastResult = "none"
  /\ denial = "none"

\* --- Credential lifecycle ---

ExpireCred ==
  /\ cred = "live"
  /\ cred' = "expired"
  /\ lastResult' = "none"
  /\ denial' = "none"
  /\ UNCHANGED <<proposal, claimed, admitted, executed>>

RevokeCred ==
  /\ cred = "live"
  /\ cred' = "revoked"
  /\ lastResult' = "none"
  /\ denial' = "none"
  /\ UNCHANGED <<proposal, claimed, admitted, executed>>

\* --- Propose write SQL ---

ProposeOk ==
  /\ cred = "live"
  /\ proposal = "none"
  /\ proposal' = "pending"
  /\ claimed' = FALSE
  /\ admitted' = FALSE
  /\ executed' = FALSE
  /\ lastResult' = "none"
  /\ denial' = "none"
  /\ UNCHANGED cred

ProposeDeniedDeadCred ==
  /\ cred \in {"expired", "revoked"}
  /\ proposal = "none"
  /\ lastResult' = "denied"
  /\ denial' = IF cred = "expired" THEN "expired_cred" ELSE "revoked_cred"
  /\ UNCHANGED <<cred, proposal, claimed, admitted, executed>>

\* --- Confirm paths ---

\* Happy path: claim, admit under live credential, execute SQL.
ConfirmSuccess ==
  /\ cred = "live"
  /\ proposal = "pending"
  /\ ~claimed
  /\ proposal' = "consumed"
  /\ claimed' = TRUE
  /\ admitted' = TRUE
  /\ executed' = TRUE
  /\ lastResult' = "ok"
  /\ denial' = "none"
  /\ UNCHANGED cred

\* Claim + admit without SQL success yet (dispatch about to run).
ConfirmClaimAdmit ==
  /\ cred = "live"
  /\ proposal = "pending"
  /\ ~claimed
  /\ proposal' = "consumed"
  /\ claimed' = TRUE
  /\ admitted' = TRUE
  /\ executed' = FALSE
  /\ lastResult' = "none"
  /\ denial' = "none"
  /\ UNCHANGED cred

ExecuteOk ==
  /\ proposal = "consumed"
  /\ claimed = TRUE
  /\ admitted = TRUE
  /\ ~executed
  /\ cred = "live"
  /\ executed' = TRUE
  /\ lastResult' = "ok"
  /\ denial' = "none"
  /\ UNCHANGED <<cred, proposal, claimed, admitted>>

ClaimThenRevokeBeforeAdmit ==
  /\ cred = "live"
  /\ proposal = "pending"
  /\ ~claimed
  /\ proposal' = "consumed"
  /\ claimed' = TRUE
  /\ admitted' = FALSE
  /\ executed' = FALSE
  /\ cred' = "revoked"
  /\ lastResult' = "denied"
  /\ denial' = "revoke_before_admit"

ClaimThenExpireBeforeAdmit ==
  /\ cred = "live"
  /\ proposal = "pending"
  /\ ~claimed
  /\ proposal' = "consumed"
  /\ claimed' = TRUE
  /\ admitted' = FALSE
  /\ executed' = FALSE
  /\ cred' = "expired"
  /\ lastResult' = "denied"
  /\ denial' = "expired_cred"

\* Wrong principal / binding: pending stays, no claim.
ConfirmCrossSession ==
  /\ proposal = "pending"
  /\ ~claimed
  /\ lastResult' = "denied"
  /\ denial' = "cross_session"
  /\ UNCHANGED <<cred, proposal, claimed, admitted, executed>>

ConfirmCrossPond ==
  /\ proposal = "pending"
  /\ ~claimed
  /\ lastResult' = "denied"
  /\ denial' = "cross_pond"
  /\ UNCHANGED <<cred, proposal, claimed, admitted, executed>>

ConfirmBadDigest ==
  /\ proposal = "pending"
  /\ ~claimed
  /\ lastResult' = "denied"
  /\ denial' = "bad_digest"
  /\ UNCHANGED <<cred, proposal, claimed, admitted, executed>>

ConfirmBadAction ==
  /\ proposal = "pending"
  /\ ~claimed
  /\ lastResult' = "denied"
  /\ denial' = "bad_action"
  /\ UNCHANGED <<cred, proposal, claimed, admitted, executed>>

ConfirmOwnerRow ==
  /\ proposal = "pending"
  /\ ~claimed
  /\ lastResult' = "denied"
  /\ denial' = "owner_row"
  /\ UNCHANGED <<cred, proposal, claimed, admitted, executed>>

ConfirmDeniedDeadCred ==
  /\ proposal = "pending"
  /\ ~claimed
  /\ cred \in {"expired", "revoked"}
  /\ lastResult' = "denied"
  /\ denial' = IF cred = "expired" THEN "expired_cred" ELSE "revoked_cred"
  /\ UNCHANGED <<cred, proposal, claimed, admitted, executed>>

ProposalExpireWhileLive ==
  /\ proposal = "pending"
  /\ ~claimed
  /\ cred = "live"
  /\ lastResult' = "denied"
  /\ denial' = "proposal_expired"
  /\ UNCHANGED <<cred, proposal, claimed, admitted, executed>>

Replay ==
  /\ proposal = "consumed"
  /\ claimed = TRUE
  /\ lastResult' = "denied"
  /\ denial' = "replay"
  /\ UNCHANGED <<cred, proposal, claimed, admitted, executed>>

\* SQL privilege failure after claim+admit; token stays spent, no rearm.
FailDispatch ==
  /\ proposal = "consumed"
  /\ claimed = TRUE
  /\ admitted = TRUE
  /\ executed = FALSE
  /\ lastResult' = "denied"
  /\ denial' = "none"
  /\ UNCHANGED <<cred, proposal, claimed, admitted, executed>>

Done ==
  /\ proposal = "consumed"
  /\ UNCHANGED vars

Next ==
  \/ ExpireCred
  \/ RevokeCred
  \/ ProposeOk
  \/ ProposeDeniedDeadCred
  \/ ConfirmSuccess
  \/ ConfirmClaimAdmit
  \/ ExecuteOk
  \/ ClaimThenRevokeBeforeAdmit
  \/ ClaimThenExpireBeforeAdmit
  \/ ConfirmCrossSession
  \/ ConfirmCrossPond
  \/ ConfirmBadDigest
  \/ ConfirmBadAction
  \/ ConfirmOwnerRow
  \/ ConfirmDeniedDeadCred
  \/ ProposalExpireWhileLive
  \/ Replay
  \/ FailDispatch
  \/ Done

Spec == Init /\ [][Next]_vars

ExecutedImpliesClaimed ==
  executed => claimed

ExecutedImpliesAdmitted ==
  executed => admitted

ExecutedImpliesConsumed ==
  executed => proposal = "consumed"

OkImpliesNoDenial ==
  lastResult = "ok" => denial = "none"

ReplayNeverOk ==
  denial = "replay" => lastResult = "denied"

ConsumedNeverPending ==
  proposal = "consumed" => claimed = TRUE

DeadCredNeverOk ==
  cred \in {"expired", "revoked"} => lastResult # "ok"

RevokeBeforeAdmitNeverExecutes ==
  denial = "revoke_before_admit" => (claimed /\ ~executed /\ ~admitted)

BindingDenialNeverClaims ==
  denial \in {"cross_session", "cross_pond", "bad_digest", "bad_action", "owner_row",
              "proposal_expired"}
    => (~claimed /\ proposal = "pending")

AtMostOneSuccess ==
  \* Once executed, replay cannot set ok again (Replay forces denied).
  (executed /\ denial = "replay") => lastResult = "denied"

====
