---- MODULE SqlQuery ----
EXTENDS Naturals

VARIABLES screen, rows, history

vars == <<screen, rows, history>>

Init == screen = "idle" /\ rows = 1 /\ history = 0

Click ==
    screen \in {"idle", "success", "error", "rejected"}
    /\ screen' = "running"
    /\ UNCHANGED <<rows, history>>

RowsComeBack ==
    screen = "running"
    /\ screen' = "success"
    /\ history' = history + 1
    /\ UNCHANGED rows

SqlFails ==
    screen = "running"
    /\ screen' = "error"
    /\ UNCHANGED <<rows, history>>

ReadOnlyRejects ==
    screen = "running"
    /\ screen' = "rejected"
    /\ UNCHANGED <<rows, history>>

Next == Click \/ RowsComeBack \/ SqlFails \/ ReadOnlyRejects

Spec == Init /\ [][Next]_vars

ReadOnlyKeepsTheRow == rows = 1

SuccessRemembersTheQuery == screen = "success" => history >= 1

RejectedDidNotWrite == screen = "rejected" => rows = 1

HistoryBound == history <= 2

====
