----------------------------- MODULE LogoutSession -----------------------------
(* What the browser does after the user presses Log out.
   Fixed = FALSE matches the client at 924c07e. The click clears the
   in-memory access token and shows the login screen even when
   POST /auth/logout fails. The httpOnly refresh cookie stays. The next
   boot calls POST /auth/refresh and signs the user back in.
   Fixed = TRUE is the chosen design. The click stores a local logged-out
   marker before the request. While that marker is set, boot skips refresh
   and stays on the login screen. Only a successful login clears it.
   A 5xx or a dropped connection keeps the marker and warns that the
   server session may still be active. The next boot retries logout
   only when that request failed or never finished. A full load has no
   access token left, and POST /auth/logout requires one, so the retry
   does not clear the cookie. The marker is what keeps the next refresh
   from signing the user in. A logout the server accepted does not
   call logout again on the next load. *)
EXTENDS Naturals
CONSTANT Fixed

VARIABLES screen, memory, cookie, marker, inflight, askedOut, failed, warned, booted
vars == <<screen, memory, cookie, marker, inflight, askedOut, failed, warned, booted>>

Init ==
  /\ screen = "app"
  /\ memory = TRUE
  /\ cookie = TRUE
  /\ marker = FALSE
  /\ inflight = FALSE
  /\ askedOut = FALSE
  /\ failed = FALSE
  /\ warned = FALSE
  /\ booted = FALSE

YouPressLogOut ==
  /\ screen = "app"
  /\ memory = TRUE
  /\ inflight = FALSE
  /\ inflight' = TRUE
  /\ askedOut' = TRUE
  /\ marker' = Fixed
  /\ UNCHANGED <<screen, memory, cookie, failed, warned, booted>>

ServerAcceptsLogout ==
  /\ inflight = TRUE
  /\ inflight' = FALSE
  /\ screen' = "login"
  /\ memory' = FALSE
  /\ cookie' = FALSE
  /\ failed' = FALSE
  /\ warned' = FALSE
  /\ booted' = FALSE
  /\ marker' = Fixed
  /\ UNCHANGED askedOut

ServerRejectsLogout ==
  /\ inflight = TRUE
  /\ inflight' = FALSE
  /\ screen' = "login"
  /\ memory' = FALSE
  /\ cookie' = TRUE
  /\ failed' = TRUE
  /\ warned' = Fixed
  /\ booted' = FALSE
  /\ marker' = Fixed
  /\ UNCHANGED askedOut

\* Reload, or a deep link such as /app/uso. A full load starts with no access token.
\* When the marker is set, boot does not refresh. The quiet logout retry
\* cannot clear the cookie, because the access token lived only in memory.
YouReloadOrOpenUso ==
  LET skip == Fixed /\ marker
      restore == ~skip /\ cookie
  IN /\ inflight' = FALSE
     /\ booted' = TRUE
     /\ screen' = IF restore THEN "app" ELSE "login"
     /\ memory' = restore
     /\ cookie' = cookie
     /\ UNCHANGED <<marker, askedOut, failed, warned>>

YouLogIn ==
  /\ screen = "login"
  /\ memory = FALSE
  /\ screen' = "app"
  /\ memory' = TRUE
  /\ cookie' = TRUE
  /\ marker' = FALSE
  /\ inflight' = FALSE
  /\ askedOut' = FALSE
  /\ failed' = FALSE
  /\ warned' = FALSE
  /\ booted' = FALSE

Next ==
  \/ YouPressLogOut
  \/ ServerAcceptsLogout
  \/ ServerRejectsLogout
  \/ YouReloadOrOpenUso
  \/ YouLogIn

Spec == Init /\ [][Next]_vars

\* After Log out has settled, a reload or a deep link must not sign the user back in.
StaysLoggedOut ==
  (askedOut /\ inflight = FALSE) => (screen = "login" /\ memory = FALSE)

\* The failed response itself is not a sign-in. The later boot must not be either.
NoSessionAfterFailedLogout ==
  failed => (memory = FALSE /\ screen = "login")

\* A failed logout that left the cookie must say the server session may remain.
FailureIsWarned ==
  (failed /\ cookie) => warned

\* A signed-in session with no logout request in flight has no marker.
LoginClearsMarker ==
  (memory /\ inflight = FALSE) => marker = FALSE

=============================================================================
