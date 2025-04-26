from fastapi import APIRouter
from app.api import contracts, invoices

api_router = APIRouter()

# Include sub-routers
api_router.include_router(contracts.router, prefix="/contracts", tags=["contracts"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])