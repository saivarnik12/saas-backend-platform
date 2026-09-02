from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import PlanTier, SubscriptionStatus


class CheckoutSessionRequest(BaseModel):
    plan: PlanTier


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    plan: PlanTier
    status: SubscriptionStatus
    current_period_end: datetime | None
