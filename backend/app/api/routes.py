from fastapi import APIRouter
from app.api import contracts, document_routes

api_router = APIRouter()

# Include sub-routers
api_router.include_router(contracts.router, prefix="/contracts", tags=["contracts"])
api_router.include_router(document_routes.router, prefix="/documents", tags=["documents"])