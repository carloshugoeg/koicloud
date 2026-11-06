---- MODULE VerifyEmailSend ----
EXTENDS Naturals

\* Target flow: register → token → verify_email sent or console-logged →
\* resend (neutral 202) → already-verified (409 on re-register).
\* Bug actions let TLC mark the break paths named in the brief.

VARIABLES
  phase,              \* "absent" | "unverified" | "verified"
  provider,           \* "console" | "resend"
  tokens,             \* open VERIFY_EMAIL tokens (0..2)
  sends,              \* notifications.send call count
  logged_plain,       \* plaintext token written to logs
  last_status,        \* "none" | "201" | "202" | "409" | "404"
  race                \* 0 = idle, 1 = first register in flight

vars == <<phase, provider, tokens, sends, logged_plain, last_status, race>>

TypeOK ==
  /\ phase \in {"absent", "unverified", "verified"}
  /\ provider \in {"console", "resend"}
  /\ tokens \in 0..2
  /\ sends \in 0..4
  /\ logged_plain \in BOOLEAN
  /\ last_status \in {"none", "201", "202", "409", "404"}
  /\ race \in 0..1

Init ==
  /\ phase = "absent"
  /\ provider \in {"console", "resend"}
  /\ tokens = 0
  /\ sends = 0
  /\ logged_plain = FALSE
  /\ last_status = "none"
  /\ race = 0

Deliver(p) ==
  /\ IF p = "resend"
     THEN /\ sends' = sends + 1
          /\ UNCHANGED logged_plain
     ELSE /\ logged_plain' = TRUE
          /\ UNCHANGED sends

\* --- intended actions ---

RegisterFresh ==
  /\ phase = "absent"
  /\ race = 0
  /\ tokens < 2
  /\ sends < 4
  /\ phase' = "unverified"
  /\ tokens' = tokens + 1
  /\ last_status' = "201"
  /\ Deliver(provider)
  /\ UNCHANGED <<provider, race>>

RegisterUnverifiedAgain ==
  /\ phase = "unverified"
  /\ tokens < 2
  /\ sends < 4
  /\ tokens' = tokens + 1
  /\ last_status' = "201"
  /\ Deliver(provider)
  /\ UNCHANGED <<phase, provider, race>>

RegisterVerifiedTaken ==
  /\ phase = "verified"
  /\ last_status' = "409"
  /\ UNCHANGED <<phase, provider, tokens, sends, logged_plain, race>>

ResendUnknownOrVerified ==
  /\ phase \in {"absent", "verified"}
  /\ last_status' = "202"
  /\ UNCHANGED <<phase, provider, tokens, sends, logged_plain, race>>

ResendUnverified ==
  /\ phase = "unverified"
  /\ tokens < 2
  /\ sends < 4
  /\ tokens' = tokens + 1
  /\ last_status' = "202"
  /\ Deliver(provider)
  /\ UNCHANGED <<phase, provider, race>>

VerifyEmail ==
  /\ phase = "unverified"
  /\ tokens >= 1
  /\ phase' = "verified"
  /\ tokens' = 0
  /\ UNCHANGED <<provider, sends, logged_plain, last_status, race>>

\* --- break-path actions (bugs / races) ---

BugRegisterNoSend ==
  /\ phase = "absent"
  /\ provider = "resend"
  /\ race = 0
  /\ phase' = "unverified"
  /\ tokens' = 1
  /\ last_status' = "201"
  /\ UNCHANGED <<provider, sends, logged_plain, race>>

BugLogPlainOnResend ==
  /\ provider = "resend"
  /\ phase = "unverified"
  /\ logged_plain = FALSE
  /\ logged_plain' = TRUE
  /\ UNCHANGED <<phase, provider, tokens, sends, last_status, race>>

BugResendEnumerates ==
  /\ phase = "absent"
  /\ last_status' = "404"
  /\ UNCHANGED <<phase, provider, tokens, sends, logged_plain, race>>

BugDoubleSendBurst ==
  /\ phase = "unverified"
  /\ provider = "resend"
  /\ sends < 3
  /\ tokens < 2
  /\ tokens' = tokens + 1
  /\ sends' = sends + 2
  /\ last_status' = "202"
  /\ UNCHANGED <<phase, provider, logged_plain, race>>

RaceBeginRegister ==
  /\ phase = "absent"
  /\ race = 0
  /\ race' = 1
  /\ UNCHANGED <<phase, provider, tokens, sends, logged_plain, last_status>>

RaceSecondRegisterWins ==
  /\ race = 1
  /\ phase = "absent"
  /\ tokens < 2
  /\ sends < 4
  /\ phase' = "unverified"
  /\ tokens' = tokens + 1
  /\ race' = 0
  /\ last_status' = "201"
  /\ Deliver(provider)
  /\ UNCHANGED provider

\* Race leaves an unverified row while another register is still in flight.
BugRaceDangling ==
  /\ race = 1
  /\ phase = "absent"
  /\ phase' = "unverified"
  /\ tokens' = 1
  /\ last_status' = "201"
  /\ Deliver(provider)
  /\ UNCHANGED <<provider, race>>

Done ==
  /\ phase = "verified"
  /\ UNCHANGED vars

Next ==
  \/ RegisterFresh
  \/ RegisterUnverifiedAgain
  \/ RegisterVerifiedTaken
  \/ ResendUnknownOrVerified
  \/ ResendUnverified
  \/ VerifyEmail
  \/ BugRegisterNoSend
  \/ BugLogPlainOnResend
  \/ BugResendEnumerates
  \/ BugDoubleSendBurst
  \/ RaceBeginRegister
  \/ RaceSecondRegisterWins
  \/ BugRaceDangling
  \/ Done

Spec == Init /\ [][Next]_vars

\* Rules the reader agreed to (target contract).
NoPlaintextOnResend == provider = "resend" => ~logged_plain
ResendAlwaysNeutral == last_status # "404"
SendWhenResendRegisters ==
  ~(provider = "resend" /\ phase = "unverified" /\ tokens >= 1 /\ sends = 0 /\ last_status = "201")
\* One delivery per open token under resend (burst sends two for one token).
NoDoubleBurst == ~(provider = "resend" /\ sends > tokens /\ tokens >= 1 /\ phase = "unverified")
RaceSettles == ~(race = 1 /\ phase = "unverified")

====
