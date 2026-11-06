---- MODULE PondToken ----
\* Pond-scoped temporary access credential for demo S2 (#203).
\* Lifecycle the presenter and audience member care about: issued, active,
\* expired, revoked. Auth and tool attempts that must never succeed are
\* modeled as steps that leave the credential where it was and record denial.

EXTENDS Integers

VARIABLES
  phase,          \* issued | active | expired | revoked
  passwordOk,     \* TRUE when the presented password matches the hash
  pondMatch,      \* TRUE when the actor targets the token's pond_id
  toolKind,       \* allowed | forbidden | other_pond
  lastAuth,       \* ok | denied
  lastTool,       \* ok | denied | none
  attempt         \* idle | use_after_expiry | use_after_revoke
                  \* marks a visible denial on an already-ended credential

vars == <<phase, passwordOk, pondMatch, toolKind, lastAuth, lastTool, attempt>>

Phases == {"issued", "active", "expired", "revoked"}
AuthResults == {"ok", "denied"}
ToolResults == {"ok", "denied", "none"}
ToolKinds == {"allowed", "forbidden", "other_pond"}
Attempts == {"idle", "use_after_expiry", "use_after_revoke"}

TypeOK ==
  /\ phase \in Phases
  /\ passwordOk \in BOOLEAN
  /\ pondMatch \in BOOLEAN
  /\ toolKind \in ToolKinds
  /\ lastAuth \in AuthResults
  /\ lastTool \in ToolResults
  /\ attempt \in Attempts

Init ==
  /\ phase = "issued"
  /\ passwordOk = TRUE
  /\ pondMatch = TRUE
  /\ toolKind = "allowed"
  /\ lastAuth = "denied"
  /\ lastTool = "none"
  /\ attempt = "idle"

\* Presenter revokes while the token is still usable.
Revoke ==
  /\ phase \in {"issued", "active"}
  /\ phase' = "revoked"
  /\ lastAuth' = "denied"
  /\ lastTool' = "none"
  /\ attempt' = "idle"
  /\ UNCHANGED <<passwordOk, pondMatch, toolKind>>

\* Wall clock passes expires_at while the token is still usable.
Expire ==
  /\ phase \in {"issued", "active"}
  /\ phase' = "expired"
  /\ lastAuth' = "denied"
  /\ lastTool' = "none"
  /\ attempt' = "idle"
  /\ UNCHANGED <<passwordOk, pondMatch, toolKind>>

\* Audience member authenticates with the link + password.
UseOk ==
  /\ phase \in {"issued", "active"}
  /\ passwordOk = TRUE
  /\ phase' = "active"
  /\ lastAuth' = "ok"
  /\ lastTool' = "none"
  /\ attempt' = "idle"
  /\ UNCHANGED <<passwordOk, pondMatch, toolKind>>

\* Wrong password against a still-usable token.
WrongPassword ==
  /\ phase \in {"issued", "active"}
  /\ passwordOk = TRUE
  /\ passwordOk' = FALSE
  /\ lastAuth' = "denied"
  /\ lastTool' = "none"
  /\ attempt' = "idle"
  /\ UNCHANGED <<phase, pondMatch, toolKind>>

\* Present the correct password again after a wrong attempt (still usable).
RetryPassword ==
  /\ phase \in {"issued", "active"}
  /\ passwordOk = FALSE
  /\ passwordOk' = TRUE
  /\ UNCHANGED <<phase, pondMatch, toolKind, lastAuth, lastTool, attempt>>

\* Use after expiry: must stay expired and deny.
UseAfterExpiry ==
  /\ phase = "expired"
  /\ attempt # "use_after_expiry"
  /\ lastAuth' = "denied"
  /\ lastTool' = "none"
  /\ attempt' = "use_after_expiry"
  /\ UNCHANGED <<phase, passwordOk, pondMatch, toolKind>>

\* Use after revoke: must stay revoked and deny.
UseAfterRevoke ==
  /\ phase = "revoked"
  /\ attempt # "use_after_revoke"
  /\ lastAuth' = "denied"
  /\ lastTool' = "none"
  /\ attempt' = "use_after_revoke"
  /\ UNCHANGED <<phase, passwordOk, pondMatch, toolKind>>

\* Wrong password while already expired or revoked (still deny).
WrongPasswordTerminal ==
  /\ phase \in {"expired", "revoked"}
  /\ passwordOk' = FALSE
  /\ lastAuth' = "denied"
  /\ lastTool' = "none"
  /\ UNCHANGED <<phase, pondMatch, toolKind, attempt>>

\* Choose which kind of tool call the audience agent will attempt next.
\* Clearing lastTool keeps the "last result" about the tool about to run,
\* not a previous allowed call.
PickAllowedTool ==
  /\ toolKind' = "allowed"
  /\ pondMatch' = TRUE
  /\ lastTool' = "none"
  /\ UNCHANGED <<phase, passwordOk, lastAuth, attempt>>

PickForbiddenTool ==
  /\ toolKind' = "forbidden"
  /\ lastTool' = "none"
  /\ UNCHANGED <<phase, passwordOk, pondMatch, lastAuth, attempt>>

PickOtherPond ==
  /\ pondMatch' = FALSE
  /\ toolKind' = "other_pond"
  /\ lastTool' = "none"
  /\ UNCHANGED <<phase, passwordOk, lastAuth, attempt>>

ResetPondMatch ==
  /\ pondMatch = FALSE
  /\ pondMatch' = TRUE
  /\ toolKind' = "allowed"
  /\ lastTool' = "none"
  /\ UNCHANGED <<phase, passwordOk, lastAuth, attempt>>

\* Run a tool while authenticated. Allowed tools on the pinned pond succeed;
\* forbidden lifecycle tools and other ponds are denied.
RunTool ==
  /\ lastAuth = "ok"
  /\ phase = "active"
  /\ passwordOk = TRUE
  /\ IF toolKind = "allowed" /\ pondMatch = TRUE
     THEN lastTool' = "ok"
     ELSE lastTool' = "denied"
  /\ UNCHANGED <<phase, passwordOk, pondMatch, toolKind, lastAuth, attempt>>

\* Attempt a tool without a successful auth (must deny).
RunToolUnauthed ==
  /\ lastAuth = "denied"
  /\ lastTool' = "denied"
  /\ UNCHANGED <<phase, passwordOk, pondMatch, toolKind, lastAuth, attempt>>

\* Stutter in terminal phases so TLC does not report deadlock.
Done ==
  /\ phase \in {"expired", "revoked"}
  /\ UNCHANGED vars

Next ==
  \/ Revoke
  \/ Expire
  \/ UseOk
  \/ WrongPassword
  \/ RetryPassword
  \/ UseAfterExpiry
  \/ UseAfterRevoke
  \/ WrongPasswordTerminal
  \/ PickAllowedTool
  \/ PickForbiddenTool
  \/ PickOtherPond
  \/ ResetPondMatch
  \/ RunTool
  \/ RunToolUnauthed
  \/ Done

Spec == Init /\ [][Next]_vars

\* --- Rules the reader agrees to (desired security properties) ---

AuthOkImpliesUsable ==
  lastAuth = "ok" => phase = "active"

AuthOkImpliesNotExpired ==
  lastAuth = "ok" => phase # "expired"

AuthOkImpliesNotRevoked ==
  lastAuth = "ok" => phase # "revoked"

AuthOkImpliesPasswordMatch ==
  lastAuth = "ok" => passwordOk = TRUE

ToolOkImpliesAuthedActive ==
  lastTool = "ok" => (lastAuth = "ok" /\ phase = "active")

ToolOkImpliesAllowedOnPinnedPond ==
  lastTool = "ok" => (toolKind = "allowed" /\ pondMatch = TRUE)

ForbiddenToolNeverOk ==
  toolKind = "forbidden" => lastTool # "ok"

OtherPondNeverOk ==
  toolKind = "other_pond" => lastTool # "ok"

ExpiredNeverAuthOk ==
  phase = "expired" => lastAuth # "ok"

RevokedNeverAuthOk ==
  phase = "revoked" => lastAuth # "ok"

====
