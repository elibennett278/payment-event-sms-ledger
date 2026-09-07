from fastapi import FastAPI, HTTPException

from payment_sms_service.campaign_service import PaymentCampaignService
from payment_sms_service.infrai_client import InfraiClient, InfraiError
from payment_sms_service.models import CampaignRequest, CampaignResult, MessageTracking


app = FastAPI(title="Payment SMS Campaign")


def service() -> PaymentCampaignService:
    return PaymentCampaignService(InfraiClient())


@app.post("/campaigns", response_model=CampaignResult)
def create_campaign(request: CampaignRequest) -> CampaignResult:
    try:
        return service().run(request)
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@app.get("/messages/{message_id}", response_model=MessageTracking)
def get_message(message_id: str) -> MessageTracking:
    try:
        return service().tracking(message_id)
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

