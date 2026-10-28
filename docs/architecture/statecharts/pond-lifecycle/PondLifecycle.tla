---- MODULE PondLifecycle ----
\* Agreed pond lifecycle for Wave B1: stop, start, delete with backup first.
\* Desire and observed move together on user delete; stop/start change desire
\* first, then the agent finishes into observed.

VARIABLES whatYouAskedFor, whatThePondShows
vars == <<whatYouAskedFor, whatThePondShows>>

whatYouAskedForStates == {"Keep it off", "Keep it on", "Remove it"}
whatThePondShowsStates == {"Being removed", "Broken", "Gone", "Not ready yet", "Offline", "Online", "Saving a last backup"}

TypeOK ==
    /\ whatYouAskedFor \in whatYouAskedForStates
    /\ whatThePondShows \in whatThePondShowsStates

Init ==
    /\ whatYouAskedFor = "Keep it on"
    /\ whatThePondShows = "Not ready yet"

\* you stop — only while the pond is Online
YouStop ==
    /\ whatYouAskedFor = "Keep it on"
    /\ whatThePondShows = "Online"
    /\ whatYouAskedFor' = "Keep it off"
    /\ UNCHANGED whatThePondShows

\* you start — only while the pond is Offline
YouStart ==
    /\ whatYouAskedFor = "Keep it off"
    /\ whatThePondShows = "Offline"
    /\ whatYouAskedFor' = "Keep it on"
    /\ UNCHANGED whatThePondShows

\* you delete — desire and pond leave together into the last-backup path
YouDelete ==
    /\ whatYouAskedFor \in {"Keep it on", "Keep it off"}
    /\ whatThePondShows \in {"Online", "Offline", "Broken"}
    /\ whatYouAskedFor' = "Remove it"
    /\ whatThePondShows' = "Saving a last backup"

\* create finishes — only while you still want it on
CreateFinishes ==
    /\ whatYouAskedFor = "Keep it on"
    /\ whatThePondShows = "Not ready yet"
    /\ whatThePondShows' = "Online"
    /\ UNCHANGED whatYouAskedFor

\* create fails
CreateFails ==
    /\ whatThePondShows = "Not ready yet"
    /\ whatThePondShows' = "Broken"
    /\ UNCHANGED whatYouAskedFor

\* stop finishes — only after you asked to keep it off
StopFinishes ==
    /\ whatYouAskedFor = "Keep it off"
    /\ whatThePondShows \in {"Online", "Broken"}
    /\ whatThePondShows' = "Offline"
    /\ UNCHANGED whatYouAskedFor

\* stop fails
StopFails ==
    /\ whatYouAskedFor = "Keep it off"
    /\ whatThePondShows = "Online"
    /\ whatThePondShows' = "Broken"
    /\ UNCHANGED whatYouAskedFor

\* restore finishes
RestoreFinishes ==
    /\ whatYouAskedFor = "Keep it on"
    /\ whatThePondShows = "Online"
    /\ whatThePondShows' = "Online"
    /\ UNCHANGED whatYouAskedFor

\* restore fails
RestoreFails ==
    /\ whatYouAskedFor = "Keep it on"
    /\ whatThePondShows = "Online"
    /\ whatThePondShows' = "Broken"
    /\ UNCHANGED whatYouAskedFor

\* start finishes — only after you asked to keep it on
StartFinishes ==
    /\ whatYouAskedFor = "Keep it on"
    /\ whatThePondShows \in {"Offline", "Broken"}
    /\ whatThePondShows' = "Online"
    /\ UNCHANGED whatYouAskedFor

\* start fails
StartFails ==
    /\ whatYouAskedFor = "Keep it on"
    /\ whatThePondShows = "Offline"
    /\ whatThePondShows' = "Broken"
    /\ UNCHANGED whatYouAskedFor

\* last backup finishes — only while remove is desired
LastBackupFinishes ==
    /\ whatYouAskedFor = "Remove it"
    /\ whatThePondShows = "Saving a last backup"
    /\ whatThePondShows' = "Being removed"
    /\ UNCHANGED whatYouAskedFor

\* last backup fails
LastBackupFails ==
    /\ whatYouAskedFor = "Remove it"
    /\ whatThePondShows = "Saving a last backup"
    /\ whatThePondShows' = "Broken"
    /\ UNCHANGED whatYouAskedFor

\* delete finishes
DeleteFinishes ==
    /\ whatYouAskedFor = "Remove it"
    /\ whatThePondShows = "Being removed"
    /\ whatThePondShows' = "Gone"
    /\ UNCHANGED whatYouAskedFor

\* delete fails
DeleteFails ==
    /\ whatYouAskedFor = "Remove it"
    /\ whatThePondShows = "Being removed"
    /\ whatThePondShows' = "Broken"
    /\ UNCHANGED whatYouAskedFor

\* you retry create
YouRetryCreate ==
    /\ whatYouAskedFor = "Keep it on"
    /\ whatThePondShows = "Broken"
    /\ whatThePondShows' = "Not ready yet"
    /\ UNCHANGED whatYouAskedFor

\* you retry last backup after a failed pre-delete
YouRetryLastBackup ==
    /\ whatYouAskedFor = "Remove it"
    /\ whatThePondShows = "Broken"
    /\ whatThePondShows' = "Saving a last backup"
    /\ UNCHANGED whatYouAskedFor

\* you retry delete only after a good pre-delete backup already exists
YouRetryDelete ==
    /\ whatYouAskedFor = "Remove it"
    /\ whatThePondShows = "Broken"
    /\ whatThePondShows' = "Being removed"
    /\ UNCHANGED whatYouAskedFor

Next ==
    \/ YouStop
    \/ YouStart
    \/ YouDelete
    \/ CreateFinishes
    \/ CreateFails
    \/ StopFinishes
    \/ StopFails
    \/ RestoreFinishes
    \/ RestoreFails
    \/ StartFinishes
    \/ StartFails
    \/ LastBackupFinishes
    \/ LastBackupFails
    \/ DeleteFinishes
    \/ DeleteFails
    \/ YouRetryCreate
    \/ YouRetryLastBackup
    \/ YouRetryDelete

Spec == Init /\ [][Next]_vars

\* The pond is never gone while you still asked to keep it on
GoneWhileWantedOn == ~(whatYouAskedFor = "Keep it on" /\ whatThePondShows = "Gone")

\* The pond is never gone while you still asked to keep it off
GoneWhileWantedOff == ~(whatYouAskedFor = "Keep it off" /\ whatThePondShows = "Gone")

\* After you ask to remove it, the pond is never still Online
OnlineAfterYouRemovedIt == ~(whatYouAskedFor = "Remove it" /\ whatThePondShows = "Online")

\* After you ask to remove it, the pond is never still Offline
OfflineAfterYouRemovedIt == ~(whatYouAskedFor = "Remove it" /\ whatThePondShows = "Offline")

\* Gone is only reached while remove is desired (delete never skips the remove intent)
GoneOnlyWhenRemoved == ~(whatThePondShows = "Gone" /\ whatYouAskedFor # "Remove it")

====
