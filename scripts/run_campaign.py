import json

from payment_sms_service.campaign_service import PaymentCampaignService
from payment_sms_service.infrai_client import InfraiClient
from payment_sms_service.models import CampaignRequest


sample = CampaignRequest.model_validate(
    {
        "events": [
            {
                "event_id": "evt_demo_101",
                "payment_id": "pay_101",
                "customer_phone": "+15555550123",
                "amount_minor": 2499,
                "currency": "USD",
                "state": "settled",
            },
            {
                "event_id": "evt_demo_102",
                "payment_id": "pay_102",
                "customer_phone": "+15555550124",
                "amount_minor": 7300,
                "currency": "USD",
                "state": "review_required",
            },
        ]
    }
)

result = PaymentCampaignService(InfraiClient()).run(sample)
print(json.dumps(result.model_dump(), indent=2))

