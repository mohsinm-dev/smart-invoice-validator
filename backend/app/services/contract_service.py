import json
import os
from datetime import datetime
from typing import List, Optional

from app.config import CONTRACTS_DIR
from app.models.contract import Contract

async def save_contract(contract: Contract) -> bool:
    """Save contract to file system"""
    try:
        # Update the timestamps
        contract.updated_at = datetime.utcnow()
        
        # Convert contract to dictionary
        contract_dict = contract.model_dump()
        
        # Save to file
        file_path = CONTRACTS_DIR / f"{contract.id}.json"
        with open(file_path, "w") as f:
            json.dump(contract_dict, f, default=str)
        
        return True
    except Exception as e:
        print(f"Error saving contract: {e}")
        return False

async def get_contract(contract_id: str) -> Optional[Contract]:
    """Get contract by ID"""
    try:
        file_path = CONTRACTS_DIR / f"{contract_id}.json"
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, "r") as f:
            contract_data = json.load(f)
        
        return Contract(**contract_data)
    except Exception as e:
        print(f"Error retrieving contract: {e}")
        return None

async def get_all_contracts() -> List[Contract]:
    """Get all contracts"""
    contracts = []
    
    try:
        for filename in os.listdir(CONTRACTS_DIR):
            if filename.endswith(".json"):
                file_path = CONTRACTS_DIR / filename
                with open(file_path, "r") as f:
                    contract_data = json.load(f)
                contracts.append(Contract(**contract_data))
    except Exception as e:
        print(f"Error retrieving contracts: {e}")
    
    return contracts