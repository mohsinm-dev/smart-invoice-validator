"""
Constants used in the document processing service.
"""

# Prompt for extracting general invoice data from an image
EXTRACT_INVOICE_DATA_PROMPT = """
Extract all relevant invoice information from this document. Include invoice number, issue date, due_date, supplier name, line items (with description, quantity, unit price, and total price), subtotal, tax, and total amount. Format as a JSON object.
"""

# Prompt for extracting contract data from an image
EXTRACT_CONTRACT_DATA_PROMPT = """
Analyze this contract document image in extreme detail and extract the following information.

CRITICAL: Pay special attention to all services/line items and their prices!

Please provide your response as a SINGLE, VALID JSON OBJECT. The object MUST follow this structure:
{
    "supplier_name": "The full name of the supplier or vendor (company name). String or null.",
    "services": [
        // This MUST be a JSON array of service objects. It must start with '[' and end with ']'.
        // Do NOT include a trailing comma after the last service object in this array.
        {
            "service_name": "Complete name of the service or product as written. String.",
            "quantity": "Numerical quantity. Default to 1.0 if not specified. Number.",
            "unit_price": "Numerical price value. Extract actual price, never 0 unless explicitly 0. Number."
        },
        // ... more services if present, otherwise an empty array []
    ],
    "effective_date": "YYYY-MM-DD string or null if not present.",
    "expiration_date": "YYYY-MM-DD string or null if not present.",
    "payment_terms": "Description of payment terms. String or null.",
    "max_amount": "Numerical value of maximum contract amount. Number or null."
}

DETAILED EXTRACTION INSTRUCTIONS FOR EACH FIELD:
1.  **supplier_name**: Extract the full legal name of the supplier or vendor.
2.  **services**: 
    a.  This field MUST be a valid JSON array. If no services are found, use an empty array: [].
    b.  For each service/item found:
        i.  **service_name**: Extract the complete name/description exactly as written.
        ii. **quantity**: Extract the numerical quantity. If not specified or not applicable (e.g., for a general service agreement), use 1.0.
        iii.**unit_price**: Extract the actual numerical price. NEVER default to 0 unless the document explicitly states the price is zero. Parse numbers like "1,234.56" or "1 234,56" as 1234.56.
    c.  Ensure the services array is correctly formatted (starts with '[', ends with ']', no trailing commas).
3.  **effective_date**: Find the contract start or effective date. Format as YYYY-MM-DD. If not found, use null.
4.  **expiration_date**: Find the contract end or expiration date. Format as YYYY-MM-DD. If not found, use null.
5.  **payment_terms**: Describe any payment terms mentioned (e.g., "Net 30 days"). If none, use null.
6.  **max_amount**: If a total contract value or maximum liability amount is specified, extract it as a numerical value. If not, use null.

GENERAL INSTRUCTIONS:
-   Find ALL services/items with associated pricing, even if not in a clear "price list" format.
-   If service names include numbers or codes (e.g., "ÅTA nr 6"), extract the full text as service_name.
-   Extract negative price values with a negative sign (e.g., -1000).
-   If you cannot find a specific field, use null (for string/number fields) or an empty array [] (for the services list) as appropriate according to the schema above.
-   The entire response MUST be a single JSON object. Do not include any text outside of this JSON object.
"""

# Prompt for extracting services and pricing from an image (typically for additional contract pages)
EXTRACT_SERVICES_PROMPT = """
Examine this contract page in detail and extract ONLY the services or products with their pricing.

CRITICAL: Find ALL services/line items and their associated prices!

YOUR RESPONSE MUST BE A SINGLE, VALID JSON ARRAY.
The array must start with '[' and end with ']'.
Each element in the array must be a JSON object.
Do NOT include a trailing comma after the last object in the array.

Example of the required format:
[
    {
        "service_name": "Complete description of the service exactly as written",
        "unit_price": "numerical price value (never use 0 unless explicitly stated as 0)"
    },
    {
        "service_name": "Another Service Example",
        "unit_price": "123.45"
    }
]

IMPORTANT INSTRUCTIONS:
1. Extract ALL items that appear to be services, work items, products, or deliverables.
2. Always include the FULL description of each service (don't abbreviate or summarize).
3. For each service, extract the associated price value. NEVER default to 0 unless the price is explicitly stated as 0 in the document.
4. If quantity is clearly specified for a service, include it as "quantity": numerical_value. If not specified or not applicable, you can omit it or use 1.0.
5. Include item numbers/references as part of the service name (e.g., "Item 1.2: Advanced Support").
6. Look for prices in any format: "$1000", "1,000.00", "1000 kr", "1 000,00 EUR", etc. Ensure the extracted value is purely numerical (e.g., "1000.00" or "1000").
7. Don't skip any services – capture everything that has an associated price.
8. If a price appears negative (with a minus sign or parentheses), capture it as a negative numerical value.

If no services or pricing information is found, return an empty JSON array: [].
"""

