export const title = "Temp SQL confirmation (bound session)";

/** Reader labels for proposal × credential × outcome. */
export const state = (v) => {
  if (v.proposal === "none") {
    if (v.lastResult === "denied") {
      if (v.denial === "expired_cred") return "NoProposal (expired before issue)";
      if (v.denial === "revoked_cred") return "NoProposal (revoked before issue)";
      return "NoProposal (denied)";
    }
    if (v.cred === "expired") return "NoProposal (credential expired)";
    if (v.cred === "revoked") return "NoProposal (credential revoked)";
    return "NoProposal";
  }
  if (v.proposal === "pending") {
    if (v.lastResult === "denied") {
      if (v.denial === "cross_session") return "Pending (other session denied)";
      if (v.denial === "cross_pond") return "Pending (other pond denied)";
      if (v.denial === "bad_digest") return "Pending (tampered SQL denied)";
      if (v.denial === "bad_action") return "Pending (bad action denied)";
      if (v.denial === "owner_row") return "Pending (owner row denied)";
      if (v.denial === "expired_cred") return "Pending (credential expired)";
      if (v.denial === "revoked_cred") return "Pending (credential revoked)";
      if (v.denial === "proposal_expired") return "Pending (proposal expired)";
      return "Pending (denied)";
    }
    if (v.cred === "expired") return "Pending (credential expired)";
    if (v.cred === "revoked") return "Pending (credential revoked)";
    return "Pending";
  }
  if (v.executed) return "Consumed (SQL ok)";
  if (v.denial === "revoke_before_admit") return "Consumed (revoked before admit)";
  if (v.denial === "expired_cred") return "Consumed (expired before admit)";
  if (v.denial === "replay") return "Consumed (replay denied)";
  return "Consumed (no execution)";
};

export const step = (action, _from, to) => {
  switch (action) {
    case "ExpireCred":
      return "credential expires";
    case "RevokeCred":
      return "presenter revokes";
    case "ProposeOk":
      return "temp write proposes CREATE TABLE";
    case "ProposeDeniedDeadCred":
      return "propose after dead credential [401]";
    case "ConfirmSuccess":
      return "same session confirms [table visible]";
    case "ConfirmClaimAdmit":
      return "claim and admit [awaiting SQL]";
    case "ExecuteOk":
      return "SQL succeeds after admit";
    case "ClaimThenRevokeBeforeAdmit":
      return "revoke after claim before admit [401]";
    case "ClaimThenExpireBeforeAdmit":
      return "expire after claim before admit [401]";
    case "ConfirmCrossSession":
      return "confirm denied [other session]";
    case "ConfirmCrossPond":
      return "confirm denied [other pond]";
    case "ConfirmBadDigest":
      return "confirm denied [tamper]";
    case "ConfirmBadAction":
      return "confirm denied [bad action]";
    case "ConfirmOwnerRow":
      return "confirm denied [owner row]";
    case "ConfirmDeniedDeadCred":
      return "confirm denied [dead credential]";
    case "ProposalExpireWhileLive":
      return "proposal TTL elapses [410]";
    case "Replay":
      return "second confirm [404]";
    case "FailDispatch":
      return "SQL fails after claim [token spent]";
    case "Done":
      return null;
    default:
      return action;
  }
};

export const group = (v) => {
  if (v.proposal === "consumed" && v.executed) return "done_ok";
  if (v.proposal === "consumed") return "done_spent";
  if (v.lastResult === "denied") return "denied";
  if (v.cred === "expired" || v.cred === "revoked") return "ended";
  if (v.proposal === "pending") return "working";
  return "waiting";
};

export const colors = {
  waiting: "tan",
  working: "yellow",
  denied: "orange",
  ended: "pink",
  done_ok: "teal",
  done_spent: "pink",
};
