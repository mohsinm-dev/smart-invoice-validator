from typing import List, Optional, Any
from datetime import date, datetime
from pydantic import BaseModel, Field, validator, root_validator

class InvoiceItemModel(BaseModel):
    description: str = "Unknown Item"
    quantity: float = Field(default=1.0)
    unit_price: float = Field(default=0.0)
    total_price: Optional[float] = None

    @validator("quantity", "unit_price", pre=True, always=True)
    def ensure_float(cls, value):
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    @root_validator(pre=True)
    def fill_total_price_from_unit_price_and_quantity(cls, values: dict) -> dict:
        # This validator is for data coming from Gemini where total_price might be missing.
        # It runs before Pydantic's own validation.
        if values.get("total_price") is None:
            quantity = values.get("quantity", 1.0)
            unit_price = values.get("unit_price", 0.0)
            try:
                q = float(quantity) if quantity is not None else 1.0
                up = float(unit_price) if unit_price is not None else 0.0
                values["total_price"] = q * up
            except (ValueError, TypeError):
                values["total_price"] = 0.0
        return values

    @root_validator(skip_on_failure=True) # Runs after individual field validation
    def calculate_total_price_if_still_none(cls, values: dict) -> dict:
        # This validator runs after Pydantic's own validation
        # and ensures total_price is calculated if it wasn't provided or calculable before.
        if values.get("total_price") is None:
            quantity = values.get("quantity", 1.0) # Will be float due to previous validator
            unit_price = values.get("unit_price", 0.0) # Will be float due to previous validator
            values["total_price"] = quantity * unit_price
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
            values["issue_date"] = date.today().isoformat() # Keep as string for date validator
        
        # Ensure items is a list
        if "items" not in values or not isinstance(values.get("items"), list):
            values["items"] = []
            
        return values

    @root_validator(skip_on_failure=True)
    def calculate_total_from_items_if_zero(cls, values: dict) -> dict:
        # If total is 0 or None, try to sum item totals.
        current_total = values.get("total")
        if current_total is None or float(current_total) == 0.0:
            items = values.get("items", [])
            if items:
                calculated_total = sum(item.total_price for item in items if item.total_price is not None)
                if calculated_total > 0:
                     values["total"] = calculated_total
        
        # If items is empty and total is still 0, create a default item
        if not values.get("items") and (values.get("total") is None or float(values.get("total")) == 0.0) :
             # This case is tricky: if total is 0 and no items, we can't infer much.
             # The prompt for Gemini asks for a total. If it's 0, and no items, this is what we get.
             # We could create a default item, but its price would be 0.
             # For now, let it be an empty list of items if total is 0.
             pass
        elif not values.get("items") and float(values.get("total", 0.0)) > 0.0:
            values["items"] = [
                InvoiceItemModel(
                    description="Unknown Item",
                    quantity=1.0,
                    unit_price=values.get("total"), # This will be float due to validator
                    total_price=values.get("total")
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
        # This is tricky if filename is needed. For now, just default.
        # The logic to derive from filename was in the old processor.
        # If the model consuming this needs the filename, it should be passed.
        return v or "Unknown Supplier"

    @validator("effective_date", "expiration_date", pre=True)
    def parse_contract_date(cls, value):
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None # Allow null if parsing fails
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
    def ensure_items_is_list(cls, values: dict) -> dict:
        if "items" not in values or not isinstance(values.get("items"), list):
            values["items"] = []
        return values 