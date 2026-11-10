export const title = "Plan onboarding (signup → first login → choice → app)";

export const colors = {
  Auth: "blue",
  Onboarding: "orange",
  App: "teal",
};

export function state(v: Record<string, unknown>): string {
  const screen = String(v.screen);
  const plan = String(v.plan);
  const done = v.onboardingDone === true || v.onboardingDone === "TRUE";
  const session = v.session === true || v.session === "TRUE";
  if (screen === "signup") return "Signup form";
  if (screen === "verify_mail") return "Check your email";
  if (screen === "login") return "Login";
  if (screen === "onboarding") return `Choose plan [${plan}]`;
  if (screen === "checkout") return "Checkout (simulated)";
  if (screen === "app") {
    if (!session) return "App (signed out)";
    return done ? `App · ${plan}` : `App · ${plan} (no gate)`;
  }
  return screen;
}

export function group(v: Record<string, unknown>): string {
  const screen = String(v.screen);
  if (screen === "signup" || screen === "verify_mail" || screen === "login") return "Auth";
  if (screen === "onboarding" || screen === "checkout") return "Onboarding";
  return "App";
}

export function step(
  action: string,
  from: Record<string, unknown>,
  to: Record<string, unknown>,
): string | null {
  if (action === "Done") return null;
  if (action.startsWith("YouSubmitSignup")) {
    const match = to.pwdMatch === true || to.pwdMatch === "TRUE";
    return match ? "you submit signup" : "you submit signup [passwords differ]";
  }
  if (action === "YouOpenLogin") return "you open login";
  if (action === "YouVerifyEmail") return "you verify email";
  if (action === "YouLogIn") return "you log in";
  if (action === "YouLogInUnverified") return "you try login [unverified]";
  if (action === "YouReloadApp") return "you reload or open /app";
  if (action.startsWith("YouChoosePaid")) return "you choose Micro or Pro";
  if (action === "YouPayOk") return "payment succeeds";
  if (action === "YouPayFail") return "payment fails";
  if (action === "YouContinueFree") return "you continue free (sandbox)";
  if (action === "YouCreatePondAsIs") return "you create a pond [auto-micro]";
  return action;
}
