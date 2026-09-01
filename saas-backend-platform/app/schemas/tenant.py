from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import PlanTier


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    plan: PlanTier
    created_at: datetime
