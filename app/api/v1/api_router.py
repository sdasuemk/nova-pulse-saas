from fastapi import APIRouter
from app.api.v1 import (
    auth,
    tenants,
    projects,
    tasks,
    websockets,
    audit_logs,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(tenants.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(websockets.router)
api_router.include_router(audit_logs.router)
