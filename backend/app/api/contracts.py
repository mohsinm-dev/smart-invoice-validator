from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Contract
from pydantic import BaseModel
from datetime import datetime
import uuid
from loguru import logger

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
    contracts = db.query(Contract).all()
    return contracts

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