from datetime import datetime, timezone

import stripe
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import PlanTier, SubscriptionStatus
from app.models.subscription import Subscription
from app.models.tenant import Tenant

stripe.api_key = settings.STRIPE_SECRET_KEY

_PRICE_ID_BY_PLAN = {
    PlanTier.PRO: settings.STRIPE_PRICE_ID_PRO,
    PlanTier.ENTERPRISE: settings.STRIPE_PRICE_ID_ENTERPRISE,
}


def _get_or_create_stripe_customer(tenant: Tenant, owner_email: str) -> str:
    if tenant.stripe_customer_id:
        return tenant.stripe_customer_id

    customer = stripe.Customer.create(
        email=owner_email,
        name=tenant.name,
        metadata={"tenant_id": tenant.id},
    )
    return customer["id"]


def create_checkout_session(db: Session, tenant: Tenant, owner_email: str, plan: PlanTier) -> str:
    if plan == PlanTier.FREE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Free plan does not require checkout")

    price_id = _PRICE_ID_BY_PLAN.get(plan)
    if not price_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown plan")

    customer_id = _get_or_create_stripe_customer(tenant, owner_email)
    if tenant.stripe_customer_id != customer_id:
        tenant.stripe_customer_id = customer_id
        db.commit()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=settings.FRONTEND_SUCCESS_URL,
        cancel_url=settings.FRONTEND_CANCEL_URL,
        metadata={"tenant_id": tenant.id, "plan": plan.value},
    )
    return session["url"]


def _plan_from_price_id(price_id: str) -> PlanTier:
    for plan, pid in _PRICE_ID_BY_PLAN.items():
        if pid == price_id:
            return plan
    return PlanTier.PRO  # sensible default fallback


def construct_webhook_event(payload: bytes, sig_header: str):
    try:
        return stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:  # type: ignore[attr-defined]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload") from exc


def handle_checkout_completed(db: Session, event_data: dict) -> None:
    metadata = event_data.get("metadata", {}) or {}
    tenant_id = metadata.get("tenant_id")
    plan_value = metadata.get("plan", PlanTier.PRO.value)

    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        return  # unknown tenant - ignore silently (would be logged in production)

    stripe_subscription_id = event_data.get("subscription")
    tenant.plan = plan_value
    tenant.stripe_subscription_id = stripe_subscription_id

    subscription = Subscription(
        tenant_id=tenant.id,
        stripe_subscription_id=stripe_subscription_id,
        plan=plan_value,
        status=SubscriptionStatus.ACTIVE.value,
        current_period_end=None,
    )
    db.add(subscription)
    db.commit()


def handle_subscription_updated(db: Session, event_data: dict) -> None:
    stripe_subscription_id = event_data.get("id")
    status_value = event_data.get("status", SubscriptionStatus.ACTIVE.value)
    period_end_ts = event_data.get("current_period_end")

    subscription = db.scalar(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
    )
    if subscription is None:
        return

    subscription.status = status_value
    if period_end_ts:
        subscription.current_period_end = datetime.fromtimestamp(period_end_ts, tz=timezone.utc)

    tenant = db.get(Tenant, subscription.tenant_id)
    if tenant is not None and status_value in (SubscriptionStatus.CANCELED.value, SubscriptionStatus.INCOMPLETE.value):
        tenant.plan = PlanTier.FREE.value

    db.commit()


def get_current_subscription(db: Session, tenant_id: str) -> Subscription | None:
    return db.scalar(
        select(Subscription)
        .where(Subscription.tenant_id == tenant_id)
        .order_by(Subscription.created_at.desc())
    )
