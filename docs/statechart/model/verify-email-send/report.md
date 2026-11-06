# VerifyEmailSend

TLC reached 84 states and 244 steps. The chart draws 11 states and 14 arrows.
The chart does not draw 171 steps that stay in one chart state.
The step you register a new email changes Account and Mail at the same time.
The step a second register commits during the race changes Account, Mail and Race at the same time.
The step re-signup races and leaves a second register in flight changes Account and Mail at the same time.

## ResendAlwaysNeutral breaks
The shortest path has 1 step:
0. Account No account, Mail Console quiet, Race Idle
1. resend returns 404 for unknown email: Account No account, Mail Console quiet, Race Idle

## SendWhenResendRegisters breaks
The shortest path has 1 step:
0. Account No account, Mail Resend idle, Race Idle
1. register creates a token but never sends: Account Unverified account, Mail Resend idle, Race Idle

## RaceSettles breaks
The shortest path has 2 steps:
0. Account No account, Mail Console quiet, Race Idle
1. a register starts and has not committed: Account No account, Mail Console quiet, Race Register in flight
2. re-signup races and leaves a second register in flight: Account Unverified account, Mail Console logged token, Race Register in flight

## NoDoubleBurst breaks
The shortest path has 2 steps:
0. Account No account, Mail Resend idle, Race Idle
1. you register a new email: Account Unverified account, Mail Resend sent×1, Race Idle
2. one resend fires two deliveries: Account Unverified account, Mail Resend sent×3, Race Idle

## NoPlaintextOnResend breaks
The shortest path has 2 steps:
0. Account No account, Mail Resend idle, Race Idle
1. you register a new email: Account Unverified account, Mail Resend sent×1, Race Idle
2. logs write the plaintext token [resend provider]: Account Unverified account, Mail Resend sent×1, Race Idle

## Rules that hold
TypeOK, NoDeadlock
