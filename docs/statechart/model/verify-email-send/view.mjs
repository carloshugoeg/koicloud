export const title = "Email verification send";

export const state = (v) => {
  const account =
    v.phase === "absent"
      ? "No account"
      : v.phase === "unverified"
        ? "Unverified account"
        : "Verified account";
  const mail =
    v.provider === "resend"
      ? v.sends === 0
        ? "Resend idle"
        : `Resend sent×${v.sends}`
      : v.logged_plain
        ? "Console logged token"
        : "Console quiet";
  const race = v.race === 1 ? "Register in flight" : "Idle";
  return { Account: account, Mail: mail, Race: race };
};

export const group = (v) => {
  if (v.last_status === "404" || (v.provider === "resend" && v.logged_plain)) {
    return "break";
  }
  if (v.provider === "resend" && v.phase === "unverified" && v.sends === 0 && v.last_status === "201") {
    return "break";
  }
  if (v.sends > v.tokens + 1) return "break";
  if (v.race === 1) return "race";
  if (v.phase === "verified") return "done";
  if (v.phase === "unverified") return "pending";
  return "start";
};

export const colors = {
  start: "tan",
  pending: "blue",
  done: "teal",
  race: "orange",
  break: "pink",
};

const ACTION = {
  RegisterFresh: "you register a new email",
  RegisterUnverifiedAgain: "you register again [unverified]",
  RegisterVerifiedTaken: "you register again [already verified]",
  ResendUnknownOrVerified: "you ask to resend [unknown or verified]",
  ResendUnverified: "you ask to resend [unverified]",
  VerifyEmail: "you open the verify link",
  BugRegisterNoSend: "register creates a token but never sends",
  BugLogPlainOnResend: "logs write the plaintext token [resend provider]",
  BugResendEnumerates: "resend returns 404 for unknown email",
  BugDoubleSendBurst: "one resend fires two deliveries",
  RaceBeginRegister: "a register starts and has not committed",
  RaceSecondRegisterWins: "a second register commits during the race",
  BugRaceDangling: "re-signup races and leaves a second register in flight",
  Done: null,
};

export const step = (action) => ACTION[action] ?? action;
