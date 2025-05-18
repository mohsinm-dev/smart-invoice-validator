from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import Contract
from ..services.document_processor import DocumentProcessor
from ..models.document_models import InvoiceItemModel
from pydantic import BaseModel
from datetime import datetime
import uuid
from loguru import logger
import os
from ..config import settings
import json

router = APIRouter(prefix="/contracts", tags=["contracts"])

class ItemResponse(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total_price: Optional[float] = None

class ContractCreate(BaseModel):
    supplier_name: str
    items: List[ItemResponse]

class ContractResponse(BaseModel):
    id: str
    supplier_name: str
    items: List[ItemResponse]
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True

@router.get("/", response_model=List[ContractResponse])
async def get_contracts(db: Session = Depends(get_db)):
    """Get all contracts."""
    try:
        contracts = db.query(Contract).all()
        logger.info(f"Retrieved {len(contracts)} contracts from database")
        return contracts
    except Exception as e:
        logger.error(f"Error retrieving contracts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve contracts")

@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(contract_id: str, db: Session = Depends(get_db)):
    """Get a specific contract by ID."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract

@router.post("/", response_model=ContractResponse, status_code=201)
async def create_contract(
    contract_data: ContractCreate,
    db: Session = Depends(get_db)
):
    """Create a new contract."""
    try:
        contract = Contract(
            id=str(uuid.uuid4()),
            supplier_name=contract_data.supplier_name,
            items=[item.dict() for item in contract_data.items]
        )
        
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        return contract
        
    except Exception as e:
        logger.error(f"Error creating contract: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/upload", response_model=ContractResponse, status_code=201)
async def upload_contract(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a contract file and process it."""
    try:
        # Save the file
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        
        file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Process the contract file using DocumentProcessor
        processor = DocumentProcessor()
        extracted_data_model = processor.process_contract(content, file.filename)
        
        if extracted_data_model is None:
            logger.error(f"Error processing contract: Failed to extract data for {file.filename}")
            raise HTTPException(status_code=400, detail="Failed to process contract file and extract data.")
        
        # Use the supplier name extracted by the model
        supplier_name = extracted_data_model.supplier_name or "Unknown Supplier"
        logger.info(f"Using extracted supplier name: {supplier_name}")
        
        # Use extracted items (List[InvoiceItemModel])
        extracted_items = extracted_data_model.items
        
        # Convert List[InvoiceItemModel] to List[dict] for DB storage / response model
        items_for_db = [item.model_dump() for item in extracted_items]

        if not items_for_db:
            logger.warning(f"No items extracted from contract {file.filename}, using defaults if applicable or empty list")
            # Default items logic might need review based on requirements.
            # For now, if no items, it will be an empty list.
            # items_for_db = [
            #     ItemResponse(description="Default Service", quantity=1.0, unit_price=0.0, total_price=0.0).model_dump()
            # ]

        # Log the extracted items for debugging
        logger.info(f"Extracted items: {json.dumps(items_for_db)}")
        
        # Create a contract in the database
        contract_id_val = str(uuid.uuid4())
        db_contract = Contract(
            id=contract_id_val,
            supplier_name=supplier_name,
            items=items_for_db
        )
        
        db.add(db_contract)
        db.commit()
        db.refresh(db_contract)
        
        logger.info(f"Contract uploaded and processed: {db_contract.id}")
        return db_contract
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error uploading contract: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error during contract upload: {str(e)}")

@router.delete("/{contract_id}")
async def delete_contract(contract_id: str, db: Session = Depends(get_db)):
    """Delete a contract by ID."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    try:
        db.delete(contract)
        db.commit()
        return {"message": "Contract deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting contract: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: str,
    contract_data: ContractCreate,
    db: Session = Depends(get_db)
):
    """Update an existing contract."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    try:
        contract.supplier_name = contract_data.supplier_name
        contract.items = [item.dict() for item in contract_data.items]
        contract.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(contract)
        
        return contract
    except Exception as e:
        logger.error(f"Error updating contract: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) 