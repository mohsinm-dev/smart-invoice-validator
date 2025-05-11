import os
import json
from typing import Dict, Optional, List, Tuple, Any
from datetime import date, datetime
import google.generativeai as genai
from pdf2image import convert_from_bytes
from PIL import Image
from pathlib import Path
import io
from loguru import logger
from ..config import settings
from ..models import Contract, Invoice

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel(settings.GEMINI_MODEL)

class InvoiceItem:
    def __init__(self, data: Dict):
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict for InvoiceItem data, got {type(data)}")
        
        # Handle description
        self.description = str(data.get("description", ""))
        
        # Handle numeric values with proper type conversion
        try:
            self.quantity = float(data.get("quantity", 0.0) or 0.0)
        except (TypeError, ValueError):
            logger.warning(f"Invalid quantity value: {data.get('quantity')}, using default 0.0")
            self.quantity = 0.0
            
        try:
            self.unit_price = float(data.get("unit_price", 0.0) or 0.0)
        except (TypeError, ValueError):
            logger.warning(f"Invalid unit_price value: {data.get('unit_price')}, using default 0.0")
            self.unit_price = 0.0
            
        try:
            self.total_price = float(data.get("total_price", 0.0) or 0.0)
        except (TypeError, ValueError):
            logger.warning(f"Invalid total_price value: {data.get('total_price')}, using default 0.0")
            self.total_price = 0.0

class ExtractedDocument:
    def __init__(self, data: Dict):
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict for ExtractedDocument data, got {type(data)}")
            
        # Handle string values
        self.invoice_number = str(data.get("invoice_number", "Unknown"))
        self.supplier_name = str(data.get("supplier_name", "Unknown"))
        self.raw_text = str(data.get("raw_text", ""))
        
        # Handle dates
        try:
            self.issue_date = data.get("issue_date", date.today().isoformat())
            if not self.issue_date:
                self.issue_date = date.today().isoformat()
        except Exception as e:
            logger.warning(f"Invalid issue_date: {data.get('issue_date')}, using today's date")
            self.issue_date = date.today().isoformat()
            
        self.due_date = data.get("due_date")
        
        # Handle items
        try:
            items_data = data.get("items", [])
            if not isinstance(items_data, list):
                logger.warning("Items data is not a list, using empty list")
                items_data = []
            
            # Convert items to InvoiceItem objects
            self.items = []
            for item in items_data:
                if isinstance(item, InvoiceItem):
                    self.items.append(item)
                elif isinstance(item, dict):
                    self.items.append(InvoiceItem(item))
                elif hasattr(item, '__dict__'):
                    self.items.append(InvoiceItem(item.__dict__))
                else:
                    logger.warning(f"Invalid item type: {type(item)}, skipping")
                    
        except Exception as e:
            logger.warning(f"Error processing items: {str(e)}, using empty list")
            self.items = []
        
        # Handle numeric values with proper type conversion
        try:
            self.subtotal = float(data.get("subtotal", 0.0) or 0.0)
        except (TypeError, ValueError):
            logger.warning(f"Invalid subtotal value: {data.get('subtotal')}, using default 0.0")
            self.subtotal = 0.0
            
        try:
            self.tax = float(data.get("tax", 0.0) or 0.0)
        except (TypeError, ValueError):
            logger.warning(f"Invalid tax value: {data.get('tax')}, using default 0.0")
            self.tax = 0.0
            
        try:
            self.total = float(data.get("total", 0.0) or 0.0)
        except (TypeError, ValueError):
            logger.warning(f"Invalid total value: {data.get('total')}, using default 0.0")
            self.total = 0.0
            
    def to_dict(self) -> Dict:
        """Convert the document to a dictionary."""
        return {
            "invoice_number": self.invoice_number,
            "supplier_name": self.supplier_name,
            "issue_date": self.issue_date,
            "due_date": self.due_date,
            "items": [
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price
                }
                for item in self.items
            ],
            "subtotal": self.subtotal,
            "tax": self.tax,
            "total": self.total,
            "raw_text": self.raw_text
        }

class ComparisonResult:
    def __init__(self, data: Dict):
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict for ComparisonResult data, got {type(data)}")
            
        self.contract_id = data.get("contract_id", "")
        self.invoice_data = data.get("invoice_data", {})
        self.matches = {
            "supplier_name": bool(data.get("matches", {}).get("supplier_name", False)),
            "prices_match": bool(data.get("matches", {}).get("prices_match", False)),
            "all_services_in_contract": bool(data.get("matches", {}).get("all_services_in_contract", False))
        }
        self.issues = data.get("issues", [])
        self.overall_match = bool(data.get("overall_match", False))

