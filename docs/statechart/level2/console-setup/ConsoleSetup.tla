---- MODULE ConsoleSetup ----
EXTENDS Naturals

VARIABLES phase, setups, rotated

vars == <<phase, setups, rotated>>

Init ==
    phase = "pending" /\ setups = 0 /\ rotated = FALSE

\* pg_isready can succeed on the temporary init server, before the pond
\* database exists. That attempt stays pending and is retried.
BootTooEarly ==
    phase = "pending"
    /\ UNCHANGED vars

ServerAccepts ==
    phase = "pending"
    /\ phase' = "done"
    /\ setups' = setups + 1
    /\ UNCHANGED rotated

Query ==
    phase = "done"
    /\ UNCHANGED vars

PasswordRotates ==
    phase = "done"
    /\ rotated = FALSE
    /\ phase' = "pending"
    /\ rotated' = TRUE
    /\ UNCHANGED setups

Next ==
    BootTooEarly \/ ServerAccepts \/ Query \/ PasswordRotates

Spec == Init /\ [][Next]_vars

QueryLeavesTheRoleAlone ==
    phase = "done" => setups >= 1

OneSetupPerPassword ==
    setups <= (IF rotated THEN 2 ELSE 1)

PondIsNotFailed ==
    phase \in {"pending", "done"}

====
