# Verify-email send (register → resend → verified)

pstack `/statechart` model for wiring `notifications.send("verify_email")` on
register and `POST /auth/resend-verification`.

## Rules

| Invariant | Reader sentence |
|---|---|
| `NoPlaintextOnResend` | With Resend, logs never hold the plaintext verify token. |
| `ResendAlwaysNeutral` | Resend-verification never returns 404 (no email enumeration). |
| `SendWhenResendRegisters` | A successful register under Resend calls `send`. |
| `NoDoubleBurst` | One resend request does not fire two deliveries. |
| `RaceSettles` | A re-signup race does not leave a second register in flight. |

## Reproduce

```sh
export TLA2TOOLS=/path/to/tla2tools.jar JAVA=$(command -v java)
<path-to-pstack-statechart>/scripts/statechart \
  VerifyEmailSend.tla \
  --config VerifyEmailSend.cfg \
  --view view.mjs \
  --out /tmp/verify-email-send-out
```

`chart.mmd` is the Mermaid diagram included in the PR.
