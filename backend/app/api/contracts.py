from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Contract
from ..services.document_processor import DocumentProcessor
from pydantic import BaseModel
from datetime import datetime
import uuid
from loguru import logger
import os
from ..config import settings
import json

router = APIRouter(prefix="/contracts", tags=["contracts"])

class Service(BaseModel):
    service_name: str
    unit_price: float

class ContractCreate(BaseModel):
    supplier_name: str
    services: List[Service]

class ContractResponse(BaseModel):
    id: str
    supplier_name: str
    services: List[Service]
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
            services=[service.dict() for service in contract_data.services]
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
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process the contract file using DocumentProcessor
        processor = DocumentProcessor()
        extracted_data = processor.process_contract(content, file.filename)
        
        if "error" in extracted_data:
            logger.error(f"Error processing contract: {extracted_data['error']}")
            raise HTTPException(status_code=400, detail=extracted_data["error"])
        
        # Use the supplier name extracted by the Gemini model
        supplier_name = extracted_data.get("supplier_name", "Unknown Supplier")
        logger.info(f"Using extracted supplier name: {supplier_name}")
        
        # Use extracted services if available
        services = extracted_data.get("services", [])
        if not services:
            logger.warning("No services extracted from contract, using defaults")
            # Provide default services only if nothing was extracted
            services = [
                {"service_name": "Professional Services", "unit_price": 100.0},
                {"service_name": "Consulting", "unit_price": 150.0}
            ]
        
        # Log the extracted services for debugging
        logger.info(f"Extracted services: {json.dumps(services)}")
        
        # Create a contract in the database
        contract_id = str(uuid.uuid4())
        contract = Contract(
            id=contract_id,
            supplier_name=supplier_name,
            services=services
        )
        
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        logger.info(f"Contract uploaded and processed: {contract.id}")
        return contract
        
    except Exception as e:
        logger.error(f"Error uploading contract: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

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
        contract.services = [service.dict() for service in contract_data.services]
        contract.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(contract)
        
        return contract
    except Exception as e:
        logger.error(f"Error updating contract: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) 