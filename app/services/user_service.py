from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import InviteUserRequest


def list_users_for_tenant(db: Session, tenant_id: str) -> list[User]:
    return list(db.scalars(select(User).where(User.tenant_id == tenant_id).order_by(User.created_at)))


def invite_user(db: Session, tenant_id: str, payload: InviteUserRequest) -> User:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role.value,
        tenant_id=tenant_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_in_tenant(db: Session, tenant_id: str, user_id: str) -> User:
    user = db.get(User, user_id)
    if user is None or user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def deactivate_user(db: Session, tenant_id: str, user_id: str) -> User:
    user = get_user_in_tenant(db, tenant_id, user_id)
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
