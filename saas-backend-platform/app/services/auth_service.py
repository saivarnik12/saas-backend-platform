import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenPair


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


def _unique_slug(db: Session, base_slug: str) -> str:
    slug = base_slug
    suffix = 1
    while db.scalar(select(Tenant).where(Tenant.slug == slug)) is not None:
        suffix += 1
        slug = f"{base_slug}-{suffix}"
    return slug


def signup(db: Session, payload: SignupRequest) -> TokenPair:
    existing_user = db.scalar(select(User).where(User.email == payload.email))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    slug = _unique_slug(db, _slugify(payload.organization_name))

    tenant = Tenant(name=payload.organization_name, slug=slug)
    db.add(tenant)
    db.flush()  # populate tenant.id without committing yet

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.OWNER.value,
        tenant_id=tenant.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenPair(
        access_token=create_access_token(user.id, {"tenant_id": user.tenant_id, "role": user.role}),
        refresh_token=create_refresh_token(user.id),
    )


def login(db: Session, payload: LoginRequest) -> TokenPair:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")

    return TokenPair(
        access_token=create_access_token(user.id, {"tenant_id": user.tenant_id, "role": user.role}),
        refresh_token=create_refresh_token(user.id),
    )


def refresh_access_token(db: Session, refresh_token: str) -> str:
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user_id = payload.get("sub")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer valid")

    return create_access_token(user.id, {"tenant_id": user.tenant_id, "role": user.role})
