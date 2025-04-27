from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Invoice, Contract
from ..services.document_processor import DocumentProcessor
from pydantic import BaseModel
from datetime import datetime
import uuid
import os
from ..config import settings
from loguru import logger
import base64

router = APIRouter(prefix="/invoices", tags=["invoices"])

class InvoiceItem(BaseModel):
    file_content: str  # Base64 encoded file content
    file_type: str  # File extension (pdf, jpg, jpeg, png, doc, docx)
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    total_price: float | None = None

class InvoiceData(BaseModel):
    invoice_number: str
    supplier_name: str
    issue_date: datetime
    due_date: datetime | None = None
    items: List[dict]  # Modified to be a list of dictionaries with description, quantity, etc.
    subtotal: float | None = None
    tax: float | None = None
    total: float
    raw_text: str | None = None

class ComparisonResult(BaseModel):
    contract_id: str
    invoice_data: InvoiceData
    matches: dict
    issues: List[dict]
    overall_match: bool

@router.post("/process")
async def process_invoice(
    invoice_item: InvoiceItem,
    db: Session = Depends(get_db)
):
    """Process an invoice from encoded file content.
    
    Example request body:
    ```json
    {
        "file_content": "base64_encoded_file_content",
        "file_type": "pdf"
    }
    ```
    
    The file_content should be the base64 encoded file content without the data URL prefix.
    The file_type should be one of: pdf, jpg, jpeg, png, doc, docx
    """
    try:
        # Validate input
        if not invoice_item.file_content:
            raise HTTPException(status_code=400, detail="File content is required")
        
        if not invoice_item.file_type:
            raise HTTPException(status_code=400, detail="File type is required")
            
        # Process invoice with file content
        try:
            file_content = base64.b64decode(invoice_item.file_content)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 encoded file content")
        
        # Process invoice to extract data using the DocumentProcessor
        processor = DocumentProcessor()
        invoice_data = await processor.process_invoice_async(file_content, invoice_item.file_type)
        
        return invoice_data
        
    except ValueError as e:
        logger.error(f"Validation error in process_invoice: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing invoice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compare", response_model=ComparisonResult)
async def compare_invoice(
    request: dict,
    db: Session = Depends(get_db)
):
    """Compare an invoice against a contract.
    
    Example request body:
    ```json
    {
        "contract_id": "contract-id-here",
        "invoice_data": {
            "invoice_number": "123",
            "supplier_name": "Supplier Name",
            "issue_date": "2023-01-01T00:00:00",
            "items": [...],
            "total": 100.0,
            ...
        }
    }
    ```
    """
    try:
        # Extract data from request body
        if not request.get("contract_id"):
            raise HTTPException(status_code=400, detail="Contract ID is required")
            
        if not request.get("invoice_data"):
            raise HTTPException(status_code=400, detail="Invoice data is required")
            
        contract_id = request.get("contract_id")
        invoice_data = request.get("invoice_data")
        
        # Get contract
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        # Compare invoice with contract using processor instance
        processor = DocumentProcessor()
        comparison_result = await processor.compare_invoice_with_contract(
            contract=contract,
            invoice_data=invoice_data
        )
        
        return ComparisonResult(**comparison_result)
        
    except Exception as e:
        logger.error(f"Error comparing invoice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=dict)
async def create_invoice(
    contract_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Create a new invoice for a specific contract."""
    try:
        # Verify contract exists
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        # Save file
        file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Create invoice record
        invoice = Invoice(
            contract_id=contract_id,
            file_path=file_path,
            content=None,  # Will be populated by document processor
            is_valid=False,
            validation_result=None
        )
        
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        return {
            "id": invoice.id,
            "contract_id": invoice.contract_id,
            "file_path": invoice.file_path,
            "is_valid": invoice.is_valid,
            "created_at": invoice.created_at
        }
        
    except Exception as e:
        logger.error(f"Error creating invoice: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[dict])
async def get_invoices(db: Session = Depends(get_db)):
    """Get all invoices."""
    invoices = db.query(Invoice).all()
    return [
        {
            "id": invoice.id,
            "contract_id": invoice.contract_id,
            "file_path": invoice.file_path,
            "is_valid": invoice.is_valid,
            "created_at": invoice.created_at
        }
        for invoice in invoices
    ]

@router.get("/{invoice_id}", response_model=dict)
async def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Get a specific invoice by ID."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return {
        "id": invoice.id,
        "contract_id": invoice.contract_id,
        "file_path": invoice.file_path,
        "content": invoice.content,
        "is_valid": invoice.is_valid,
        "validation_result": invoice.validation_result,
        "created_at": invoice.created_at,
        "updated_at": invoice.updated_at
    }

@router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Delete an invoice by ID."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    try:
        # Delete file
        if os.path.exists(invoice.file_path):
            os.remove(invoice.file_path)
        
        # Delete database record
        db.delete(invoice)
        db.commit()
        
        return {"message": "Invoice deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting invoice: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/process-example")
async def process_invoice_example():
    """
    Example endpoint demonstrating how to process an invoice with base64 encoding.
    
    This endpoint doesn't actually process an invoice - it just shows the expected request format.
    
    Example usage with curl:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/invoices/process-example" -H "Content-Type: application/json" -d '{"file_content": "base64_content_here", "file_type": "pdf"}'
    ```
    
    Response will show the expected format of the request body.
    """
    return {
        "expected_request_format": {
            "file_content": "base64_encoded_file_content",
            "file_type": "pdf"
        },
        "note": "For actual processing, send this format to the /process endpoint"
    }

@router.post("/compare-example")
async def compare_invoice_example():
    """
    Example endpoint demonstrating how to compare an invoice with a contract.
    
    This endpoint doesn't actually perform a comparison - it just shows the expected request format.
    
    Example usage with curl:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/invoices/compare-example" -H "Content-Type: application/json"
    ```
    
    Response will show the expected format of the request body.
    """
    return {
        "expected_request_format": {
            "contract_id": "contract-id-here",
            "invoice_data": {
                "invoice_number": "123456",
                "supplier_name": "Supplier Name",
                "issue_date": "2023-01-01T00:00:00",
                "due_date": "2023-02-01T00:00:00",
                "items": [
                    {
                        "description": "Service description",
                        "quantity": 1,
                        "unit_price": 100.0,
                        "total_price": 100.0
                    }
                ],
                "subtotal": 100.0,
                "tax": 20.0,
                "total": 120.0,
                "raw_text": "Sample invoice content"
            }
        },
        "note": "For actual comparison, send this format to the /compare endpoint"
    } 