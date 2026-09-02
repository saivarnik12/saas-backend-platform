from fastapi import APIRouter, Depends

from app.api.deps import get_current_tenant
from app.models.tenant import Tenant
from app.schemas.tenant import TenantOut

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/me", response_model=TenantOut)
def read_current_tenant(tenant: Tenant = Depends(get_current_tenant)):
    return tenant
