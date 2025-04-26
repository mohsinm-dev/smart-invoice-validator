from datetime import date
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class InvoiceItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total_price: Optional[float] = None

class ExtractedInvoice(BaseModel):
    invoice_number: str
    supplier_name: str
    issue_date: date
    due_date: Optional[date] = None
    items: List[InvoiceItem]
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: float
    raw_text: Optional[str] = None
    
class ComparisonResult(BaseModel):
    contract_id: str
    invoice_data: ExtractedInvoice
    matches: Dict[str, bool]
    issues: List[Dict[str, Any]]
    overall_match: bool