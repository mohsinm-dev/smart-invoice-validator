from fastapi import APIRouter, HTTPException, status
from typing import List
import uuid

from app.models.contract import Contract
from app.services.contract_service import save_contract, get_contract, get_all_contracts

router = APIRouter()

@router.post("/", response_model=Contract, status_code=status.HTTP_201_CREATED)
async def create_contract(contract: Contract):
    """Create a new contract"""
    if not contract.id:
        contract.id = str(uuid.uuid4())
    
    result = await save_contract(contract)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save contract"
        )
    return contract

@router.get("/", response_model=List[Contract])
async def list_contracts():
    """Get all contracts"""
    return await get_all_contracts()

@router.get("/{contract_id}", response_model=Contract)
async def get_contract_by_id(contract_id: str):
    """Get a specific contract by ID"""
    contract = await get_contract(contract_id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with ID {contract_id} not found"
        )
    return contract