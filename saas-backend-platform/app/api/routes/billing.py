from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant, get_current_user, require_roles
from app.core.database import get_db
from app.models.enums import UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.billing import CheckoutSessionRequest, CheckoutSessionResponse, SubscriptionOut
from app.services import billing_service

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
def create_checkout_session(
    payload: CheckoutSessionRequest,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Only owners/admins can change billing. Returns a Stripe-hosted checkout URL."""
    checkout_url = billing_service.create_checkout_session(db, tenant, current_user.email, payload.plan)
    return CheckoutSessionResponse(checkout_url=checkout_url)


@router.get("/subscription", response_model=SubscriptionOut | None)
def get_subscription(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return billing_service.get_current_subscription(db, tenant.id)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
    db: Session = Depends(get_db),
):
    """
    Public endpoint that receives events directly from Stripe.
    Signature is verified against STRIPE_WEBHOOK_SECRET before any data is trusted.
    """
    if stripe_signature is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe-Signature header")

    payload = await request.body()
    event = billing_service.construct_webhook_event(payload, stripe_signature)

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type == "checkout.session.completed":
        billing_service.handle_checkout_completed(db, data_object)
    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        billing_service.handle_subscription_updated(db, data_object)

    return {"received": True}
