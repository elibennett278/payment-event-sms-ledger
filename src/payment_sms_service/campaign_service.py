from payment_sms_service.infrai_client import InfraiClient
from payment_sms_service.models import (
    CampaignRequest,
    CampaignResult,
    MessageDecision,
    MessageTracking,
    PaymentEvent,
    PaymentState,
)


def _notification(event: PaymentEvent) -> str:
    amount = f"{event.amount_minor / 100:.2f} {event.currency.upper()}"
    if event.state == PaymentState.SETTLED:
        return f"Payment {event.payment_id} settled for {amount}."
    return f"Payment {event.payment_id} was refunded for {amount}."


class PaymentCampaignService:
    def __init__(self, client: InfraiClient) -> None:
        self.client = client

    def run(self, campaign: CampaignRequest) -> CampaignResult:
        decisions: list[MessageDecision] = []
        for event in campaign.events:
            if event.state == PaymentState.REVIEW_REQUIRED:
                decisions.append(
                    MessageDecision(
                        event_id=event.event_id,
                        payment_id=event.payment_id,
                        action="manual_review",
                        reason="Risk-sensitive event held for an operator decision",
                    )
                )
                continue

            sent = self.client.send_sms(
                to=event.customer_phone,
                body=_notification(event),
                idempotency_key=f"payment-event:{event.event_id}",
            )
            decisions.append(
                MessageDecision(
                    event_id=event.event_id,
                    payment_id=event.payment_id,
                    action="sent",
                    reason="Customer notification dispatched",
                    message_id=str(sent["message_id"]),
                )
            )
        return CampaignResult(decisions=decisions)

    def tracking(self, message_id: str) -> MessageTracking:
        return MessageTracking(
            message_id=message_id,
            status=self.client.get_status(message_id),
            events=self.client.get_events(message_id),
        )

