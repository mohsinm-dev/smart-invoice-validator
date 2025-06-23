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
    total: float

class ContractCreate(BaseModel):
    supplier_name: str
    items: List[ItemResponse]
    document_path: Optional[str] = None
    is_manual: Optional[bool] = False

class ContractResponse(BaseModel):
    id: str
    supplier_name: str
    items: List[ItemResponse]
    document_path: Optional[str] = None
    is_manual: Optional[bool] = False
    created_at: datetime
    updated_at: datetime

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
        # Convert Pydantic items to dict for JSON storage
        items_for_db = [item.model_dump() for item in contract_data.items]

        contract = Contract(
            id=str(uuid.uuid4()),
            supplier_name=contract_data.supplier_name,
            items=items_for_db, # Store as list of dicts
            document_path=contract_data.document_path,
            is_manual=contract_data.is_manual,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
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
        # Normalize file extension check (remove dot, lowercase)
        original_file_name = file.filename
        file_ext_from_upload = os.path.splitext(original_file_name)[1].lower().lstrip('.')
        
        # Use settings.ALLOWED_EXTENSIONS which should be a list of strings without dots
        # Example: ALLOWED_EXTENSIONS = ['pdf', 'png', 'jpg', 'jpeg'] in config.py
        if file_ext_from_upload not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"File type '{file_ext_from_upload}' not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        
        file_path = os.path.join(settings.UPLOAD_DIR, original_file_name)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        processor = DocumentProcessor()
        # Pass original_file_name for DocumentProcessor to derive extension again, or pass normalized file_ext_from_upload
        # DocumentProcessor internally normalizes from filename, so original_file_name is fine.
        extracted_data_model = processor.process_contract(content, original_file_name)
        
        if extracted_data_model is None:
            logger.error(f"Error processing contract: Failed to extract data for {original_file_name}")
            # This detail should reflect the error from DocumentProcessor if possible, 
            # or a generic one if DocumentProcessor returned None without specific error.
            raise HTTPException(status_code=400, detail=f"Failed to process contract file '{original_file_name}'. Document processing returned no data. Check logs for details.")
        
        supplier_name = extracted_data_model.supplier_name or "Unknown Supplier"
        logger.info(f"Using extracted supplier name: {supplier_name}")
        
        extracted_items = extracted_data_model.items
        # Convert List[InvoiceItemModel from Pydantic model] to List[dict for DB]
        items_for_db = [item.model_dump() for item in extracted_items]

        if not items_for_db:
            logger.warning(f"No items extracted from contract {original_file_name}, using empty list")
        
        logger.info(f"Extracted items for DB: {json.dumps(items_for_db)}")
        
        contract_id_val = str(uuid.uuid4())
        db_contract = Contract(
            id=contract_id_val,
            supplier_name=supplier_name,
            items=items_for_db,
            document_path=file_path, # Save the path where the file is stored
            is_manual=False, # This contract is from an upload
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(db_contract)
        db.commit()
        db.refresh(db_contract)
        
        logger.info(f"Contract uploaded and processed: {db_contract.id}")
        return db_contract
        
    except HTTPException as http_exc:
        # Re-raise HTTPException to ensure FastAPI handles it correctly
        raise http_exc
    except Exception as e:
        logger.error(f"Error uploading contract '{file.filename if file else 'nofile'}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error during contract upload: {str(e)}")

@router.delete("/{contract_id}")
async def delete_contract(contract_id: str, db: Session = Depends(get_db)):
    """Delete a contract by ID."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    try:
        # Optionally, delete the associated file if it exists
        if contract.document_path and os.path.exists(contract.document_path):
            try:
                os.remove(contract.document_path)
                logger.info(f"Deleted contract file: {contract.document_path}")
            except Exception as e_file_delete:
                logger.error(f"Error deleting contract file {contract.document_path}: {e_file_delete}")
                # Decide if this should prevent contract deletion or just log

        db.delete(contract)
        db.commit()
        return {"message": "Contract deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting contract ID {contract_id}: {str(e)}")
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
        contract.items = [item.model_dump() for item in contract_data.items] # Ensure items are dicts for JSON
        contract.document_path = contract_data.document_path # Allow updating path
        contract.is_manual = contract_data.is_manual # Allow updating manual flag
        contract.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(contract)
        
        return contract
    except Exception as e:
        logger.error(f"Error updating contract {contract_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) 