# Unified prompt for item extraction
UNIFIED_DOCUMENT_ITEM_EXTRACTION_PROMPT = """
Analyze this document page in detail and extract all line items, services, or products.
For each item, provide:
- description: The full description of the item or service.
- quantity: The quantity of the item. Default to 1.0 if not specified or not applicable (e.g., for a contracted service).
- unit_price: The price per unit of the item or service. Extract the actual price; never use 0 unless explicitly stated as 0 in the document.
- total_price: The total price for the item (quantity * unit_price). If not directly stated, it can be calculated.

CRITICAL INSTRUCTIONS:
1. Find ALL items/services, even if not in a clear list format.
2. Extract the complete name/description exactly as written.
3. ALWAYS extract the actual price value. Look for prices in formats like "$1000", "1,000.00", "1000 kr", etc.
4. If a service appears to have multiple sub-items, try to split them if they have individual pricing.
5. For contract-like documents, if a main project description has a total amount, use that as unit_price and set quantity to 1.
6. Ensure all monetary values are captured correctly.

Return a JSON array of objects, where each object represents an item.
Example:
[
    {
        "description": "Consulting Services Rendered",
        "quantity": 1.0,
        "unit_price": 5000.00,
        "total_price": 5000.00
    },
    {
        "description": "Product A - Widget",
        "quantity": 10.0,
        "unit_price": 25.50,
        "total_price": 255.00
    }
]

If no items or pricing information is found, return an empty array.
"""

# Prompt for processing an invoice image (detailed)
PROCESS_INVOICE_PROMPT = """
Analyze this document image in extreme detail and extract invoice information in JSON format.

IMPORTANT: Pay special attention to all line items or services with their quantities and prices!

YOUR RESPONSE MUST BE A VALID JSON OBJECT with these fields:
{
    "invoice_number": "the invoice number (only numbers and letters, no extra text)",
    "supplier_name": "name of the supplier/company",
    "issue_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD or null if not present",
    "items": [
        {
            "description": "full description of the item or service",
            "quantity": "numeric value (default to 1.0 if unclear)",
            "unit_price": "numeric price value (IMPORTANT: extract actual price, not 0)",
            "total_price": "numeric value or null"
        },
        ... more items
    ],
    "subtotal": "numeric value",
    "tax": "numeric value",
    "total": "numeric value",
    "raw_text": "summary of the invoice content"
}

CRITICAL INSTRUCTIONS:
1. Find ALL services/items in the document even if not in a typical "invoice" format
2. For each line item, set quantity to 1.0 if not explicitly specified
3. For each line item, THE PRICE IS CRITICAL - look in the same row or right-aligned columns for price values
4. MOST IMPORTANT: If you see a dollar amount on the same line as a service name, that is the price - DO NOT SET IT TO ZERO
5. For values like "$9900.00" or "$26400.00" shown on the right side of service names, these are the prices
6. Look for prices in formats like "$1000", "1,000.00", "1000 kr", "1.000,00", etc.
7. If service names include numbers like "ÅTA nr 6", extract the full text as description
8. Extract negative values with the negative sign (e.g., "-1000" or "-$1000")
9. If you see "1 x $0.00" in the document, IGNORE THE $0.00 and look for the actual price value elsewhere on the line
10. THE RIGHT-ALIGNED NUMBER next to each service is typically the price - use that value
11. Carefully examine columns with numbers, looking for values that are aligned vertically and appear to be prices
12. For multi-column layouts, check BOTH the price column and total column for relevant values
13. Check all monetary values in the document to ensure no prices are missed
14. NEVER return a zero price unless absolutely certain there is no price information for that item
15. If a price appears to be missing but there are other prices in the document, use pattern recognition to estimate a reasonable value

If you find items but can't determine specific prices, use the right-most numerical value on the same line.
NEVER return 0 for prices unless there is absolutely no price information available.
"""

# Default values
DEFAULT_INVOICE_NUMBER = "Unknown"
DEFAULT_SUPPLIER_NAME = "Unknown"
DEFAULT_QUANTITY = 1.0
DEFAULT_PRICE = 0.0

# Supported file types for invoices (async processing)
SUPPORTED_INVOICE_FILE_TYPES = ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx']

# Supported file types for general document processing
SUPPORTED_DOCUMENT_FILE_TYPES = ['.pdf', '.jpg', '.jpeg', '.png'] 