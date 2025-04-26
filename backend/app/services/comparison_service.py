import difflib

from app.models.invoice import ExtractedInvoice, ComparisonResult
from app.services.contract_service import get_contract

async def compare_invoice_to_contract(contract_id: str, invoice_data: ExtractedInvoice) -> ComparisonResult:
    """Compare invoice data with contract terms"""
    # Get the contract
    contract = await get_contract(contract_id)
    if not contract:
        raise ValueError(f"Contract with ID {contract_id} not found")
    
    # Initialize results
    matches = {
        "supplier_name": False,
        "prices_match": False,
        "all_services_in_contract": False
    }
    issues = []
    
    # Compare supplier name
    # Use fuzzy matching to account for slight differences in naming
    supplier_similarity = difflib.SequenceMatcher(None, 
                                                  contract.supplier_name.lower(), 
                                                  invoice_data.supplier_name.lower()).ratio()
    matches["supplier_name"] = supplier_similarity >= 0.8
    
    if not matches["supplier_name"]:
        issues.append({
            "type": "supplier_mismatch",
            "contract_value": contract.supplier_name,
            "invoice_value": invoice_data.supplier_name
        })
    
    # Create a dictionary of services in the contract for easy lookup
    contract_services = {item.service_name.lower(): item.unit_price for item in contract.services}
    
    # Check if all invoice items are in the contract
    all_items_in_contract = True
    price_issues = False
    
    for item in invoice_data.items:
        # Try to find matching service in contract
        best_match = None
        best_match_ratio = 0
        
        for service_name in contract_services.keys():
            ratio = difflib.SequenceMatcher(None, 
                                           service_name, 
                                           item.description.lower()).ratio()
            if ratio > best_match_ratio and ratio >= 0.7:  # Threshold for matching
                best_match = service_name
                best_match_ratio = ratio
        
        if best_match:
            # Check price
            contract_price = contract_services[best_match]
            if abs(contract_price - item.unit_price) > 0.01:  # Allow for small float differences
                price_issues = True
                issues.append({
                    "type": "price_mismatch",
                    "service_name": item.description,
                    "contract_price": contract_price,
                    "invoice_price": item.unit_price
                })
        else:
            all_items_in_contract = False
            issues.append({
                "type": "service_not_in_contract",
                "service_name": item.description
            })
    
    matches["prices_match"] = not price_issues
    matches["all_services_in_contract"] = all_items_in_contract
    
    # Overall match determination
    overall_match = all(matches.values())
    
    return ComparisonResult(
        contract_id=contract_id,
        invoice_data=invoice_data,
        matches=matches,
        issues=issues,
        overall_match=overall_match
    )