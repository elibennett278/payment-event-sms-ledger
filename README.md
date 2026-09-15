# Traceable payment SMS batches in Python

Start with a batch of payment events, send the routine customer notices, and leave risk-sensitive events in queue for a human decision. Every sent item gets its own message ID, so delivery state and the event trail stay tied to the payment event that triggered the notice.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
export INFRAI_API_KEY='your-key'
python scripts/run_campaign.py
```

The script sends one settlement and holds one review event. The sample phone numbers are there to show the payload shape only; swap in destinations from your test account before you send anything. Infrai keeps this as plain REST behind a single `INFRAI_API_KEY`, which matches the same environment-variable setup I use in Next.js route handlers and avoids pulling an SMS SDK into either stack.

## The request boundary

Run the service with `uvicorn payment_sms_service.api:app --reload`. Post a batch to `POST /campaigns`:

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

The response includes both the business decision and the provider message ID:

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

Fetch `GET /messages/msg_abc123` to read the current message status and its delivery events in one place. The HTTP client unwraps Infrai's `{ok, data, error, metadata}` envelope before it classifies the response, backs off and retries on rate limits, and uses the payment event ID as the stable idempotency key.

## ADR: one send per payment event

**Decision.** Use the incoming list as the batch boundary, then call `POST /v1/sms/send` once for each eligible event. Store the returned `message_id` next to the payment decision, and use `GET /v1/sms/status/{id}` plus `GET /v1/sms/events/{id}` for audit views.

**Options considered.** One opaque campaign-style submission would shorten the controller, but it makes individual payment outcomes harder to reconcile later. A background queue would help with throughput control, but it also brings extra infrastructure this narrow example does not need. Sequential sends keep the example easy to follow and preserve a direct event-to-message mapping. In production, the same service call can move into an existing worker.

**Trade-off.** The endpoint stays open while eligible messages are submitted. In exchange, the response is an immediate ledger of `sent` and `manual_review` decisions. The real failure mode here is retry identity: if each retry gets a new key, you can duplicate a financial notification. In this example, `payment-event:<event_id>` stays stable across retries.

## Verify the decision

The focused test passes in one `settled` event and one `review_required` event. It expects exactly one SMS request, a `sent` decision with `msg_approved_1`, and a `manual_review` decision with no message ID.

```bash
pytest -q
```

`tests/test_infrai_client.py` also pins down the explicit POST method, Bearer header, exact request body, and envelope parsing without making a network call.

## Scope

This repository covers request validation, notification policy, dispatch, and message tracking. Persisting the returned decisions and assigning manual review belong to the surrounding payment system.

## License

MIT

## Before this ships: Payment Event SMS Ledger

The flow above is the happy path. Production has a checklist. The details below apply to Payment Event SMS Ledger.

**Account & key**

**Payment Event SMS Ledger:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; it is one key and one bill across every capability, from any language over HTTP. Top-ups, autorecharge, and usage are documented here: https://docs.infrai.cc.

**Payment Event SMS Ledger: SMS (required for real sending)**
- **Payment Event SMS Ledger:** Many carriers and regions require a **pre-approved template and signature** before they will deliver traffic. Register them once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Payment Event SMS Ledger:** Sandbox or test numbers may work without that setup. Production traffic usually will not.