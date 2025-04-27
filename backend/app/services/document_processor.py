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
        
        self.description = str(data.get("description", ""))
        self.quantity = float(data.get("quantity", 0.0) or 0.0)
        self.unit_price = float(data.get("unit_price", 0.0) or 0.0)
        self.total_price = float(data.get("total_price", 0.0) or 0.0)

class ExtractedDocument:
    def __init__(self, data: Dict):
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict for ExtractedDocument data, got {type(data)}")
            
        self.invoice_number = str(data.get("invoice_number", "Unknown"))
        self.supplier_name = str(data.get("supplier_name", "Unknown"))
        self.raw_text = str(data.get("raw_text", ""))
        
        try:
            self.issue_date = data.get("issue_date", date.today().isoformat())
            if not self.issue_date:
                self.issue_date = date.today().isoformat()
        except Exception as e:
            logger.warning(f"Invalid issue_date: {data.get('issue_date')}, using today's date")
            self.issue_date = date.today().isoformat()
            
        self.due_date = data.get("due_date")
        
        try:
            items_data = data.get("items", [])
            if not isinstance(items_data, list):
                logger.warning("Items data is not a list, using empty list")
                items_data = []
            
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
    @staticmethod
    def verify_invoice(image: Image.Image) -> Tuple[bool, str]:
        """Verify if the document is an invoice using Gemini."""
        logger.info("Starting invoice verification")
        try:
            prompt = """
            Analyze this image and determine if it is an invoice.
            Consider the following characteristics:
            1. Presence of invoice number
            2. Item listings with quantities and prices
            3. Supplier/vendor information
            4. Total amount
            5. Tax information
            
            You must respond with ONLY a valid JSON object in this exact format:
            {
                "is_invoice": true or false,
                "confidence": number between 0 and 1,
                "reason": "explanation of your decision"
            }
            """
            
            response = model.generate_content([prompt, image])
            content = response.text.strip()
            
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            result = json.loads(content)
            
            if not isinstance(result.get("is_invoice"), bool):
                logger.error(f"Invalid is_invoice value: {result.get('is_invoice')}")
                return False, "Invalid response from verification model"
                
            if not isinstance(result.get("confidence"), (int, float)) or not 0 <= result.get("confidence") <= 1:
                logger.error(f"Invalid confidence score: {result.get('confidence')}")
                return False, "Invalid confidence score"
            
            if not isinstance(result.get("reason"), str):
                logger.error(f"Invalid reason type: {type(result.get('reason'))}")
                return False, "Invalid response from verification model"
            
            logger.info(f"Invoice verification result: is_invoice={result['is_invoice']}, confidence={result['confidence']}")
            return result["is_invoice"], result["reason"]
            
        except Exception as e:
            logger.error(f"Error during invoice verification: {str(e)}", exc_info=True)
            return False, f"Error during verification: {str(e)}"

    @staticmethod
    def convert_to_image(file_content: bytes, file_extension: str) -> Image.Image:
        """Convert document to image and stitch if multiple pages."""
        logger.info(f"Converting document to image (extension: {file_extension})")
        try:
            if file_extension.lower() == 'pdf':
                images = convert_from_bytes(file_content)
                if not images:
                    raise ValueError("No pages found in PDF")
                
                if len(images) == 1:
                    return images[0]
                
                total_height = sum(img.height for img in images)
                max_width = max(img.width for img in images)
                
                stitched_image = Image.new('RGB', (max_width, total_height))
                
                y_offset = 0
                for img in images:
                    stitched_image.paste(img, (0, y_offset))
                    y_offset += img.height
                    
                return stitched_image
                
            else:
                return Image.open(io.BytesIO(file_content))
                
        except Exception as e:
            logger.error(f"Error converting document to image: {str(e)}", exc_info=True)
            raise ValueError(f"Error converting document to image: {str(e)}")

    @staticmethod
    def extract_document_data(file_content: bytes, file_extension: str) -> Optional[ExtractedDocument]:
        """Extract structured data from a document using Gemini."""
        logger.info("Starting document data extraction")
        try:
            image = DocumentProcessor.convert_to_image(file_content, file_extension)
            
            is_invoice, reason = DocumentProcessor.verify_invoice(image)
            if not is_invoice:
                logger.warning(f"Document verification failed: {reason}")
                raise ValueError(f"Document is not an invoice: {reason}")
            
            prompt = """
            Analyze this image and extract the following information from the document.
            
            You must respond with ONLY a valid JSON object in this exact format:
            {
                "invoice_number": "string",
                "supplier_name": "string",
                "issue_date": "YYYY-MM-DD",
                "due_date": "YYYY-MM-DD or null",
                "items": [
                    {
                        "description": "string",
                        "quantity": number,
                        "unit_price": number,
                        "total_price": number
                    }
                ],
                "subtotal": number,
                "tax": number,
                "total": number,
                "raw_text": "string"
            }
            """
            
            response = model.generate_content([prompt, image])
            content = response.text.strip()
            
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            data = json.loads(content)
            
            required_fields = ["invoice_number", "supplier_name", "issue_date", "items", "subtotal", "tax", "total", "raw_text"]
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise ValueError(f"Missing required fields in response: {missing_fields}")
            
            if not isinstance(data["items"], list):
                raise ValueError("Items must be a list")
            
            for i, item in enumerate(data["items"]):
                if not isinstance(item, dict):
                    raise ValueError(f"Item at index {i} must be a dictionary")
                
                required_item_fields = ["description", "quantity", "unit_price", "total_price"]
                missing_item_fields = [field for field in required_item_fields if field not in item]
                if missing_item_fields:
                    raise ValueError(f"Missing required fields in item {i}: {missing_item_fields}")
            
            logger.info("Successfully extracted and validated document data")
            return ExtractedDocument(data)
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}", exc_info=True)
            raise RuntimeError(f"Error processing document: {str(e)}")
        finally:
            if 'image' in locals():
                image.close()

    @staticmethod
    def compare_documents(contract: Contract, invoice: ExtractedDocument) -> ComparisonResult:
        """Compare an invoice with a contract and return the comparison results."""
        logger.info(f"Starting document comparison (Contract ID: {contract.id})")
        
        supplier_match = contract.supplier_name.lower() == invoice.supplier_name.lower()
        
        contract_services = {service["description"].lower(): service["unit_price"] 
                           for service in contract.services}
        
        all_services_in_contract = True
        price_matches = True
        issues = []
        
        for item in invoice.items:
            service_name = item.description.lower()
            if service_name not in contract_services:
                all_services_in_contract = False
                issues.append({
                    "type": "service_not_in_contract",
                    "service_name": item.description
                })
            else:
                contract_price = contract_services[service_name]
                invoice_price = item.unit_price
                
                if contract_price == 0:
                    if invoice_price != 0:
                        price_matches = False
                        issues.append({
                            "type": "price_mismatch",
                            "service_name": item.description,
                            "contract_value": contract_price,
                            "invoice_value": invoice_price
                        })
                else:
                    price_diff_percentage = abs(invoice_price - contract_price) / contract_price
                    if price_diff_percentage > 0.01:  # 1% tolerance
                        price_matches = False
                        issues.append({
                            "type": "price_mismatch",
                            "service_name": item.description,
                            "contract_value": contract_price,
                            "invoice_value": invoice_price
                        })
        
        if not supplier_match:
            issues.append({
                "type": "supplier_mismatch",
                "contract_value": contract.supplier_name,
                "invoice_value": invoice.supplier_name
            })
        
        matches = {
            "supplier_name": supplier_match,
            "prices_match": price_matches,
            "all_services_in_contract": all_services_in_contract
        }
        
        overall_match = all([supplier_match, price_matches, all_services_in_contract])
        logger.info(f"Comparison complete. Overall match: {overall_match}")
        
        return ComparisonResult({
            "contract_id": contract.id,
            "invoice_data": invoice.to_dict(),
            "matches": matches,
            "issues": issues,
            "overall_match": overall_match
        })

    @staticmethod
    async def process_invoice(file_content: bytes, file_type: str) -> Dict[str, Any]:
        """Process an invoice file and extract relevant information."""
        try:
            # Convert file content to text (placeholder - implement actual conversion)
            text_content = "Sample invoice content"  # TODO: Implement actual conversion
            
            # Prepare prompt for Gemini
            prompt = f"""
            Analyze this invoice document and extract the following information in JSON format:
            - invoice_number
            - supplier_name
            - issue_date (YYYY-MM-DD)
            - due_date (YYYY-MM-DD, if available)
            - items (list of objects with description, quantity, unit_price, total_price)
            - subtotal (if available)
            - tax (if available)
            - total
            
            Document content:
            {text_content}
            """
            
            # Get response from Gemini
            response = model.generate_content(prompt)
            extracted_data = json.loads(response.text)
            
            # Convert dates to datetime objects
            extracted_data["issue_date"] = datetime.strptime(extracted_data["issue_date"], "%Y-%m-%d")
            if extracted_data.get("due_date"):
                extracted_data["due_date"] = datetime.strptime(extracted_data["due_date"], "%Y-%m-%d")
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error processing invoice: {str(e)}")
            raise

    @staticmethod
    async def compare_invoice_with_contract(
        contract: Contract,
        invoice_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare invoice data with contract terms."""
        try:
            # Prepare contract data for comparison
            contract_services = {service["service_name"]: service["unit_price"] 
                              for service in contract.services}
            
            # Initialize comparison results
            matches = {
                "supplier_name": contract.supplier_name == invoice_data["supplier_name"],
                "prices_match": True,
                "all_services_in_contract": True
            }
            
            issues = []
            
            # Check supplier name match
            if not matches["supplier_name"]:
                issues.append({
                    "type": "supplier_mismatch",
                    "contract_value": contract.supplier_name,
                    "invoice_value": invoice_data["supplier_name"]
                })
            
            # Check each invoice item against contract
            for item in invoice_data["items"]:
                service_name = item["description"]
                unit_price = item["unit_price"]
                
                if service_name not in contract_services:
                    matches["all_services_in_contract"] = False
                    issues.append({
                        "type": "service_not_in_contract",
                        "service_name": service_name
                    })
                elif contract_services[service_name] != unit_price:
                    matches["prices_match"] = False
                    issues.append({
                        "type": "price_mismatch",
                        "service_name": service_name,
                        "contract_value": contract_services[service_name],
                        "invoice_value": unit_price
                    })
            
            # Calculate overall match
            overall_match = all(matches.values())
            
            return {
                "contract_id": contract.id,
                "invoice_data": invoice_data,
                "matches": matches,
                "issues": issues,
                "overall_match": overall_match
            }
            
        except Exception as e:
            logger.error(f"Error comparing invoice with contract: {str(e)}")
            raise