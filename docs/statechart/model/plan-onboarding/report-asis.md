# PlanOnboarding

TLC reached 13 states and 24 steps. The chart draws 5 states and 5 arrows.
The chart does not draw 9 steps that stay in one chart state.
The view hides 4 steps, so the chart does not draw them.

## RegisterIsSandbox breaks
The shortest path has 1 step:
0. Signup form
1. you submit signup [passwords differ]: Check your email

## MismatchBlocksRegister breaks
The shortest path has 1 step:
0. Signup form
1. you submit signup [passwords differ]: Check your email

## MustOnboard breaks
The shortest path has 4 steps:
0. Signup form
1. you submit signup [passwords differ]: Check your email
2. you open login: Login
3. you verify email: Login
4. you log in: App · none (no gate)

## NoSilentMicro breaks
The shortest path has 5 steps:
0. Signup form
1. you submit signup [passwords differ]: Check your email
2. you open login: Login
3. you verify email: Login
4. you log in: App · none (no gate)
5. you create a pond [auto-micro]: App · micro (no gate)

## Rules that hold
OnboardingOnce
