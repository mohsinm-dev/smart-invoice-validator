from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
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
    total: float | None = None

class InvoiceData(BaseModel):
    id: str
    contract_id: Optional[str] = None
    supplier_name: str
    items: List[dict]
    document_path: Optional[str] = None
    is_valid: Optional[bool] = None
    validation_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

@router.post("/process")
async def process_invoice(
    invoice_item: InvoiceItem,
    db: Session = Depends(get_db)
):
    """Process an invoice from encoded file content."""
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
        stitched_content_bytes = processor.stitch_document(file_content, invoice_item.file_type)
        
        if stitched_content_bytes is None:
            logger.error(f"Failed to stitch document for file type: {invoice_item.file_type}")
            raise HTTPException(status_code=500, detail=f"Failed to process document: Could not convert or stitch file type '{invoice_item.file_type}'")

        # Now, process the stitched PNG image content
        # The file_type for process_invoice_async should now be 'png'
        extracted_invoice_model = await processor.process_invoice_async(stitched_content_bytes, 'png', skip_type_check=True)
        
        if extracted_invoice_model is None:
            logger.error(f"Processing the stitched PNG image returned no data.")
            raise HTTPException(status_code=500, detail="Failed to extract data from the processed document.")
        
        try:
            items_for_db = [item.model_dump() for item in extracted_invoice_model.items]

            db_invoice = Invoice(
                id=str(uuid.uuid4()),
                supplier_name=extracted_invoice_model.supplier_name,
                items=items_for_db,
                document_path=None,
                is_valid=False,
                validation_message=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(db_invoice)
            db.commit()
            db.refresh(db_invoice)
            logger.info(f"Processed invoice data saved to DB with ID: {db_invoice.id}")
            
            return InvoiceData(
                id=db_invoice.id,
                contract_id=db_invoice.contract_id,
                supplier_name=db_invoice.supplier_name,
                items=db_invoice.items,
                document_path=db_invoice.document_path,
                is_valid=db_invoice.is_valid,
                validation_message=db_invoice.validation_message,
                created_at=db_invoice.created_at,
                updated_at=db_invoice.updated_at
            )
            
        except Exception as db_error:
            logger.error(f"Error saving processed invoice to database: {db_error}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to save processed invoice data.")
        
    except ValueError as e:
        logger.error(f"Validation error in process_invoice: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing invoice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=dict)
async def create_invoice(
    contract_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Create a new invoice for a specific contract."""
    try:
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        invoice = Invoice(
            contract_id=contract_id,
            document_path=file_path,
            items=[],
            is_valid=False,
            validation_message=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        return {
            "id": invoice.id,
            "contract_id": invoice.contract_id,
            "document_path": invoice.document_path,
            "is_valid": invoice.is_valid,
            "created_at": invoice.created_at,
            "updated_at": invoice.updated_at
        }
        
    except Exception as e:
        logger.error(f"Error creating invoice: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[InvoiceData])
async def get_invoices(db: Session = Depends(get_db)):
    """Get all invoices with their processed data."""
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).all()
    
    results = []
    for invoice in invoices:
        results.append(
            InvoiceData(
                id=invoice.id,
                contract_id=invoice.contract_id,
                supplier_name=invoice.supplier_name,
                items=invoice.items,
                document_path=invoice.document_path,
                is_valid=invoice.is_valid,
                validation_message=invoice.validation_message,
                created_at=invoice.created_at,
                updated_at=invoice.updated_at
            )
        )
    return results

@router.get("/{invoice_id}", response_model=InvoiceData)
async def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    """Get a specific invoice by ID."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return InvoiceData(
        id=invoice.id,
        contract_id=invoice.contract_id,
        supplier_name=invoice.supplier_name,
        items=invoice.items,
        document_path=invoice.document_path,
        is_valid=invoice.is_valid,
        validation_message=invoice.validation_message,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at
    )

@router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: str, db: Session = Depends(get_db)):
    """Delete an invoice by ID."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    try:
        if invoice.document_path and os.path.exists(invoice.document_path):
            os.remove(invoice.document_path)
            logger.info(f"Deleted associated file: {invoice.document_path} for invoice ID: {invoice_id}")
        elif invoice.document_path:
            logger.warning(f"File path {invoice.document_path} for invoice ID: {invoice_id} was set but file not found.")
        else:
            logger.info(f"No file path associated with invoice ID: {invoice_id}. No file to delete.")
        
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
    """
    return {
        "expected_request_format": {
            "file_content": "base64_encoded_file_content",
            "file_type": "pdf"
        },
        "note": "For actual processing, send this format to the /process endpoint"
    } 