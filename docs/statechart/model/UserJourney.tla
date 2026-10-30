----------------------------- MODULE UserJourney -----------------------------
(* Web user journey: session, pond list, pond detail tabs, SQL console history,
   billing (Uso del mes + Facturacion merged) and plan change / checkout.
   Fixed = FALSE models main @ 72015b5 (preview as Carlos tested it, MSW mocks);
   Fixed = TRUE models the behaviour asked for in #96 r6.
   Code: apps/web/src/app/session-boot-gate.tsx, lib/auth-store.ts (in-memory tokens),
   features/ponds/detail-page.tsx:96-101, backups-page.tsx:102-104,
   sql-console/sql-console-page.tsx:47-51, mocks/handlers.ts:207 (history ignores pondId),
   app/layout/nav-config.ts:42-44, features/plans/checkout-modal.tsx:22-33. *)
EXTENDS Naturals
CONSTANT Fixed

VARIABLES auth, screen, from, cur, history, reloadLost, co, chargedBadCard
vars == <<auth, screen, from, cur, history, reloadLost, co, chargedBadCard>>

Ponds == {"p1", "p2"}                         \* p2 = brand-new pond, no queries yet
TabOrder == <<"Resumen", "Respaldos", "Consola">>
PondTabs == {"resumen", "respaldos", "consola"}

Tabs(s) ==   \* tab strip the page renders
  IF Fixed THEN TabOrder
  ELSE IF s = "respaldos" THEN <<"Resumen", "Respaldos">>
  ELSE IF s = "consola"   THEN <<"Resumen", "Consola", "Respaldos">>
  ELSE <<"Resumen", "Respaldos", "Consola">>
ShownHistory == IF Fixed THEN {h \in history : h = cur} ELSE history

Init == auth = "out" /\ screen = "login" /\ from = "login" /\ cur = "p1"
     /\ history = {"p1"} /\ reloadLost = FALSE /\ co = "closed" /\ chargedBadCard = FALSE

Go(s) == screen' = s /\ from' = screen

YouLogIn     == auth = "out" /\ auth' = "in" /\ Go("list") /\ UNCHANGED <<cur, history, reloadLost, co, chargedBadCard>>
YouLogInBad  == auth = "out" /\ screen = "login" /\ UNCHANGED vars    \* 401: stays on login with error
YouReload    == auth = "in" /\ co = "closed"
                /\ IF Fixed THEN UNCHANGED vars
                   ELSE auth' = "out" /\ Go("login") /\ reloadLost' = TRUE
                        /\ UNCHANGED <<cur, history, co, chargedBadCard>>
YouLogOut    == auth = "in" /\ co = "closed" /\ auth' = "out" /\ Go("login") /\ UNCHANGED <<cur, history, reloadLost, co, chargedBadCard>>
YouOpenPond(p) == auth = "in" /\ co = "closed" /\ screen = "list" /\ cur' = p /\ Go("resumen")
                  /\ UNCHANGED <<auth, history, reloadLost, co, chargedBadCard>>
TabName(t) == IF t = "resumen" THEN "Resumen" ELSE IF t = "respaldos" THEN "Respaldos" ELSE "Consola"
YouPickTab(t)  == auth = "in" /\ screen \in PondTabs /\ t # screen
                  /\ \E i \in DOMAIN Tabs(screen) : Tabs(screen)[i] = TabName(t)
                  /\ Go(t) /\ UNCHANGED <<auth, cur, history, reloadLost, co, chargedBadCard>>
YouRunQuery  == auth = "in" /\ screen = "consola" /\ history' = history \cup {cur}
                /\ UNCHANGED <<auth, screen, from, cur, reloadLost, co, chargedBadCard>>
YouBackToList == auth = "in" /\ co = "closed" /\ screen # "list" /\ screen # "login" /\ Go("list")
                 /\ UNCHANGED <<auth, cur, history, reloadLost, co, chargedBadCard>>
YouOpenBilling == auth = "in" /\ co = "closed" /\ screen \notin {"billing", "login"} /\ Go("billing")
                  /\ UNCHANGED <<auth, cur, history, reloadLost, co, chargedBadCard>>
\* Fixed: "Cambiar de plan" inside Tu plan actual. As-is: also a "Planes" sidebar item from anywhere.
YouOpenPlans == auth = "in" /\ co = "closed" /\ screen \notin {"plans", "login"}
                /\ (Fixed => screen = "billing") /\ Go("plans")
                /\ UNCHANGED <<auth, cur, history, reloadLost, co, chargedBadCard>>
YouPickPlan  == screen = "plans" /\ co = "closed" /\ co' = "editing" /\ Go("checkout")
                /\ UNCHANGED <<auth, cur, history, reloadLost, chargedBadCard>>
\* Submit: NIT ok (<=32, "CF", empty) or invalid (422); card valid or not.
YouPay(nitOk, cardOk) ==
  screen = "checkout" /\ co \in {"editing", "invalid_nit", "declined"}
  /\ UNCHANGED <<auth, screen, from, cur, history, reloadLost>>
  /\ IF ~nitOk THEN co' = "invalid_nit" /\ UNCHANGED chargedBadCard
     ELSE IF ~cardOk /\ Fixed THEN co' = "declined" /\ UNCHANGED chargedBadCard
     ELSE co' = "issued" /\ chargedBadCard' = (chargedBadCard \/ ~cardOk)   \* as-is: card never checked or sent
YouSeeInvoice == co = "issued" /\ co' = "closed" /\ Go("billing")
                 /\ UNCHANGED <<auth, cur, history, reloadLost, chargedBadCard>>
YouCancel == screen = "checkout" /\ co \in {"editing", "invalid_nit", "declined"} /\ co' = "closed" /\ Go("plans")
             /\ UNCHANGED <<auth, cur, history, reloadLost, chargedBadCard>>

Next == YouLogIn \/ YouLogInBad \/ YouReload \/ YouLogOut
     \/ (\E p \in Ponds : YouOpenPond(p)) \/ (\E t \in PondTabs : YouPickTab(t))
     \/ YouRunQuery \/ YouBackToList \/ YouOpenBilling \/ YouOpenPlans \/ YouPickPlan
     \/ (\E n, c \in BOOLEAN : YouPay(n, c)) \/ YouSeeInvoice \/ YouCancel

Spec == Init /\ [][Next]_vars

\* ---- Invariants (#96 r6) ----
TabsFixedOrder    == screen \in PondTabs => Tabs(screen) = TabOrder
HistoryScoped     == screen = "consola" => ShownHistory \subseteq {cur}
ReloadKeepsSession == ~reloadLost
PlansViaBilling   == screen = "plans" /\ from # "checkout" => from = "billing"
NoChargeBadCard   == ~chargedBadCard
=============================================================================
