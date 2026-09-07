from enum import Enum

from pydantic import BaseModel, Field


class PaymentState(str, Enum):
    SETTLED = "settled"
    REFUNDED = "refunded"
    REVIEW_REQUIRED = "review_required"


class PaymentEvent(BaseModel):
    event_id: str = Field(min_length=1)
    payment_id: str = Field(min_length=1)
    customer_phone: str = Field(min_length=7)
    amount_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    state: PaymentState


class CampaignRequest(BaseModel):
    events: list[PaymentEvent] = Field(min_length=1, max_length=100)


class MessageDecision(BaseModel):
    event_id: str
    payment_id: str
    action: str
    reason: str
    message_id: str | None = None


class CampaignResult(BaseModel):
    decisions: list[MessageDecision]


class MessageTracking(BaseModel):
    message_id: str
    status: dict[str, object]
    events: list[dict[str, object]]

