from fastapi import APIRouter

from app.api.routes import auth, billing, tenants, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tenants.router)
api_router.include_router(billing.router)
