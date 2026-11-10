---- MODULE ConsoleConnect ----
\* Console-agent connect flow for demo S3 (#204).
\* Reader path: paste temporary link + password into Claude Code / Cursor CLI /
\* Codex CLI → auth → pond-pinned session → allowed read tool vs denied
\* off-pond or forbidden tool.

EXTENDS Integers

VARIABLES
  session,     \* bare | pasted | auth_failed | pond_pinned
  passwordOk,  \* TRUE when the pasted password matches the token
  toolKind,    \* allowed | forbidden | other_pond
  lastAuth,    \* none | ok | denied
  lastTool     \* none | ok | denied

vars == <<session, passwordOk, toolKind, lastAuth, lastTool>>

Sessions == {"bare", "pasted", "auth_failed", "pond_pinned"}
AuthResults == {"none", "ok", "denied"}
ToolResults == {"none", "ok", "denied"}
ToolKinds == {"allowed", "forbidden", "other_pond"}

TypeOK ==
  /\ session \in Sessions
  /\ passwordOk \in BOOLEAN
  /\ toolKind \in ToolKinds
  /\ lastAuth \in AuthResults
  /\ lastTool \in ToolResults

Init ==
  /\ session = "bare"
  /\ passwordOk = TRUE
  /\ toolKind = "allowed"
  /\ lastAuth = "none"
  /\ lastTool = "none"

\* Audience pastes the temporary link + password into a console agent.
PasteLinkPassword ==
  /\ session = "bare"
  /\ session' = "pasted"
  /\ lastAuth' = "none"
  /\ lastTool' = "none"
  /\ UNCHANGED <<passwordOk, toolKind>>

\* Console agent authenticates against /mcp with Basic slug:password.
AuthSucceed ==
  /\ session = "pasted"
  /\ passwordOk = TRUE
  /\ session' = "pond_pinned"
  /\ lastAuth' = "ok"
  /\ lastTool' = "none"
  /\ UNCHANGED <<passwordOk, toolKind>>

AuthFail ==
  /\ session = "pasted"
  /\ passwordOk = TRUE
  /\ passwordOk' = FALSE
  /\ session' = "auth_failed"
  /\ lastAuth' = "denied"
  /\ lastTool' = "none"
  /\ UNCHANGED toolKind

\* Paste the correct password again after a failed attempt.
RepasteCorrect ==
  /\ session = "auth_failed"
  /\ passwordOk = FALSE
  /\ passwordOk' = TRUE
  /\ session' = "pasted"
  /\ lastAuth' = "none"
  /\ lastTool' = "none"
  /\ UNCHANGED toolKind

\* Choose the next tool the agent will attempt.
PickAllowed ==
  /\ toolKind' = "allowed"
  /\ lastTool' = "none"
  /\ UNCHANGED <<session, passwordOk, lastAuth>>

PickForbidden ==
  /\ toolKind' = "forbidden"
  /\ lastTool' = "none"
  /\ UNCHANGED <<session, passwordOk, lastAuth>>

PickOtherPond ==
  /\ toolKind' = "other_pond"
  /\ lastTool' = "none"
  /\ UNCHANGED <<session, passwordOk, lastAuth>>

\* Call a tool while pond-pinned. Allowed read (whoami / get_pond) succeeds;
\* forbidden tools and off-pond targets are denied; actor stays pond_pinned.
CallTool ==
  /\ session = "pond_pinned"
  /\ lastAuth = "ok"
  /\ IF toolKind = "allowed"
     THEN lastTool' = "ok"
     ELSE lastTool' = "denied"
  /\ UNCHANGED <<session, passwordOk, toolKind, lastAuth>>

\* Tool call without a successful auth must deny.
CallToolUnauthed ==
  /\ lastAuth \in {"none", "denied"}
  /\ lastTool' = "denied"
  /\ UNCHANGED <<session, passwordOk, toolKind, lastAuth>>

\* End states may stutter so TLC does not report deadlock.
Done ==
  /\ session \in {"pond_pinned", "auth_failed"}
  /\ UNCHANGED vars

Next ==
  \/ PasteLinkPassword
  \/ AuthSucceed
  \/ AuthFail
  \/ RepasteCorrect
  \/ PickAllowed
  \/ PickForbidden
  \/ PickOtherPond
  \/ CallTool
  \/ CallToolUnauthed
  \/ Done

Spec == Init /\ [][Next]_vars

\* --- Rules the audience demo depends on ---

AuthOkImpliesPinned ==
  lastAuth = "ok" => session = "pond_pinned"

AuthOkImpliesPasswordMatch ==
  lastAuth = "ok" => passwordOk = TRUE

AuthFailNeverPinned ==
  session = "auth_failed" => lastAuth # "ok"

ToolOkImpliesPinned ==
  lastTool = "ok" => (session = "pond_pinned" /\ lastAuth = "ok")

ToolOkImpliesAllowed ==
  lastTool = "ok" => toolKind = "allowed"

ForbiddenNeverOk ==
  toolKind = "forbidden" => lastTool # "ok"

OtherPondNeverOk ==
  toolKind = "other_pond" => lastTool # "ok"

UnauthedNeverToolOk ==
  lastAuth # "ok" => lastTool # "ok"

PinnedStaysPinnedAfterTool ==
  lastTool \in {"ok", "denied"} /\ lastAuth = "ok" => session = "pond_pinned"

====
