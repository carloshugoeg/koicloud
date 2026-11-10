---- MODULE InviteAgent ----
\* Presenter UI flow for demo S7 (#208): Invitar agente dialog on pond detail.
\* Reader path: closed → open → generate link+password → password once →
\* QR + paste instructions → reopen hides plaintext → revoke → MCP auth fails.

EXTENDS Integers

VARIABLES
  ui,              \* closed | open_idle | open_created | open_revisit | open_revoked
  passwordShown,   \* TRUE only immediately after create
  qrShown,         \* QR of the invite/link is visible in the dialog
  snippetsShown,   \* Claude Code / Cursor CLI / Codex CLI paste blocks visible
  tokenUsable,     \* TRUE from create until revoke
  lastMcpAuth      \* none | ok | denied

vars == <<ui, passwordShown, qrShown, snippetsShown, tokenUsable, lastMcpAuth>>

UIs == {"closed", "open_idle", "open_created", "open_revisit", "open_revoked"}
AuthResults == {"none", "ok", "denied"}

TypeOK ==
  /\ ui \in UIs
  /\ passwordShown \in BOOLEAN
  /\ qrShown \in BOOLEAN
  /\ snippetsShown \in BOOLEAN
  /\ tokenUsable \in BOOLEAN
  /\ lastMcpAuth \in AuthResults

Init ==
  /\ ui = "closed"
  /\ passwordShown = FALSE
  /\ qrShown = FALSE
  /\ snippetsShown = FALSE
  /\ tokenUsable = FALSE
  /\ lastMcpAuth = "none"

\* Presenter opens Invitar agente with no active invite in this session view.
OpenIdle ==
  /\ ui = "closed"
  /\ tokenUsable = FALSE
  /\ ui' = "open_idle"
  /\ passwordShown' = FALSE
  /\ qrShown' = FALSE
  /\ snippetsShown' = FALSE
  /\ lastMcpAuth' = "none"
  /\ UNCHANGED tokenUsable

\* Presenter reopens the dialog while a token is still usable.
\* List/API never returns plaintext; UI must not re-display the password.
OpenRevisit ==
  /\ ui = "closed"
  /\ tokenUsable = TRUE
  /\ ui' = "open_revisit"
  /\ passwordShown' = FALSE
  /\ qrShown' = TRUE
  /\ snippetsShown' = TRUE
  /\ lastMcpAuth' = "none"
  /\ UNCHANGED tokenUsable

Close ==
  /\ ui \in {"open_idle", "open_created", "open_revisit", "open_revoked"}
  /\ ui' = "closed"
  /\ passwordShown' = FALSE
  /\ qrShown' = FALSE
  /\ snippetsShown' = FALSE
  /\ lastMcpAuth' = "none"
  /\ UNCHANGED tokenUsable

\* Generate temporary link + password via existing create endpoint.
\* Password shown once; QR and console paste instructions appear together.
Generate ==
  /\ ui = "open_idle"
  /\ ui' = "open_created"
  /\ passwordShown' = TRUE
  /\ qrShown' = TRUE
  /\ snippetsShown' = TRUE
  /\ tokenUsable' = TRUE
  /\ lastMcpAuth' = "none"

\* Audience can authenticate while the token is usable.
McpAuthOk ==
  /\ tokenUsable = TRUE
  /\ lastMcpAuth' = "ok"
  /\ UNCHANGED <<ui, passwordShown, qrShown, snippetsShown, tokenUsable>>

\* Revoke from the dialog; MCP auth must fail afterward.
Revoke ==
  /\ ui \in {"open_created", "open_revisit"}
  /\ tokenUsable = TRUE
  /\ ui' = "open_revoked"
  /\ passwordShown' = FALSE
  /\ qrShown' = FALSE
  /\ snippetsShown' = FALSE
  /\ tokenUsable' = FALSE
  /\ lastMcpAuth' = "none"

\* MCP auth attempt after revoke (or with no usable token) stays denied.
McpAuthDenied ==
  /\ tokenUsable = FALSE
  /\ lastMcpAuth' = "denied"
  /\ UNCHANGED <<ui, passwordShown, qrShown, snippetsShown, tokenUsable>>

Done ==
  /\ ui = "closed"
  /\ UNCHANGED vars

Next ==
  \/ OpenIdle
  \/ OpenRevisit
  \/ Close
  \/ Generate
  \/ Revoke
  \/ McpAuthOk
  \/ McpAuthDenied
  \/ Done

Spec == Init /\ [][Next]_vars

\* Password plaintext only in the create-once view.
PasswordOnlyOnCreate ==
  passwordShown => ui = "open_created"

\* Reopening never re-displays plaintext.
RevisitHidesPassword ==
  ui = "open_revisit" => ~passwordShown

\* Closed dialog never leaves password visible.
ClosedHidesPassword ==
  ui = "closed" => ~passwordShown

\* Active invite view shows QR and console paste instructions.
InviteShowsQrAndSnippets ==
  ui \in {"open_created", "open_revisit"} => (qrShown /\ snippetsShown)

\* After revoke, MCP auth cannot succeed.
RevokedNeverAuthOk ==
  ~tokenUsable => lastMcpAuth # "ok"

\* Auth ok only while the token is usable.
AuthOkImpliesUsable ==
  lastMcpAuth = "ok" => tokenUsable

====
