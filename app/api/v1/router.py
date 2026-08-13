from fastapi import APIRouter

from app.api.v1 import admin_crud, auth, dashboard, public

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(admin_crud.router)
api_router.include_router(dashboard.router)
api_router.include_router(public.router)

