import os
import json
from typing import Dict, Optional, List, Tuple
from datetime import date, datetime
import google.generativeai as genai
from pdf2image import convert_from_bytes
from PIL import Image
from dotenv import load_dotenv
import io
from logging_config import logger

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))

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

class Contract:
    def __init__(self, data: Dict):
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict for Contract data, got {type(data)}")
        self.id = data.get("id", "")
        self.supplier_name = data.get("supplier_name", "")
        self.services = data.get("services", [])
        self.created_at = data.get("created_at", datetime.now().isoformat())
        self.updated_at = data.get("updated_at")

class ComparisonResult:
    def __init__(self, data: Dict):
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict for ComparisonResult data, got {type(data)}")
            
        self.contract_id = data.get("contract_id", "")
        
        # Handle invoice_data conversion
        invoice_data = data.get("invoice_data", {})
        if isinstance(invoice_data, ExtractedDocument):
            self.invoice_data = invoice_data
        elif isinstance(invoice_data, dict):
            # Convert items to InvoiceItem objects if they aren't already
            if "items" in invoice_data and isinstance(invoice_data["items"], list):
                invoice_data["items"] = [
                    item if isinstance(item, InvoiceItem) 
                    else InvoiceItem(item) if isinstance(item, dict)
                    else InvoiceItem(item.__dict__ if hasattr(item, "__dict__") else {})
                    for item in invoice_data["items"]
                ]
            try:
                self.invoice_data = ExtractedDocument(invoice_data)
            except Exception as e:
                logger.error(f"Error converting invoice_data: {str(e)}")
                raise ValueError(f"Invalid invoice_data format: {str(e)}")
        else:
            logger.error(f"Invalid invoice_data type: {type(invoice_data)}")
            raise ValueError(f"Invalid invoice_data type: {type(invoice_data)}")
        
        # Handle matches
        matches_data = data.get("matches", {})
        if not isinstance(matches_data, dict):
            logger.warning("Invalid matches data format, using defaults")
            matches_data = {}
            
        self.matches = {
            "supplier_name": bool(matches_data.get("supplier_name", False)),
            "prices_match": bool(matches_data.get("prices_match", False)),
            "all_services_in_contract": bool(matches_data.get("all_services_in_contract", False))
        }
        
        # Handle issues
        issues_data = data.get("issues", [])
        if not isinstance(issues_data, list):
            logger.warning("Invalid issues data format, using empty list")
            issues_data = []
            
        self.issues = issues_data
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
            
            Important:
            1. Return ONLY the JSON object
            2. Do not include any other text or explanations
            3. Do not include markdown code blocks
            4. Ensure the JSON is properly formatted
            5. The confidence must be a number between 0 and 1
            6. The is_invoice must be a boolean (true or false)
            7. The reason must be a string
            """
            
            logger.debug("Sending verification request to Gemini")
            response = model.generate_content([prompt, image])
            content = response.text.strip()
            
            # Log the raw response for debugging
            logger.debug(f"Raw Gemini response: {content}")
            
            # Clean the response if it contains markdown code blocks
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # Parse the JSON response
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response. Raw content: {content}")
                raise ValueError(f"Invalid JSON response from Gemini: {str(e)}")
            
            # Validate the response
            if not isinstance(result.get("is_invoice"), bool):
                logger.error(f"Invalid is_invoice value: {result.get('is_invoice')}")
                return False, "Invalid response from verification model: is_invoice must be a boolean"
                
            if not isinstance(result.get("confidence"), (int, float)) or not 0 <= result.get("confidence") <= 1:
                logger.error(f"Invalid confidence score: {result.get('confidence')}")
                return False, "Invalid confidence score: must be a number between 0 and 1"
            
            if not isinstance(result.get("reason"), str):
                logger.error(f"Invalid reason type: {type(result.get('reason'))}")
                return False, "Invalid response from verification model: reason must be a string"
            
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
                logger.debug("Converting PDF to images")
                # Convert PDF to images
                images = convert_from_bytes(file_content)
                if not images:
                    logger.error("No pages found in PDF")
                    raise ValueError("No pages found in PDF")
                
                # If single page, return it
                if len(images) == 1:
                    logger.info("Single page PDF, returning first page")
                    return images[0]
                
                # For multiple pages, stitch them vertically
                logger.info(f"Stitching {len(images)} pages together")
                total_height = sum(img.height for img in images)
                max_width = max(img.width for img in images)
                
                # Create a new image with the total height
                stitched_image = Image.new('RGB', (max_width, total_height))
                
                # Paste each image
                y_offset = 0
                for i, img in enumerate(images):
                    logger.debug(f"Stitching page {i+1}/{len(images)}")
                    stitched_image.paste(img, (0, y_offset))
                    y_offset += img.height
                    
                logger.info("Successfully stitched all pages")
                return stitched_image
                
            else:
                logger.info("Opening image file")
                # For image files, just open and return
                return Image.open(io.BytesIO(file_content))
                
        except Exception as e:
            logger.error(f"Error converting document to image: {str(e)}", exc_info=True)
            raise ValueError(f"Error converting document to image: {str(e)}")

    @staticmethod
    def extract_document_data(file_content: bytes, file_extension: str) -> Optional[ExtractedDocument]:
        """Extract structured data from a document using Gemini."""
        logger.info("Starting document data extraction")
        try:
            # Convert document to image
            image = DocumentProcessor.convert_to_image(file_content, file_extension)
            
            # Verify if it's an invoice
            is_invoice, reason = DocumentProcessor.verify_invoice(image)
            if not is_invoice:
                logger.warning(f"Document verification failed: {reason}")
                raise ValueError(f"Document is not an invoice: {reason}")
            
            logger.info("Document verified as invoice, proceeding with data extraction")

            # Create the prompt for Gemini
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
            
            Important:
            1. Return ONLY the JSON object
            2. Do not include any other text or explanations
            3. Do not include markdown code blocks
            4. Ensure the JSON is properly formatted
            5. All monetary values must be numbers
            6. Dates must be in YYYY-MM-DD format
            7. Use null for missing fields
            8. Include the raw text content of the document
            9. The items array can be empty if no items are found
            """
            
            try:
                logger.debug("Sending extraction request to Gemini")
                # Get response from Gemini
                response = model.generate_content([prompt, image])
                content = response.text.strip()
                
                # Log the raw response for debugging
                logger.debug(f"Raw Gemini response: {content}")
                
                # Clean the response if it contains markdown code blocks
                if content.startswith('```json'):
                    content = content[7:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                logger.debug("Parsing Gemini response")
                # Parse the JSON response
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response. Raw content: {content}")
                    raise ValueError(f"Invalid JSON response from Gemini: {str(e)}")
                
                # Validate required fields
                required_fields = ["invoice_number", "supplier_name", "issue_date", "items", "subtotal", "tax", "total", "raw_text"]
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    logger.error(f"Missing required fields in response: {missing_fields}")
                    raise ValueError(f"Missing required fields in response: {missing_fields}")
                
                # Validate data types
                if not isinstance(data["items"], list):
                    logger.error(f"Invalid items type: {type(data['items'])}")
                    raise ValueError("Items must be a list")
                
                # Validate each item in the items list
                for i, item in enumerate(data["items"]):
                    if not isinstance(item, dict):
                        logger.error(f"Invalid item type at index {i}: {type(item)}")
                        raise ValueError(f"Item at index {i} must be a dictionary")
                    
                    required_item_fields = ["description", "quantity", "unit_price", "total_price"]
                    missing_item_fields = [field for field in required_item_fields if field not in item]
                    if missing_item_fields:
                        logger.error(f"Missing required fields in item {i}: {missing_item_fields}")
                        raise ValueError(f"Missing required fields in item {i}: {missing_item_fields}")
                
                logger.info("Successfully extracted and validated document data")
                return ExtractedDocument(data)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing Gemini response: {str(e)}", exc_info=True)
                raise RuntimeError(f"Error parsing Gemini response: {str(e)}")
            except Exception as e:
                logger.error(f"Error getting response from Gemini: {str(e)}", exc_info=True)
                raise RuntimeError(f"Error getting response from Gemini: {str(e)}")

        except Exception as e:
            logger.error(f"Error processing document: {str(e)}", exc_info=True)
            raise RuntimeError(f"Error processing document: {str(e)}")
        finally:
            # Clean up
            if 'image' in locals():
                logger.debug("Cleaning up image resources")
                image.close()

    @staticmethod
    def compare_documents(contract: Contract, invoice: ExtractedDocument) -> ComparisonResult:
        """Compare an invoice with a contract and return the comparison results."""
        logger.info(f"Starting document comparison (Contract ID: {contract.id})")
        
        # Check supplier name match
        supplier_match = contract.supplier_name.lower() == invoice.supplier_name.lower()
        logger.debug(f"Supplier name match: {supplier_match}")
        
        # Check if all services in invoice are in contract
        contract_services = {service["service_name"].lower(): service["unit_price"] 
                           for service in contract.services}
        
        all_services_in_contract = True
        price_matches = True
        issues = []
        
        logger.debug("Checking service matches")
        for item in invoice.items:
            service_name = item.description.lower()
            if service_name not in contract_services:
                logger.warning(f"Service not in contract: {item.description}")
                all_services_in_contract = False
                issues.append({
                    "type": "service_not_in_contract",
                    "service_name": item.description
                })
            else:
                # Check if price matches within 1% tolerance
                contract_price = contract_services[service_name]
                invoice_price = item.unit_price
                
                # Handle zero prices
                if contract_price == 0:
                    if invoice_price != 0:
                        logger.warning(f"Price mismatch for {item.description}: Contract=0, Invoice={invoice_price}")
                        price_matches = False
                        issues.append({
                            "type": "price_mismatch",
                            "service_name": item.description,
                            "contract_value": contract_price,
                            "invoice_value": invoice_price
                        })
                else:
                    # Calculate price difference percentage
                    price_diff_percentage = abs(invoice_price - contract_price) / contract_price
                    if price_diff_percentage > 0.01:  # 1% tolerance
                        logger.warning(f"Price mismatch for {item.description}: Contract={contract_price}, Invoice={invoice_price}")
                        price_matches = False
                        issues.append({
                            "type": "price_mismatch",
                            "service_name": item.description,
                            "contract_value": contract_price,
                            "invoice_value": invoice_price
                        })
        
        if not supplier_match:
            logger.warning(f"Supplier name mismatch: Contract={contract.supplier_name}, Invoice={invoice.supplier_name}")
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