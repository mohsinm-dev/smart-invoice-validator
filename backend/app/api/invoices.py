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
    total_price: float | None = None

class InvoiceData(BaseModel):
    id: str
    invoice_number: str
    supplier_name: str
    issue_date: datetime
    due_date: Optional[datetime] = None
    items: List[dict]  # Modified to be a list of dictionaries with description, quantity, etc.
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: float
    created_at: datetime

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
        stitched_content_bytes = processor.stitch_document(file_content, invoice_item.file_type)
        
        if stitched_content_bytes is None:
            # Stitching failed, possibly due to unsupported file type or internal error
            logger.error(f"Failed to stitch document for file type: {invoice_item.file_type}")
            raise HTTPException(status_code=500, detail=f"Failed to process document: Could not convert or stitch file type '{invoice_item.file_type}'")

        # Now, process the stitched PNG image content
        # The file_type for process_invoice_async should now be 'png'
        extracted_invoice_model = await processor.process_invoice_async(stitched_content_bytes, 'png')
        
        if extracted_invoice_model is None:
            # This might happen if process_invoice_async itself fails or returns None
            logger.error(f"Processing the stitched PNG image returned no data.")
            raise HTTPException(status_code=500, detail="Failed to extract data from the processed document.")
        
        # Save the processed invoice data to the database
        try:
            # Ensure items are in a JSON-serializable format (list of dicts)
            items_for_db = [item.model_dump() for item in extracted_invoice_model.items]

            db_invoice = Invoice(
                id=str(uuid.uuid4()), # Generate a new UUID for the invoice
                invoice_number=extracted_invoice_model.invoice_number,
                supplier_name=extracted_invoice_model.supplier_name,
                issue_date=extracted_invoice_model.issue_date,
                due_date=extracted_invoice_model.due_date,
                items=items_for_db, # Store as JSON
                subtotal=extracted_invoice_model.subtotal,
                tax=extracted_invoice_model.tax,
                total=extracted_invoice_model.total,
                # raw_text=extracted_invoice_model.raw_text, # Temporarily removed if DB schema doesn't have it
                # contract_id can be associated later if needed, or passed in request
            )
            db.add(db_invoice)
            db.commit()
            db.refresh(db_invoice)
            logger.info(f"Processed invoice data saved to DB with ID: {db_invoice.id}")
            
            # Return the Pydantic model of the extracted data, not the DB model directly for consistency
            # or a new Pydantic model that represents a saved invoice.
            # For now, returning the extracted_invoice_model which matches InvoiceData definition partially.
            return extracted_invoice_model 
            
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

@router.get("/", response_model=List[InvoiceData])
async def get_invoices(db: Session = Depends(get_db)):
    """Get all invoices with their processed data."""
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).all()
    
    results = []
    for invoice in invoices:
        results.append(
            InvoiceData(
                id=invoice.id,
                invoice_number=invoice.invoice_number,
                supplier_name=invoice.supplier_name,
                issue_date=invoice.issue_date,
                due_date=invoice.due_date,
                items=invoice.items,
                subtotal=invoice.subtotal,
                tax=invoice.tax,
                total=invoice.total,
                created_at=invoice.created_at
            )
        )
    return results

@router.get("/{invoice_id}", response_model=InvoiceData)
async def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    """Get a specific invoice by ID."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Map SQLAlchemy model to Pydantic model
    return InvoiceData(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        supplier_name=invoice.supplier_name,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        items=invoice.items,
        subtotal=invoice.subtotal,
        tax=invoice.tax,
        total=invoice.total,
        created_at=invoice.created_at
    )

@router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: str, db: Session = Depends(get_db)):
    """Delete an invoice by ID."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    try:
        # Delete file only if file_path exists and the file is present
        if invoice.file_path and os.path.exists(invoice.file_path):
            os.remove(invoice.file_path)
            logger.info(f"Deleted associated file: {invoice.file_path} for invoice ID: {invoice_id}")
        elif invoice.file_path:
            logger.warning(f"File path {invoice.file_path} for invoice ID: {invoice_id} was set but file not found.")
        else:
            logger.info(f"No file path associated with invoice ID: {invoice_id}. No file to delete.")
        
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