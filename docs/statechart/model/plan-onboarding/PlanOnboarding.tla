----------------------------- MODULE PlanOnboarding -----------------------------
(* Signup → verify → first login → one-time plan choice → app.
   Fixed = TRUE is the demo P0 design.
   Fixed = FALSE is today's main behaviour (no confirm gate, no onboarding,
   no sandbox at register, auto-micro on first pond). *)
EXTENDS Naturals
CONSTANT Fixed

VARIABLES
  screen,
  emailVerified,
  session,
  onboardingDone,
  plan,
  pwdMatch,
  registered

vars == <<screen, emailVerified, session, onboardingDone, plan, pwdMatch, registered>>

Init ==
  /\ screen = "signup"
  /\ emailVerified = FALSE
  /\ session = FALSE
  /\ onboardingDone = FALSE
  /\ plan = "none"
  /\ pwdMatch = TRUE
  /\ registered = FALSE

\* Fixed: mismatch blocks. As-is: no confirm field, always registers.
YouSubmitSignup(match) ==
  /\ screen = "signup"
  /\ ~registered
  /\ pwdMatch' = match
  /\ IF Fixed /\ ~match
     THEN UNCHANGED <<screen, emailVerified, session, onboardingDone, plan, registered>>
     ELSE /\ registered' = TRUE
          /\ plan' = IF Fixed THEN "sandbox" ELSE "none"
          /\ screen' = "verify_mail"
          /\ UNCHANGED <<emailVerified, session, onboardingDone>>

YouOpenLogin ==
  /\ screen = "verify_mail"
  /\ screen' = "login"
  /\ UNCHANGED <<emailVerified, session, onboardingDone, plan, pwdMatch, registered>>

YouVerifyEmail ==
  /\ registered
  /\ ~emailVerified
  /\ emailVerified' = TRUE
  /\ UNCHANGED <<screen, session, onboardingDone, plan, pwdMatch, registered>>

YouLogIn ==
  /\ screen = "login"
  /\ registered
  /\ emailVerified
  /\ session' = TRUE
  /\ IF Fixed /\ ~onboardingDone
     THEN screen' = "onboarding"
     ELSE screen' = "app"
  /\ UNCHANGED <<emailVerified, onboardingDone, plan, pwdMatch, registered>>

YouLogInUnverified ==
  /\ screen = "login"
  /\ registered
  /\ ~emailVerified
  /\ UNCHANGED vars

YouReloadApp ==
  /\ session
  /\ registered
  /\ emailVerified
  /\ IF Fixed /\ ~onboardingDone
     THEN screen' = "onboarding"
     ELSE screen' = "app"
  /\ UNCHANGED <<emailVerified, session, onboardingDone, plan, pwdMatch, registered>>

YouChoosePaid(p) ==
  /\ Fixed
  /\ screen = "onboarding"
  /\ session
  /\ ~onboardingDone
  /\ p \in {"micro", "pro"}
  /\ screen' = "checkout"
  /\ UNCHANGED <<emailVerified, session, onboardingDone, plan, pwdMatch, registered>>

YouPayOk ==
  /\ Fixed
  /\ screen = "checkout"
  /\ session
  /\ ~onboardingDone
  /\ \E p \in {"micro", "pro"} :
       /\ plan' = p
       /\ onboardingDone' = TRUE
       /\ screen' = "app"
  /\ UNCHANGED <<emailVerified, session, pwdMatch, registered>>

YouPayFail ==
  /\ Fixed
  /\ screen = "checkout"
  /\ session
  /\ ~onboardingDone
  /\ screen' = "checkout"
  /\ UNCHANGED <<emailVerified, session, onboardingDone, plan, pwdMatch, registered>>

YouContinueFree ==
  /\ Fixed
  /\ screen = "onboarding"
  /\ session
  /\ ~onboardingDone
  /\ plan = "sandbox"
  /\ onboardingDone' = TRUE
  /\ screen' = "app"
  /\ UNCHANGED <<emailVerified, session, plan, pwdMatch, registered>>

YouCreatePondAsIs ==
  /\ ~Fixed
  /\ session
  /\ screen = "app"
  /\ plan = "none"
  /\ plan' = "micro"
  /\ UNCHANGED <<screen, emailVerified, session, onboardingDone, pwdMatch, registered>>

Done ==
  /\ screen = "app"
  /\ session
  /\ (Fixed => onboardingDone)
  /\ UNCHANGED vars

Next ==
  \/ (\E m \in BOOLEAN : YouSubmitSignup(m))
  \/ YouOpenLogin
  \/ YouVerifyEmail
  \/ YouLogIn
  \/ YouLogInUnverified
  \/ YouReloadApp
  \/ (\E p \in {"micro", "pro"} : YouChoosePaid(p))
  \/ YouPayOk
  \/ YouPayFail
  \/ YouContinueFree
  \/ YouCreatePondAsIs
  \/ Done

Spec == Init /\ [][Next]_vars

\* Desired demo P0 rules (absolute — used to mark as-is breaks).
RegisterIsSandbox ==
  registered /\ ~emailVerified /\ screen = "verify_mail" => plan = "sandbox"

MismatchBlocksRegister ==
  ~pwdMatch => ~registered

OnboardingOnce ==
  onboardingDone => screen # "onboarding"

MustOnboard ==
  session /\ emailVerified /\ ~onboardingDone =>
    screen \in {"onboarding", "checkout"}

NoSilentMicro ==
  ~(plan = "micro" /\ ~onboardingDone)

=============================================================================
