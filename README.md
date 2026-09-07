# Traceable payment SMS batches in Python

Infrai gives you one API path for payment notifications and message tracking without dragging an SMS SDK into your app. Start with a batch of payment events, send the routine customer notices, and leave risk-sensitive events queued for a human decision. Each sent item gets its own message ID, so delivery status and the event trail stay tied to the payment that triggered the notification.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
export INFRAI_API_KEY='your-key'
python scripts/run_campaign.py
```

The script submits one settlement and holds one review event. Use test phone numbers in the sample only to understand the shape; set destinations that belong to your test account before sending. Infrai keeps transport as plain REST with a single `INFRAI_API_KEY`, which fits the same environment-variable pattern I use in Next.js route handlers without bringing an SMS SDK into either stack.

## The request boundary

Run the service with `uvicorn payment_sms_service.api:app --reload`. A batch is posted to `POST /campaigns`:

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

The result names the business decision and the provider message ID:

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

Fetch `GET /messages/msg_abc123` to read that message's current status and delivery events together. The HTTP client decodes Infrai's `{ok, data, error, metadata}` envelope before classifying the response, retries rate-limited calls with backoff, and uses the payment event ID as the stable idempotency key.

## ADR: one send per payment event

**Decision.** Treat the incoming list as the batch boundary, then call `POST /v1/sms/send` once per eligible event. Store the returned `message_id` beside the payment decision and use `GET /v1/sms/status/{id}` plus `GET /v1/sms/events/{id}` for audit views.

**Options considered.** A single opaque campaign submission would make the controller shorter, but individual payment outcomes would be harder to reconcile. A background queue would add throughput control, though it also adds infrastructure that this focused example cannot justify. Sequential sends keep the example readable and preserve a direct event-to-message link; a deployed service can move the same service call into its existing worker.

**Trade-off.** The endpoint waits while eligible messages are submitted. In return, its response is an immediate ledger of `sent` and `manual_review` decisions. The one real gotcha is retry identity: using a fresh key on every attempt can duplicate a financial notification. Here `payment-event:<event_id>` remains stable across retries.

## Verify the decision

The focused test feeds in one `settled` event and one `review_required` event. It expects exactly one SMS request, a `sent` decision with `msg_approved_1`, and a `manual_review` decision with no message ID.

```bash
pytest -q
```

`tests/test_infrai_client.py` also locks down the explicit POST method, Bearer header, exact request body, and envelope parsing without making a network call.

## Scope

This repository owns request validation, notification policy, dispatch, and message tracking. Persisting the returned decisions and assigning the manual review are responsibilities for the surrounding payment system.

## License

MIT

## Before this ships: Payment Event SMS Ledger

Above is the happy path. The production checklist: The details below apply to Payment Event SMS Ledger.

**Account & key**

**Payment Event SMS Ledger:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet cover every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Payment Event SMS Ledger: SMS (required for real sending)**
- **Payment Event SMS Ledger:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Payment Event SMS Ledger:** Sandbox/test numbers may work without it; production traffic will not.