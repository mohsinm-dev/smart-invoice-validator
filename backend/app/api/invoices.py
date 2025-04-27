from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Invoice, Contract
from ..services.document_processor import DocumentProcessor
from pydantic import BaseModel
from datetime import datetime
import uuid
from loguru import logger

router = APIRouter(prefix="/invoices", tags=["invoices"])

class InvoiceItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total_price: float | None = None

class InvoiceData(BaseModel):
    invoice_number: str
    supplier_name: str
    issue_date: datetime
    due_date: datetime | None = None
    items: List[InvoiceItem]
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

@router.post("/process", response_model=InvoiceData)
async def process_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Process an invoice file and extract data."""
    try:
        # Read file content
        content = await file.read()
        file_type = file.filename.split('.')[-1].lower()
        
        # Process invoice using document processor
        extracted_data = await DocumentProcessor.process_invoice(content, file_type)
        
        # Convert to InvoiceData model
        invoice_data = InvoiceData(
            invoice_number=extracted_data["invoice_number"],
            supplier_name=extracted_data["supplier_name"],
            issue_date=extracted_data["issue_date"],
            due_date=extracted_data.get("due_date"),
            items=[
                InvoiceItem(
                    description=item["description"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    total_price=item.get("total_price")
                )
                for item in extracted_data["items"]
            ],
            subtotal=extracted_data.get("subtotal"),
            tax=extracted_data.get("tax"),
            total=extracted_data["total"],
            raw_text=extracted_data.get("raw_text")
        )
        
        return invoice_data
        
    except Exception as e:
        logger.error(f"Error processing invoice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compare", response_model=ComparisonResult)
async def compare_invoice(
    contract_id: str,
    invoice_data: InvoiceData,
    db: Session = Depends(get_db)
):
    """Compare an invoice against a contract."""
    try:
        # Get contract
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        # Compare invoice with contract
        comparison_result = await DocumentProcessor.compare_invoice_with_contract(
            contract=contract,
            invoice_data=invoice_data.dict()
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