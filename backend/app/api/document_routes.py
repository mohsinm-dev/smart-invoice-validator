from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import List, Dict, Any, Optional
import io
from ..services.document_processor import DocumentProcessor, VerificationResult
from ..config import settings
from app.models.invoice import ExtractedInvoice, ComparisonResult
from app.services.comparison_service import compare_invoice_to_contract

router = APIRouter()

# Initialize the document processor with API key from settings
document_processor = DocumentProcessor(
    api_key=settings.GEMINI_API_KEY,
    confidence_threshold=settings.CONFIDENCE_THRESHOLD,
    model_name=settings.GEMINI_MODEL
)

@router.post("/process-document")
async def process_document(file: UploadFile = File(...)):
    """
    Process a single document and extract purchase order items.
    
    Args:
        file (UploadFile): The document file to process
        
    Returns:
        Dict containing:
            - items: List of extracted items (if successful)
            - verification: Verification result
            - error: Error message (if any)
    """
    try:
        # Read the file into memory
        contents = await file.read()
        document = io.BytesIO(contents)
        
        # Process the document
        items, verification = document_processor.process_document(document)
        
        # Prepare the response
        response = {
            "verification": verification.dict() if verification else None,
            "items": items if items else [],
            "error": None
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )

@router.post("/verify-document")
async def verify_document(file: UploadFile = File(...)):
    """
    Verify if a document is a purchase order.
    
    Args:
        file (UploadFile): The document file to verify
        
    Returns:
        Dict containing:
            - verification: Verification result
            - error: Error message (if any)
    """
    try:
        # Read the file into memory
        contents = await file.read()
        document = io.BytesIO(contents)
        
        # Verify the document
        verification = document_processor.verify_document(document)
        
        # Prepare the response
        response = {
            "verification": verification.dict(),
            "error": None
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error verifying document: {str(e)}"
        )

@router.post("/compare", response_model=ComparisonResult)
async def compare_to_contract(
    contract_id: str = Form(...),
    invoice_data: ExtractedInvoice = None,
):
    """Compare processed invoice data with a specific contract"""
    try:
        result = await compare_invoice_to_contract(contract_id, invoice_data)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare invoice: {str(e)}"
        ) 