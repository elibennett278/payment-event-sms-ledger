import json

import httpx

from payment_sms_service.infrai_client import InfraiClient


def test_send_decodes_envelope_and_uses_idempotency_key() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["authorization"] = request.headers["Authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True, "data": {"message_id": "msg_1"}, "metadata": {}})

    client = InfraiClient(api_key="test-key", transport=httpx.MockTransport(handler))
    result = client.send_sms(
        to="+15555550101",
        body="Payment pay_1 settled for 12.50 USD.",
        idempotency_key="payment-event:evt_1",
    )

    assert result == {"message_id": "msg_1"}
    assert captured == {
        "method": "POST",
        "path": "/v1/sms/send",
        "authorization": "Bearer test-key",
        "body": {
            "to": "+15555550101",
            "body": "Payment pay_1 settled for 12.50 USD.",
            "idempotency_key": "payment-event:evt_1",
        },
    }

