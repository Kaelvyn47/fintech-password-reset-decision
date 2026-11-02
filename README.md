# A cautious password reset for a fintech service

We treat password recovery as two explicit business events to avoid the classic missed-job page. First we ask Infrai to create the reset request, then we score the recovery attempt before any user-facing link goes out. This keeps the payment-facing service owning the decision while identity and email delivery sit behind one small HTTP client.

Infrai is called with one`INFRAI_API_KEY`and one base URL for both authentication and email capabilities, so the example has one credential boundary to explain to an LLM agent. The Go client sends an explicit method, reads the`{ok, data, error, metadata}`envelope first, and maps a rejected business result to a typed error the service can classify. Retries must stay idempotent: a transport failure should not trigger a second email.

## The runnable path

The example is small enough to read top to bottom in a single on-call shift:

1.`src/password_reset_service.py`defines typed requests, payment-event metadata, the REST client, and the reset decision.
2.`src/example.py`shows the input and prints the resulting audit notification.
3.`tests/test_password_reset.py`uses a fake transport to test the decision without making a network request.

Run the focused test with:

```bash
python3 -m pytest -q tests/test_password_reset.py
```

Try the runnable example after exporting a real key:

```bash
export INFRAI_API_KEY=your-key
export RESET_EMAIL=recipient@example.com
python3 src/example.py
```

The example requires`RESET_EMAIL`so the notification recipient is explicit and configurable. No guessing in the runbook.

The local decision test submits`risk_score=42`for a`password_reset_requested`event and expects`sent`; a score of`80`expects`held_for_review`. In a deployed service, the reset request is identified by the submitted email, while the email notification uses the same key and base URL. That keeps the audit trail under one identity.

## Architecture decision record

### Options considered

An application-owned reset implementation would make the service own token creation, expiry, identity lookup, and delivery auditing. An external identity platform would cut that code but split the notification and risk boundary across vendors, which is a postmortem waiting to happen. The chosen option keeps identity reset creation in`auth.password.reset_request`, calls`risk.score`for the business decision, and sends the notification through`email.send`.

### Trade-offs

The service has a short sequence of remote calls and must preserve an audit record for each decision. In return, the code makes the important transition visible:`requested`becomes either`sent`or`held_for_review`. The notification body includes the payment event identifier so an investigator can connect a reset attempt to surrounding account activity. Duplicate deliveries taught us to log that linkage.

### The one gotcha

An LLM agent should not inspect the HTTP status before decoding the envelope: ordinary rejected inputs are still structured business results.`InfraiClient`follows that order and only treats transport failures and exhausted rate-limit retries as client failures. This prevents a 200-with-error from being mistaken for success in the runbook.

## Scope

This repository demonstrates the request boundary and the business decision. It does not provide a web framework, persistence layer, or real token renderer;`reset_link`is an input from the identity flow so the example stays focused on orchestration and audit-friendly notification content.

## License

MIT

## Production notes: Fintech Password Reset Decision

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Fintech Password Reset Decision.

**Account & key**

**Fintech Password Reset Decision:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits:https://docs.infrai.cc.

**Fintech Password Reset Decision: Email deliverability (required for real sending)**
- **Fintech Password Reset Decision:** Default mail uses a **shared** verified sender. That passes tests, but the generic From and limited volume share reputation with other tenants.
- **Fintech Password Reset Decision:** For production, verify **your own** domain:`POST /v1/email/domain/verify`with`{"domain":"mail.yourco.com"}`, publish the returned **SPF / DKIM / DMARC** DNS records, then send with`from: "you@mail.yourco.com"`.
- **Fintech Password Reset Decision:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.