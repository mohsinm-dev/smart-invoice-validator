from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status

from app.models.invoice import ExtractedInvoice, ComparisonResult
from app.services.invoice_service import process_invoice
from app.services.comparison_service import compare_invoice_to_contract

router = APIRouter()

@router.post("/process", response_model=ExtractedInvoice)
async def upload_invoice(
    file: UploadFile = File(...),
):
    """Upload and process an invoice using OCR"""
    try:
        # Process the invoice
        extracted_data = await process_invoice(file)
        return extracted_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process invoice: {str(e)}"
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