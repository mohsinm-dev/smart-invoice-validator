from fastapi import APIRouter
from .document_routes import router as document_router

# Create the main API router
router = APIRouter()

# Include all route modules
router.include_router(document_router, prefix="/documents", tags=["documents"])
