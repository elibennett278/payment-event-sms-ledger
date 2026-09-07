from typing import Any

from payment_sms_service.campaign_service import PaymentCampaignService
from payment_sms_service.models import CampaignRequest


class RecordingClient:
    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def send_sms(self, *, to: str, body: str, idempotency_key: str) -> dict[str, Any]:
        self.sent.append({"to": to, "body": body, "idempotency_key": idempotency_key})
        return {"message_id": "msg_approved_1"}


def test_campaign_sends_settlement_and_holds_risk_review() -> None:
    campaign = CampaignRequest.model_validate(
        {
            "events": [
                {
                    "event_id": "evt_1",
                    "payment_id": "pay_1",
                    "customer_phone": "+15555550101",
                    "amount_minor": 1250,
                    "currency": "USD",
                    "state": "settled",
                },
                {
                    "event_id": "evt_2",
                    "payment_id": "pay_2",
                    "customer_phone": "+15555550102",
                    "amount_minor": 8800,
                    "currency": "USD",
                    "state": "review_required",
                },
            ]
        }
    )
    client = RecordingClient()

    result = PaymentCampaignService(client).run(campaign)  # type: ignore[arg-type]

    assert [decision.action for decision in result.decisions] == ["sent", "manual_review"]
    assert result.decisions[0].message_id == "msg_approved_1"
    assert result.decisions[1].message_id is None
    assert client.sent == [
        {
            "to": "+15555550101",
            "body": "Payment pay_1 settled for 12.50 USD.",
            "idempotency_key": "payment-event:evt_1",
        }
    ]

