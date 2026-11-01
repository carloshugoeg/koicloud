---------------------------- MODULE ViolationProbe ----------------------------
(* Two reachable states. Inv holds in the first and fails in the second,
   so TLC -continue finishes and still prints "No error has been found". *)
VARIABLE x
Init == x = 0
Next == x = 0 /\ x' = 1
Spec == Init /\ [][Next]_x
Inv == x = 0
=============================================================================
