---- MODULE SqlQuery ----
EXTENDS Naturals

VARIABLES screen, rows, history, truncated

vars == <<screen, rows, history, truncated>>

Init ==
    screen = "idle" /\ rows = 1 /\ history = 0 /\ truncated = FALSE

Settled ==
    screen \in {"idle", "success", "error", "rejected", "timeout", "unavailable"}

ClickRead ==
    Settled
    /\ screen' = "running"
    /\ UNCHANGED <<rows, history, truncated>>

OpenWriteConfirm ==
    Settled
    /\ screen' = "confirming"
    /\ UNCHANGED <<rows, history, truncated>>

CancelWrite ==
    screen = "confirming"
    /\ screen' = "idle"
    /\ UNCHANGED <<rows, history, truncated>>

ConfirmWrite ==
    screen = "confirming"
    /\ screen' = "running"
    /\ UNCHANGED <<rows, history, truncated>>

RowsComeBack ==
    screen = "running"
    /\ screen' = "success"
    /\ history' = history + 1
    /\ truncated' = FALSE
    /\ UNCHANGED rows

RowCap ==
    screen = "running"
    /\ screen' = "success"
    /\ history' = history + 1
    /\ truncated' = TRUE
    /\ UNCHANGED rows

UserSqlError ==
    screen = "running"
    /\ screen' = "error"
    /\ UNCHANGED <<rows, history, truncated>>

TimedOut ==
    screen = "running"
    /\ screen' = "timeout"
    /\ UNCHANGED <<rows, history, truncated>>

NodeDown ==
    screen = "running"
    /\ screen' = "unavailable"
    /\ UNCHANGED <<rows, history, truncated>>

ReadOnlyRejects ==
    screen = "running"
    /\ screen' = "rejected"
    /\ UNCHANGED <<rows, history, truncated>>

Next ==
    ClickRead \/ OpenWriteConfirm \/ CancelWrite \/ ConfirmWrite
    \/ RowsComeBack \/ RowCap \/ UserSqlError \/ TimedOut
    \/ NodeDown \/ ReadOnlyRejects

Spec == Init /\ [][Next]_vars

ReadOnlyKeepsTheRow == rows = 1

SuccessRemembersTheQuery == screen = "success" => history >= 1

RejectedDidNotWrite == screen = "rejected" => rows = 1

ErrorDidNotWrite == screen \in {"error", "timeout", "unavailable", "rejected"} => rows = 1

HistoryBound == history <= 3

====
