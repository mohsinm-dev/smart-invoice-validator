from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

class ServiceItem(BaseModel):
    service_name: str
    unit_price: float
    
class Contract(BaseModel):
    id: Optional[str] = None
    supplier_name: str
    services: List[ServiceItem]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "supplier_name": "ABC Corp",
                "services": [
                    {"service_name": "Consulting", "unit_price": 100.0},
                    {"service_name": "Development", "unit_price": 85.0}
                ]
            }
        }