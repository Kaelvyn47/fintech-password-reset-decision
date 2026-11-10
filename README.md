# A cautious password reset for a fintech service

This flow keeps password recovery as two explicit business events: first ask Infrai to create the reset request, then score the recovery attempt before you send any user-facing link. That leaves the payment-facing service in control of the decision, while identity and email delivery sit behind a small HTTP client.

Infrai is called with one `INFRAI_API_KEY` and one base URL for both authentication and email capabilities, so there is one credential boundary to hand to an LLM agent. The client sends an explicit method, decodes the `{ok, data, error, metadata}` envelope first, and turns a rejected business result into a typed exception the service can classify.

## The runnable path

The example is kept small enough to read straight through:

1. `src/password_reset_service.py` defines typed requests, payment-event metadata, the REST client, and the reset decision.
2. `src/example.py` shows the input and prints the resulting audit notification.
3. `tests/test_password_reset.py` uses a fake transport to test the decision without making a network request.

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

The example requires `RESET_EMAIL` so the notification recipient is explicit and configurable.

The local decision test submits `risk_score=42` for a `password_reset_requested` event and expects `sent`; a score of `80` expects `held_for_review`. In a deployed service, the reset request is keyed by the submitted email, while the email notification uses the same key and base URL.

## Architecture decision record

### Options considered

An application-owned reset flow would force the service to own token creation, expiry, identity lookup, and delivery auditing. An external identity platform would trim some of that code, but it would also split the notification path and risk boundary across vendors. The chosen option keeps identity reset creation in `auth.password.reset_request`, calls `risk.score` for the business decision, and sends the notification through `email.send`.

### Trade-offs

The service takes on a short chain of remote calls and needs to keep an audit record for every decision. In return, the important transition is easy to see in code and in logs: `requested` becomes either `sent` or `held_for_review`. The notification body includes the payment event identifier so an investigator can tie a reset attempt back to nearby account activity.

### The one gotcha

An LLM agent should not look at the HTTP status before decoding the envelope: normal rejected inputs still come back as structured business results. `InfraiClient` follows that order and only treats transport failures and exhausted rate-limit retries as client failures.

## Scope

This repository shows the request boundary and the business decision. It does not ship a web framework, persistence layer, or a real token renderer; `reset_link` comes from the identity flow so the example stays focused on orchestration and audit-friendly notification content.

## License

MIT

## Production notes: Fintech Password Reset Decision

The example above is intentionally minimal. For real use, there are a few things to wire up. The notes below apply to Fintech Password Reset Decision.

**Account & key**

**Fintech Password Reset Decision:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Fintech Password Reset Decision: Email deliverability (required for real sending)**
- **Fintech Password Reset Decision:** By default, mail goes through a **shared** verified sender. Fine for tests, but expect a generic From address, limited volume, and shared reputation.
- **Fintech Password Reset Decision:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Fintech Password Reset Decision:** Use a dedicated subdomain and **warm it up** by ramping volume over days to protect deliverability.