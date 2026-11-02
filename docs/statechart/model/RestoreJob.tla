------------------------------ MODULE RestoreJob ------------------------------
EXTENDS Integers

CONSTANT AsIs

VARIABLES phase, agent, screen, ticks

vars == <<phase, agent, screen, ticks>>

Init ==
  /\ phase = "queued"
  /\ agent \in {"up", "down"}
  /\ screen = "queued"
  /\ ticks = 0

Claim ==
  /\ agent = "up"
  /\ phase = "queued"
  /\ phase' = "running"
  /\ screen' = IF AsIs THEN "queued" ELSE "running"
  /\ UNCHANGED <<agent, ticks>>

FinishOk ==
  /\ phase = "running"
  /\ phase' = "succeeded"
  /\ screen' = IF AsIs THEN "queued" ELSE "succeeded"
  /\ UNCHANGED <<agent, ticks>>

FinishFail ==
  /\ phase = "running"
  /\ phase' = "failed"
  /\ screen' = IF AsIs THEN "queued" ELSE "failed"
  /\ UNCHANGED <<agent, ticks>>

TimeOut ==
  /\ phase = "running"
  /\ ticks >= 2
  /\ phase' = "timed_out"
  /\ screen' = IF AsIs THEN "queued" ELSE "timed_out"
  /\ UNCHANGED <<agent, ticks>>

GiveUp ==
  /\ ~AsIs
  /\ agent = "down"
  /\ phase = "queued"
  /\ ticks >= 2
  /\ phase' = "agent_unreachable"
  /\ screen' = "agent_unreachable"
  /\ UNCHANGED <<agent, ticks>>

Advance ==
  /\ ticks < 3
  /\ phase \in {"queued", "running"}
  /\ ~(~AsIs /\ agent = "down" /\ phase = "queued" /\ ticks >= 2)
  /\ ticks' = ticks + 1
  /\ UNCHANGED <<phase, agent, screen>>

Done ==
  /\ phase \in {"succeeded", "failed", "timed_out", "agent_unreachable"}
  /\ UNCHANGED vars

Stuck ==
  /\ AsIs
  /\ agent = "down"
  /\ phase = "queued"
  /\ ticks >= 3
  /\ UNCHANGED vars

Next ==
  Claim \/ FinishOk \/ FinishFail \/ TimeOut \/ GiveUp \/ Advance \/ Done \/ Stuck

Spec == Init /\ [][Next]_vars

ScreenShowsJob == screen = phase

AgentDownEnds == agent = "down" /\ ticks >= 3 => phase # "queued"

ClockBound == ticks <= 3

=============================================================================