class DocumentProcessor:
    """Process and extract data from invoice documents."""
    
    def __init__(self):
        self.model = model
        logger.info("DocumentProcessor initialized with Gemini model")
    
    def process_document(self, file_content: bytes, file_name: str) -> Dict:
        """
        Process a document file and extract its data.
        
        Args:
            file_content: The binary content of the file
            file_name: The name of the file
            
        Returns:
            Extracted data as a dictionary
        """
        logger.info(f"Processing document: {file_name}")
        
        # Convert PDF to images if it's a PDF
        if file_name.lower().endswith('.pdf'):
            logger.info("Converting PDF to images")
            try:
                images = self._convert_pdf_to_images(file_content)
                if not images:
                    logger.error("Failed to convert PDF to images")
                    return {"error": "Failed to convert PDF to images"}
                
                # Process the first page for now
                image_bytes = self._get_image_bytes(images[0])
                if not image_bytes:
                    logger.error("Failed to convert image to bytes")
                    return {"error": "Failed to process document image"}
                
                # Extract data from the image
                extracted_data = self._extract_data_from_image(image_bytes)
                
            except Exception as e:
                logger.error(f"Error processing PDF: {str(e)}")
                return {"error": f"Error processing document: {str(e)}"}
                
        # Handle image files directly
        elif file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
            logger.info("Processing image file directly")
            try:
                extracted_data = self._extract_data_from_image(file_content)
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}")
                return {"error": f"Error processing document: {str(e)}"}
                
        else:
            logger.error(f"Unsupported file format: {file_name}")
            return {"error": "Unsupported file format. Please upload a PDF or image file."}
            
        return extracted_data
    
    def process_contract(self, file_content: bytes, file_name: str) -> Dict:
        """
        Process a contract document file and extract services and supplier information.
        
        Args:
            file_content: The binary content of the file
            file_name: The name of the file
            
        Returns:
            Extracted contract data as a dictionary
        """
        logger.info(f"Processing contract document: {file_name}")
        
        # Convert PDF to images if it's a PDF
        if file_name.lower().endswith('.pdf'):
            logger.info("Converting contract PDF to images")
            try:
                images = self._convert_pdf_to_images(file_content)
                if not images:
                    logger.error("Failed to convert contract PDF to images")
                    return {"error": "Failed to convert contract PDF to images"}
                
                # Use first page for basic contract details
                image_bytes = self._get_image_bytes(images[0])
                if not image_bytes:
                    logger.error("Failed to convert contract image to bytes")
                    return {"error": "Failed to process contract image"}
                
                # Extract data from the image
                contract_data = self._extract_contract_data_from_image(image_bytes)
                
                # If contract has multiple pages, extract services from all pages
                if len(images) > 1:
                    logger.info(f"Processing {len(images)} pages for service details")
                    all_services = []
                    
                    # We already processed the first page
                    for i in range(1, len(images)):
                        page_image_bytes = self._get_image_bytes(images[i])
                        if page_image_bytes:
                            page_services = self._extract_services_from_image(page_image_bytes)
                            if page_services and isinstance(page_services, list):
                                all_services.extend(page_services)
                    
                    # Add services from additional pages
                    if all_services:
                        if not contract_data.get("services"):
                            contract_data["services"] = all_services
                        else:
                            contract_data["services"].extend(all_services)
                
            except Exception as e:
                logger.error(f"Error processing contract PDF: {str(e)}")
                return {"error": f"Error processing contract document: {str(e)}"}
                
        # Handle image files directly
        elif file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
            logger.info("Processing contract image file directly")
            try:
                contract_data = self._extract_contract_data_from_image(file_content)
            except Exception as e:
                logger.error(f"Error processing contract image: {str(e)}")
                return {"error": f"Error processing contract image: {str(e)}"}
                
        else:
            logger.error(f"Unsupported contract file format: {file_name}")
            return {"error": "Unsupported file format. Please upload a PDF or image file."}
        
        # Ensure contract data has all required fields
        if not contract_data.get("error"):
            if not contract_data.get("supplier_name"):
                # Try to extract from filename if not found in document
                supplier_name = file_name.split('.')[0].replace('_', ' ').replace('-', ' ')
                contract_data["supplier_name"] = supplier_name
                logger.info(f"Using filename as supplier name: {supplier_name}")
            
            # Ensure services is at least an empty array
            if not contract_data.get("services"):
                contract_data["services"] = []
                logger.warning("No services found in contract document")
        
        return contract_data
    
    def _convert_pdf_to_images(self, pdf_bytes: bytes) -> List[Image.Image]:
        """Convert PDF bytes to a list of PIL Images."""
        try:
            return convert_from_bytes(pdf_bytes)
        except Exception as e:
            logger.error(f"PDF conversion error: {str(e)}")
            return []
    
    def _get_image_bytes(self, image: Image.Image) -> Optional[bytes]:
        """Convert PIL Image to bytes."""
        try:
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            return img_byte_arr.getvalue()
        except Exception as e:
            logger.error(f"Image conversion error: {str(e)}")
            return None
    
    def _extract_data_from_image(self, image_bytes: bytes) -> Dict:
        """Extract invoice data from an image using Gemini."""
        try:
            response = self.model.generate_content(
                [
                    "Extract all relevant invoice information from this document. Include invoice number, issue date, due date, supplier name, line items (with description, quantity, unit price, and total price), subtotal, tax, and total amount. Format as a JSON object.",
                    {"mime_type": "image/png", "data": image_bytes}
                ]
            )
            
            # Process the response to get structured data
            return self._process_gemini_response(response)
            
        except Exception as e:
            logger.error(f"Data extraction error: {str(e)}")
            return {"error": f"Error extracting data from document: {str(e)}"}
    
    def _extract_contract_data_from_image(self, image_bytes: bytes) -> Dict:
        """Extract contract data from an image using Gemini."""
        try:
            prompt = """
            Analyze this contract document image in extreme detail and extract the following information.
            
            CRITICAL: Pay special attention to all services/line items and their prices!
            
            Please provide your response as a valid JSON object with these fields:
            {
                "supplier_name": "The full name of the supplier or vendor (company name)",
                "services": [
                    {
                        "service_name": "Complete name of the service or product as written",
                        "unit_price": numerical price value (extract the actual price, never 0 unless explicitly stated)
                    },
                    ... more services
                ],
                "effective_date": "YYYY-MM-DD or null if not present",
                "expiration_date": "YYYY-MM-DD or null if not present",
                "payment_terms": "Description of payment terms if present",
                "max_amount": numerical value of maximum contract amount if specified, null otherwise
            }
            
            EXTRACTION INSTRUCTIONS:
            1. Find ALL services/items with associated pricing, even if not in a clear "price list" format
            2. For each service, extract the complete name exactly as written
            3. ALWAYS extract the actual price value associated with each service (never default to 0)
            4. If service names include numbers like "ÅTA nr 6", extract the full text as service_name
            5. Look for prices in formats like "$1000", "1,000.00", "1000 kr", "1.000,00", etc.
            6. Extract negative values with the negative sign (e.g., "-1000" or "-$1000")
            7. If a service appears to have multiple line items, split them into separate services
            8. Pay special attention to service descriptions that span multiple lines
            9. IMPORTANT: For headline/main project descriptions (like "Ombyggnad av lokaler..."), use the total contract amount as the price if no specific price is listed
            10. When a description mentions a sum (like "Kontraktssumma"), use that value as the unit_price
            
            Focus on extracting every single service or line item with its pricing.
            If you can't find specific fields, use null or empty arrays as appropriate.
            Never set unit_price to 0 unless explicitly shown as zero in the document.
            """
            
            response = self.model.generate_content(
                [
                    prompt,
                    {"mime_type": "image/png", "data": image_bytes}
                ]
            )
            
            # Process the response to get structured contract data
            contract_data = self._process_gemini_response(response)
            
            # Normalize services data structure
            if "services" in contract_data and isinstance(contract_data["services"], list):
                normalized_services = []
                for service in contract_data["services"]:
                    if isinstance(service, dict):
                        # Extract and clean service name
                        service_name = service.get("service_name", "Unknown Service")
                        service_name = " ".join(service_name.split())
                        
                        # Extract and validate price
                        price_str = str(service.get("unit_price", "0")).strip()
                        # Handle various price formats
                        price_str = price_str.replace(",", ".")  # Replace comma with dot
                        price_str = price_str.replace(" ", "")   # Remove spaces
                        # Handle negative values with minus sign or parentheses
                        is_negative = price_str.startswith("-") or price_str.startswith("(")
                        price_str = price_str.replace("-", "").replace("(", "").replace(")", "")
                        
                        try:
                            unit_price = float(price_str)
                            if is_negative:
                                unit_price = -unit_price
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid price value: {price_str}, using 0.0")
                            unit_price = 0.0
                        
                        normalized_service = {
                            "service_name": service_name,
                            "unit_price": unit_price
                        }
                        normalized_services.append(normalized_service)
                
                contract_data["services"] = normalized_services
            
            return contract_data
            
        except Exception as e:
            logger.error(f"Contract data extraction error: {str(e)}")
            return {"error": f"Error extracting data from contract document: {str(e)}"}
    
    def _extract_services_from_image(self, image_bytes: bytes) -> List[Dict]:
        """Extract services and pricing information from an image."""
        try:
            prompt = """
            Examine this contract page in detail and extract ONLY the services or products with their pricing.
            
            CRITICAL: Find ALL services/line items and their associated prices!
            
            Return a JSON array of objects like this:
            [
                {
                    "service_name": "Complete description of the service exactly as written",
                    "unit_price": numerical price value (never use 0 unless explicitly stated as 0)
                },
                ... more services
            ]
            
            IMPORTANT INSTRUCTIONS:
            1. Extract ALL items that appear to be services, work items, products, or deliverables
            2. Always include the FULL description of each service (don't abbreviate or summarize)
            3. For each service, extract the associated price value, never defaulting to 0
            4. Include item numbers/references as part of the service name (e.g., "ÅTA nr 6")
            5. Look for prices in any format: "$1000", "1,000.00", "1000 kr", etc.
            6. Don't skip any services - capture everything that has an associated price
            7. If a price appears negative (with minus sign or parentheses), capture it as negative
            
            If no services or pricing information is found, return an empty array.
            """
            
            response = self.model.generate_content(
                [
                    prompt,
                    {"mime_type": "image/png", "data": image_bytes}
                ]
            )
            
            content = response.text.strip()
            
            # Try to extract JSON from the response
            json_start = content.find('[')
            json_end = content.rfind(']')
            
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end+1]
                try:
                    services = json.loads(json_str)
                    
                    # Validate and normalize each service
                    if isinstance(services, list):
                        return [
                            {
                                "service_name": service.get("service_name", "Unknown Service"),
                                "unit_price": float(service.get("unit_price", 0.0)) if service.get("unit_price") is not None else 0.0
                            }
                            for service in services
                            if isinstance(service, dict)
                        ]
                    
                except json.JSONDecodeError:
                    logger.warning("Failed to parse services JSON")
            
            return []
            
        except Exception as e:
            logger.error(f"Service extraction error: {str(e)}")
            return []
    
    def _process_gemini_response(self, response) -> Dict:
        """Process the Gemini response to extract structured invoice data."""
        try:
            # Get text from response
            text = response.text
            
            # Try to extract JSON object if present
            json_start = text.find('{')
            json_end = text.rfind('}')
            
            if json_start >= 0 and json_end > json_start:
                json_str = text[json_start:json_end+1]
                try:
                    data = json.loads(json_str)
                    return self._normalize_extracted_data(data)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON from response, using fallback extraction")
            
            # Fallback to structured text analysis
            logger.info("Using fallback text analysis for extraction")
            extracted_data = self._extract_from_text(text)
            return extracted_data
            
        except Exception as e:
            logger.error(f"Response processing error: {str(e)}")
            return {"error": f"Error processing AI response: {str(e)}"}
    
    def _normalize_extracted_data(self, data: Dict) -> Dict:
        """Normalize the extracted data to ensure consistent structure."""
        if not isinstance(data, dict):
            logger.warning(f"Expected dict for data, got {type(data)}")
            return {"error": "Invalid data format"}
        
        # For invoice data, use ExtractedDocument
        if "invoice_number" in data or "total" in data:
            try:
                document = ExtractedDocument(data)
                return document.to_dict()
            except Exception as e:
                logger.error(f"Error normalizing invoice data: {str(e)}")
                return data
        
        # For contract data, just return it with basic validation
        return data
    
    def _extract_from_text(self, text: str) -> Dict:
        """Extract structured data from unstructured text."""
        # Basic extraction logic for fallback
        result = {
            "invoice_number": "Unknown",
            "supplier_name": "Unknown",
            "issue_date": date.today().isoformat(),
            "due_date": None,
            "items": [],
            "subtotal": 0.0,
            "tax": 0.0,
            "total": 0.0,
            "raw_text": text
        }
        
        # Look for invoice number
        if "invoice" in text.lower() and "#" in text:
            lines = text.split("\n")
            for line in lines:
                if "invoice" in line.lower() and "#" in line:
                    parts = line.split("#")
                    if len(parts) > 1:
                        result["invoice_number"] = parts[1].strip()
        
        # Extract total amount
        if "total" in text.lower():
            lines = text.split("\n")
            for line in lines:
                if "total" in line.lower():
                    # Try to extract a number
                    import re
                    numbers = re.findall(r'\d+\.\d+|\d+', line)
                    if numbers:
                        try:
                            result["total"] = float(numbers[-1])
                        except ValueError:
                            pass
        
        return result
    
    def verify_invoice(self, invoice_data: Dict, contract: Contract) -> Tuple[bool, List[str]]:
        """
        Verify if an invoice complies with the contract terms.
        
        Args:
            invoice_data: The extracted invoice data
            contract: The contract model object to verify against
            
        Returns:
            Tuple of (is_valid, list of issues found)
        """
        issues = []
        is_valid = True
        
        # Create a document object for easier access
        try:
            document = ExtractedDocument(invoice_data)
        except Exception as e:
            logger.error(f"Error creating ExtractedDocument: {str(e)}")
            return False, [f"Invalid invoice data format: {str(e)}"]
        
        # Check supplier name
        if contract.supplier_name and document.supplier_name != "Unknown":
            if contract.supplier_name.lower() not in document.supplier_name.lower():
                issues.append(f"Supplier name mismatch: Expected '{contract.supplier_name}', found '{document.supplier_name}'")
                is_valid = False
        
        # Check total amount against contract max amount
        if contract.max_amount and document.total > contract.max_amount:
            issues.append(f"Invoice total (${document.total}) exceeds contract maximum (${contract.max_amount})")
            is_valid = False
        
        # Check due date against contract terms
        if contract.payment_terms and document.due_date:
            # Implementation depends on how payment_terms is stored
            # This is a placeholder for the logic
            pass
        
        # Check line items against contract items (if specified)
        if hasattr(contract, 'items') and contract.items:
            # This would need to be implemented based on how contract items are stored
            pass
        
        return is_valid, issues
    
    def compare_documents(self, doc1: Dict, doc2: Dict) -> Tuple[bool, List[str], Dict]:
        """
        Compare two documents for discrepancies.
        
        Args:
            doc1: First document data
            doc2: Second document data
            
        Returns:
            Tuple of (is_matching, list of discrepancies, comparison details)
        """
        discrepancies = []
        comparison = {}
        is_matching = True
        
        try:
            # Convert to ExtractedDocument objects
            extracted1 = ExtractedDocument(doc1)
            extracted2 = ExtractedDocument(doc2)
            
            # Compare invoice numbers
            if extracted1.invoice_number != extracted2.invoice_number:
                discrepancies.append(f"Invoice number mismatch: '{extracted1.invoice_number}' vs '{extracted2.invoice_number}'")
                comparison["invoice_number"] = {
                    "match": False,
                    "doc1": extracted1.invoice_number,
                    "doc2": extracted2.invoice_number
                }
                is_matching = False
            else:
                comparison["invoice_number"] = {
                    "match": True,
                    "value": extracted1.invoice_number
                }
            
            # Compare supplier names
            if extracted1.supplier_name != extracted2.supplier_name:
                discrepancies.append(f"Supplier name mismatch: '{extracted1.supplier_name}' vs '{extracted2.supplier_name}'")
                comparison["supplier_name"] = {
                    "match": False,
                    "doc1": extracted1.supplier_name,
                    "doc2": extracted2.supplier_name
                }
                is_matching = False
            else:
                comparison["supplier_name"] = {
                    "match": True,
                    "value": extracted1.supplier_name
                }
            
            # Compare issue dates
            if extracted1.issue_date != extracted2.issue_date:
                discrepancies.append(f"Issue date mismatch: '{extracted1.issue_date}' vs '{extracted2.issue_date}'")
                comparison["issue_date"] = {
                    "match": False,
                    "doc1": extracted1.issue_date,
                    "doc2": extracted2.issue_date
                }
                is_matching = False
            else:
                comparison["issue_date"] = {
                    "match": True,
                    "value": extracted1.issue_date
                }
            
            # Compare totals with a tolerance for floating-point comparison
            if abs(extracted1.total - extracted2.total) > 0.01:
                discrepancies.append(f"Total amount mismatch: ${extracted1.total} vs ${extracted2.total}")
                comparison["total"] = {
                    "match": False,
                    "doc1": extracted1.total,
                    "doc2": extracted2.total
                }
                is_matching = False
            else:
                comparison["total"] = {
                    "match": True,
                    "value": extracted1.total
                }
            
            # Additional comparisons could be added for line items, subtotal, tax, etc.
            
        except Exception as e:
            logger.error(f"Error comparing documents: {str(e)}")
            discrepancies.append(f"Error comparing documents: {str(e)}")
            is_matching = False
        
        return is_matching, discrepancies, comparison

    @staticmethod
    async def compare_invoice_with_contract(
        contract: Contract,
        invoice_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Static method for backward compatibility - calls the instance method."""
        try:
            processor = DocumentProcessor()
            return await processor.compare_invoice_with_contract_async(contract, invoice_data)
        except Exception as e:
            logger.error(f"Error in static compare_invoice_with_contract: {str(e)}")
            raise
            
    async def compare_invoice_with_contract_async(
        self,
        contract: Contract,
        invoice_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare invoice data with contract terms."""
        try:
            # Validate contract data
            if not contract or not contract.services:
                logger.warning("Contract is empty or has no services")
                return {
                    "contract_id": getattr(contract, "id", "unknown"),
                    "invoice_data": invoice_data,
                    "matches": {
                        "supplier_name": False,
                        "prices_match": False,
                        "all_services_in_contract": False
                    },
                    "issues": [{"type": "contract_invalid", "detail": "Contract is empty or has no services"}],
                    "overall_match": False
                }
            
            # Validate invoice data
            if not invoice_data:
                logger.warning("Invoice data is empty")
                return {
                    "contract_id": contract.id,
                    "invoice_data": {},
                    "matches": {
                        "supplier_name": False,
                        "prices_match": False,
                        "all_services_in_contract": False
                    },
                    "issues": [{"type": "invoice_invalid", "detail": "Invoice data is empty"}],
                    "overall_match": False
                }
            
            # Ensure items exist
            if "items" not in invoice_data or not invoice_data.get("items"):
                invoice_data["items"] = []
                logger.warning("Invoice has no items")
            
            # Prepare contract data for comparison
            contract_services = {}
            logger.info(f"Contract has {len(contract.services)} services")
            for service in contract.services:
                if isinstance(service, dict) and "service_name" in service:
                    # Keep the original service name
                    original_service_name = service.get("service_name", "")
                    service_name = original_service_name.lower()
                    # Simple normalization - just remove excess whitespace
                    service_name_norm = " ".join(service_name.split())
                    
                    unit_price = float(service.get("unit_price", 0.0)) if service.get("unit_price") is not None else 0.0
                    # Store both original and normalized names for better matching
                    contract_services[service_name_norm] = {
                        "original_name": original_service_name,
                        "price": unit_price
                    }
                    logger.debug(f"Contract service: '{service_name_norm}' -> ${unit_price}")
            
            # Initialize issues and matches
            issues = []
            matches = {
                "prices_match": True,
                "all_services_in_contract": True
            }
            
            # Prepare detailed price comparison
            price_comparison_details = []
            all_prices_match = True

            # Check each invoice item against contract
            for item in invoice_data.get("items", []):
                if not isinstance(item, dict):
                    continue
                # Get the original service description
                original_service_name = item.get("description", "")
                if not original_service_name:
                    continue

                # Keep a normalized version for better matching
                service_name = original_service_name.lower()
                service_name_norm = " ".join(service_name.split())
                
                # Try individual prices first
                try:
                    invoice_price = float(item.get("unit_price", 0.0)) if item.get("unit_price") is not None else 0.0
                except (ValueError, TypeError):
                    invoice_price = 0.0
                
                # If item's total_price exists and is non-zero but unit_price is zero, use total_price
                if invoice_price == 0 and item.get("total_price") and float(item.get("total_price", 0)) > 0:
                    invoice_price = float(item.get("total_price", 0))
                    logger.debug(f"Using total_price as invoice_price for '{service_name_norm}': ${invoice_price}")
                
                logger.debug(f"Invoice item: '{service_name_norm}' -> ${invoice_price}")
                
                # Find matching contract service using various matching techniques
                matched_service = None
                matched_service_name = None
                
                # 1. Try exact match (case-insensitive)
                if service_name_norm in contract_services:
                    matched_service = contract_services[service_name_norm]
                    matched_service_name = service_name_norm
                    logger.debug(f"Found exact match for '{service_name_norm}'")
                
                # 2. Try partial matching if no exact match
                if not matched_service:
                    for contract_service_name, contract_service_data in contract_services.items():
                        # Check if either is a substring of the other
                        if (service_name_norm in contract_service_name or 
                            contract_service_name in service_name_norm):
                            matched_service = contract_service_data
                            matched_service_name = contract_service_name
                            logger.debug(f"Found substring match: '{service_name_norm}' ~ '{contract_service_name}'")
                            break
                
                # 3. Try word-level matching
                if not matched_service:
                    service_words = set(service_name_norm.split())
                    for contract_service_name, contract_service_data in contract_services.items():
                        contract_words = set(contract_service_name.split())
                        # If there's significant word overlap (at least 2 words or 50%)
                        common_words = service_words.intersection(contract_words)
                        if len(common_words) >= 2 or (len(common_words) > 0 and len(common_words) / len(service_words) >= 0.5):
                            matched_service = contract_service_data
                            matched_service_name = contract_service_name
                            logger.debug(f"Found word overlap match: '{service_name_norm}' ~ '{contract_service_name}'")
                            break
                
                # If still no match, process as not found
                if not matched_service:
                    logger.debug(f"No match found for invoice item: '{service_name_norm}'")
                    matches["all_services_in_contract"] = False
                    issues.append({
                        "type": "service_not_in_contract",
                        "service_name": original_service_name
                    })
                    price_comparison_details.append({
                        "service_name": original_service_name,
                        "contract_price": None,
                        "invoice_price": invoice_price,
                        "match": False
                    })
                    all_prices_match = False
                else:
                    contract_price = matched_service["price"]
                    logger.debug(f"Found match: '{original_service_name}' (invoice ${invoice_price}) ~ '{matched_service['original_name']}' (contract ${contract_price})")
                    
                    price_match = (
                        abs(invoice_price - contract_price) <= 0.01 or
                        (invoice_price == 0 and contract_price < 0) or
                        (contract_price == 0 and invoice_price < 0)
                    )
                    price_comparison_details.append({
                        "service_name": original_service_name,
                        "contract_price": contract_price,
                        "invoice_price": invoice_price,
                        "match": price_match
                    })
                    if not price_match:
                        issues.append({
                            "type": "price_mismatch",
                            "service_name": original_service_name,
                            "contract_value": contract_price,
                            "invoice_value": invoice_price
                        })
                        all_prices_match = False

                # If service matched but invoice price is still 0, try to use total prices from the invoice
                if matched_service and invoice_price == 0 and invoice_data.get("total"):
                    # Try to extract price from the right aligned number
                    logger.debug(f"Invoice price is 0 for matched service '{original_service_name}'. Trying to infer from contract.")
                    
                    # If we're showing a price mismatch but the invoice price is 0, use the contract price
                    # and mark it as unverified (this is better than showing $0)
                    contract_price = matched_service["price"]
                    
                    # Add to price comparison with a note
                    price_comparison_details.append({
                        "service_name": original_service_name,
                        "contract_price": contract_price, 
                        "invoice_price": 0.0,
                        "match": False,
                        "note": "Price not detected in invoice"
                    })
                    
                    # Add issue for the missing price
                    issues.append({
                        "type": "price_mismatch", 
                        "service_name": original_service_name,
                        "contract_value": contract_price,
                        "invoice_value": 0.0
                    })
                    
                    all_prices_match = False
                    continue
            
            # Set prices_match based on all price comparisons
            matches["prices_match"] = all_prices_match
            # Remove supplier_name from matches
            if "supplier_name" in matches:
                del matches["supplier_name"]
            # Calculate overall match
            overall_match = all(matches.values())
            return {
                "contract_id": contract.id,
                "invoice_data": invoice_data,
                "matches": matches,
                "issues": issues,
                "overall_match": overall_match,
                "price_comparison_details": price_comparison_details
            }
            
        except Exception as e:
            logger.error(f"Error comparing invoice with contract: {str(e)}")
            # Return a fallback result with error information
            return {
                "contract_id": getattr(contract, "id", "unknown"),
                "invoice_data": invoice_data or {},
                "matches": {
                    "supplier_name": False,
                    "prices_match": False,
                    "all_services_in_contract": False
                },
                "issues": [{"type": "comparison_error", "detail": str(e)}],
                "overall_match": False
            }

    @staticmethod
    async def process_invoice(file_content: bytes, file_type: str) -> Dict[str, Any]:
        """Static method for backward compatibility - calls the instance method."""
        try:
            processor = DocumentProcessor()
            return await processor.process_invoice_async(file_content, file_type)
        except Exception as e:
            logger.error(f"Error in static process_invoice: {str(e)}")
            raise
            
    async def process_invoice_async(self, file_content: bytes, file_type: str) -> Dict[str, Any]:
        """Process an invoice file and extract relevant information."""
        try:
            logger.info(f"Processing invoice file of type: {file_type}")
            
            # Check if the file content is valid
            if not file_content:
                raise ValueError("Empty file content")
                
            if file_type.lower() not in ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx']:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # For image files, convert directly to image
            if file_type.lower() in ['jpg', 'jpeg', 'png']:
                image = Image.open(io.BytesIO(file_content))
            # For PDF files, convert the first page to image
            elif file_type.lower() == 'pdf':
                images = self._convert_pdf_to_images(file_content)
                if not images:
                    raise ValueError("Could not extract any images from PDF")
                image = images[0]  # Use first page
            # For doc/docx, we'll use a basic placeholder approach
            else:
                # In a real implementation, you would use a library to extract text
                # For now, just generate mock data
                return {
                    "invoice_number": "INV-2023-001",
                    "supplier_name": "Sample Supplier",
                    "issue_date": datetime.now(),
                    "due_date": datetime.now(),
                    "items": [
                        {"description": "Service 1", "quantity": 1, "unit_price": 100.0, "total_price": 100.0},
                        {"description": "Service 2", "quantity": 2, "unit_price": 50.0, "total_price": 100.0}
                    ],
                    "subtotal": 200.0,
                    "tax": 20.0,
                    "total": 220.0,
                    "raw_text": "Sample invoice content"
                }
            
            # Create a prompt for Gemini to extract data
            prompt = """
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
                        "quantity": numeric value (default to 1.0 if unclear),
                        "unit_price": numeric price value (IMPORTANT: extract actual price, not 0),
                        "total_price": numeric value or null
                    },
                    ... more items
                ],
                "subtotal": numeric value,
                "tax": numeric value,
                "total": numeric value,
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
            
            # Send to Gemini for processing
            response = self.model.generate_content([prompt, image])
            content = response.text.strip()
            
            # Extract JSON from the response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            # Parse JSON
            logger.info("Parsing extracted data from Gemini")
            extracted_data = json.loads(content)
            
            # Convert date strings to datetime objects
            if extracted_data.get("issue_date"):
                extracted_data["issue_date"] = datetime.strptime(extracted_data["issue_date"], "%Y-%m-%d")
            else:
                extracted_data["issue_date"] = datetime.now()
                
            if extracted_data.get("due_date"):
                extracted_data["due_date"] = datetime.strptime(extracted_data["due_date"], "%Y-%m-%d")
            
            # Ensure all required fields exist
            required_fields = ["invoice_number", "supplier_name", "items", "total"]
            for field in required_fields:
                if field not in extracted_data:
                    extracted_data[field] = "Unknown" if field in ["invoice_number", "supplier_name"] else ([] if field == "items" else 0)
                    logger.warning(f"Missing required field in extracted data: {field}, using default value")
            
            # Ensure total is a number
            if not isinstance(extracted_data["total"], (int, float)) or extracted_data["total"] is None:
                extracted_data["total"] = 0.0
                logger.warning("Invalid or missing total, using default value")
            
            # Ensure subtotal and tax are numbers
            for field in ["subtotal", "tax"]:
                if field not in extracted_data or not isinstance(extracted_data.get(field), (int, float)) or extracted_data.get(field) is None:
                    extracted_data[field] = 0.0
                    logger.warning(f"Invalid or missing {field}, using default value")
            
            # Ensure all item fields exist and are valid numbers
            for i, item in enumerate(extracted_data.get("items", [])):
                # Ensure item is a dictionary
                if not isinstance(item, dict):
                    item = {"description": f"Item {i+1}", "quantity": 1.0, "unit_price": 0.0, "total_price": 0.0}
                    extracted_data["items"][i] = item
                    continue
                    
                # Ensure required item fields exist
                for field in ["description", "quantity", "unit_price"]:
                    if field not in item or item[field] is None:
                        if field == "description":
                            item[field] = f"Item {i+1}"
                        else:
                            item[field] = 1.0 if field == "quantity" else 0.0
                        logger.warning(f"Missing or None {field} in item {i}, using default value")
                
                # Convert numeric fields to float
                for field in ["quantity", "unit_price"]:
                    try:
                        item[field] = float(item[field]) if item[field] is not None else (1.0 if field == "quantity" else 0.0)
                    except (ValueError, TypeError):
                        item[field] = 1.0 if field == "quantity" else 0.0
                        logger.warning(f"Invalid {field} value in item {i}, using default value")
                
                # Special handling: if unit_price is 0 but total_price has a value, use that
                if item["unit_price"] == 0 and "total_price" in item and item["total_price"]:
                    try:
                        total_price = float(item["total_price"])
                        if total_price != 0:
                            # Use total_price as unit_price if quantity is 0 or 1
                            if item["quantity"] <= 1:
                                item["unit_price"] = total_price
                                logger.info(f"Using total_price {total_price} as unit_price for item {i}")
                            else:
                                # Otherwise, calculate unit_price from total and quantity
                                item["unit_price"] = total_price / item["quantity"]
                                logger.info(f"Calculated unit_price {item['unit_price']} from total_price for item {i}")
                    except (ValueError, TypeError, ZeroDivisionError):
                        pass
                        
                # Calculate total_price if not provided or invalid
                if "total_price" not in item or item["total_price"] is None:
                    quantity = float(item["quantity"]) if item["quantity"] is not None else 1.0
                    unit_price = float(item["unit_price"]) if item["unit_price"] is not None else 0.0
                    item["total_price"] = quantity * unit_price
                else:
                    try:
                        item["total_price"] = float(item["total_price"])
                    except (ValueError, TypeError):
                        quantity = float(item["quantity"]) if item["quantity"] is not None else 1.0
                        unit_price = float(item["unit_price"]) if item["unit_price"] is not None else 0.0
                        item["total_price"] = quantity * unit_price
                        logger.warning(f"Invalid total_price in item {i}, calculated from quantity and unit_price")
            
            # If no items were extracted, create a default item
            if not extracted_data["items"]:
                extracted_data["items"] = [
                    {"description": "Unknown Item", "quantity": 1.0, "unit_price": extracted_data["total"], "total_price": extracted_data["total"]}
                ]
                logger.warning("No items extracted, creating default item based on total")
            
            # Ensure all required fields are present
            required_fields = ["invoice_number", "supplier_name", "issue_date", "total"]
            for field in required_fields:
                if field not in extracted_data or extracted_data[field] is None:
                    if field == "invoice_number":
                        extracted_data[field] = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    elif field == "supplier_name":
                        extracted_data[field] = "Unknown Supplier"
                    elif field == "issue_date":
                        extracted_data[field] = datetime.now()
                    elif field == "total":
                        # Calculate total from items if not present
                        total = sum(item.get("total_price", 0) for item in extracted_data["items"])
                        extracted_data[field] = total
                    logger.warning(f"Missing required field {field}, using default value")
            
            logger.info("Successfully processed invoice")
            return extracted_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from Gemini response: {str(e)}")
            raise ValueError(f"Failed to parse invoice data: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing invoice: {str(e)}")
            raise

    async def process_invoice(self, file_path: str) -> Dict[str, Any]:
        """Process an invoice file from a file path."""
        try:
            logger.info(f"Processing invoice file from path: {file_path}")
            
            # Check if the file exists
            if not os.path.exists(file_path):
                raise ValueError(f"File not found: {file_path}")
                
            # Get file extension
            file_extension = file_path.split('.')[-1].lower()
            if file_extension not in ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx']:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            # Read the file content
            with open(file_path, 'rb') as file:
                file_content = file.read()
                
            # Process using existing method
            return await self.process_invoice_async(file_content, file_extension)
            
        except Exception as e:
            logger.error(f"Error processing invoice from file path: {str(e)}")
            raise