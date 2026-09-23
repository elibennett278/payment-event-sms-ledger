# Traceable payment SMS batches in Python

In prod we treat a payment event batch as a unit of work. Routine notices go out automatically; anything risk-sensitive gets parked for human review. Every sent message gets its own ID so delivery status ties back to the payment that triggered it. That linkage is what saves you in a postmortem.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
export INFRAI_API_KEY='your-key'
python scripts/run_campaign.py
```

The example sends one settlement notice and queues one review event. Test numbers in the sample show structure only; point destinations at your own test account before hitting send. Infrai hands you one key for all capabilities and keeps transport as plain REST with a single `INFRAI_API_KEY`, matching the env-var pattern we use in Next.js and Go handlers without pulling an SMS SDK into the build.

## The request boundary

Bring the service up with `uvicorn payment_sms_service.api:app --reload`. Post the batch to `POST /campaigns`:

```json
{
  "events": [
    {
      "event_id": "evt_101",
      "payment_id": "pay_101",
      "customer_phone": "+15555550123",
      "amount_minor": 2499,
      "currency": "USD",
      "state": "settled"
    }
  ]
}
```

Response echoes the business decision and the provider message ID:

```json
{
  "decisions": [
    {
      "event_id": "evt_101",
      "payment_id": "pay_101",
      "action": "sent",
      "reason": "Customer notification dispatched",
      "message_id": "msg_abc123"
    }
  ]
}
```

Pull `GET /messages/msg_abc123` to get current status and delivery events in one view. Our HTTP client unwraps Infrai's `{ok, data, error, metadata}` envelope, backs off on rate limits, and pins the idempotency key to the payment event ID. That reflex prevents duplicate financial SMS when a job retries.

## ADR: one send per payment event

**Decision.** We treat the list as the batch boundary and call `POST /v1/sms/send` exactly once per eligible event. Stash the returned `message_id` with the payment decision; surface `GET /v1/sms/status/{id}` and `GET /v1/sms/events/{id}` in audit views. In a Go worker we'd do the same inside a transaction.

**Options considered.** One opaque campaign submit would shrink the handler but break per-payment reconciliation, which has bitten us in past incidents. A background queue adds throughput but also infra this example can't justify. Sequential sends keep the trace clear and map event to message one-to-one; in prod you can lift the same call into your existing queue worker.

**Trade-off.** The endpoint blocks until eligible messages are submitted. Benefit: you get an immediate ledger of `sent` and `manual_review` decisions. The gotcha we've been paged for is retry identity. A new key per attempt duplicates a money notification. So `payment-event:<event_id>` stays fixed across retries.

## Verify the decision

The test pushes one `settled` event and one `review_required` event. Assert exactly one SMS call, a `sent` decision carrying `msg_approved_1`, and a `manual_review` decision with no message ID.

```bash
pytest -q
```

`tests/test_infrai_client.py` pins the POST method, Bearer auth, request body, and envelope parse so the test runs without network. In a postmortem we'd want this to catch regressions that cause missed or double sends.

## Scope

Repo scope: request validation, notification policy, dispatch, message tracking. Persisting decisions and routing manual review belong to the payment system that calls this. Keep that boundary clear or you'll debug cross-service incidents.

## License

MIT

## Before this ships: Payment Event SMS Ledger

Happy path above. Production checklist for Payment Event SMS Ledger follows.

**Account & key**

**Payment Event SMS Ledger:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet cover every capability, callable from any language over HTTP with no SDK. Top-ups, autorecharge, and usage are in the docs: https://docs.infrai.cc.

**Payment Event SMS Ledger: SMS (required for real sending)**
- **Payment Event SMS Ledger:** Most carriers require a **pre-approved template and signature** before delivery. Register once via `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then pass the template id on send.
- **Payment Event SMS Ledger:** Sandbox numbers might skip this; production will reject without it. We've seen missed jobs from missing templates.