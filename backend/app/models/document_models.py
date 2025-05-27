from typing import List, Optional, Any
from datetime import date, datetime
from pydantic import BaseModel, Field, validator, root_validator

class InvoiceItemModel(BaseModel):
    description: str = "Unknown Item"
    quantity: float = Field(default=1.0)
    unit_price: float = Field(default=0.0)
    total: Optional[float] = None

    @validator("quantity", "unit_price", pre=True, always=True)
    def ensure_float(cls, value):
        if value is None:
            if "quantity" in cls.__fields__ and cls.__fields__["quantity"].default == 1.0:
                 return 1.0
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            if "quantity" in cls.__fields__ and cls.__fields__["quantity"].default == 1.0:
                 return 1.0
            return 0.0

    @root_validator(pre=True)
    def fill_total_from_unit_price_and_quantity(cls, values: dict) -> dict:
        if values.get("total") is None:
            quantity = values.get("quantity")
            unit_price = values.get("unit_price")
            
            try:
                q = float(quantity) if quantity is not None else 1.0
                up = float(unit_price) if unit_price is not None else 0.0
                values["total"] = q * up
            except (ValueError, TypeError):
                values["total"] = 0.0 
        return values

class ExtractedInvoiceModel(BaseModel):
    invoice_number: str = "Unknown"
    supplier_name: str = "Unknown"
    issue_date: Optional[date] = Field(default_factory=date.today)
    due_date: Optional[date] = None
    items: List[InvoiceItemModel] = Field(default_factory=list)
    subtotal: Optional[float] = 0.0
    tax: Optional[float] = 0.0
    total: float = 0.0
    raw_text: Optional[str] = ""

    @validator("issue_date", "due_date", pre=True)
    def parse_date(cls, value):
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return None

    @validator("subtotal", "tax", "total", pre=True, always=True)
    def ensure_float_optional(cls, value):
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
            
    @root_validator(pre=True)
    def handle_missing_fields_from_gemini(cls, values: dict) -> dict:
        if "invoice_number" not in values or values["invoice_number"] is None:
            values["invoice_number"] = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if "supplier_name" not in values or values["supplier_name"] is None:
            values["supplier_name"] = "Unknown Supplier"
        if "issue_date" not in values or values["issue_date"] is None:
            values["issue_date"] = date.today().isoformat()
        
        raw_items = values.get("items")
        if not isinstance(raw_items, list):
            values["items"] = []
        else:
            processed_items = []
            for item in raw_items:
                if isinstance(item, dict):
                    item["quantity"] = item.get("quantity", 1.0)
                    item["unit_price"] = item.get("unit_price", 0.0)
                    processed_items.append(item)
            values["items"] = processed_items
            
        return values

    @root_validator(skip_on_failure=True)
    def calculate_total_from_items_if_zero(cls, values: dict) -> dict:
        current_total = values.get("total")
        if current_total is None or float(current_total) == 0.0:
            items = values.get("items", [])
            if items:
                calculated_total = sum(item.total for item in items if item.total is not None)
                if calculated_total > 0:
                     values["total"] = calculated_total
        
        if not values.get("items") and (values.get("total") is None or float(values.get("total")) == 0.0) :
             pass
        elif not values.get("items") and float(values.get("total", 0.0)) > 0.0:
            values["items"] = [
                InvoiceItemModel(
                    description="Unknown Item",
                    quantity=1.0,
                    unit_price=values.get("total"),
                    total=values.get("total")
                )
            ]
        return values

class ExtractedContractModel(BaseModel):
    supplier_name: Optional[str] = "Unknown Supplier"
    items: List[InvoiceItemModel] = Field(default_factory=list)
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    payment_terms: Optional[str] = None
    max_amount: Optional[float] = None

    @validator("supplier_name", pre=True, always=True)
    def set_default_supplier_name(cls, v):
        return v or "Unknown Supplier"

    @validator("effective_date", "expiration_date", pre=True)
    def parse_contract_date(cls, value):
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return None

    @validator("max_amount", pre=True)
    def parse_max_amount(cls, value):
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @root_validator(pre=True)
    def ensure_contract_fields(cls, values: dict) -> dict:
        if "supplier_name" not in values or values["supplier_name"] is None:
            values["supplier_name"] = "Unknown Supplier"
        
        raw_items = values.get("items")
        if not isinstance(raw_items, list):
            values["items"] = []
        else:
            processed_items = []
            for item in raw_items:
                if isinstance(item, dict):
                    item["quantity"] = item.get("quantity", 1.0)
                    item["unit_price"] = item.get("unit_price", 0.0)
                    processed_items.append(item)
            values["items"] = processed_items
        return values 

class PromptItemSchema(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total: float 