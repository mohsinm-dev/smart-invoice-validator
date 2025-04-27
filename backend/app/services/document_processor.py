import io
import json
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field, validator
import google.generativeai as genai
from PIL import Image
from pdf2image import convert_from_bytes

class VerificationResult(BaseModel):
    """Model for document verification result."""
    is_purchase_order: bool = Field(..., description="Whether the document is a purchase order")
    confidence: float = Field(..., description="Confidence score (0-1)", ge=0, le=1)
    reason: str = Field(..., description="Explanation for the verification result")

class ItemId(BaseModel):
    """Model for item ID."""
    id: str = Field(..., description="Item identifier, can contain periods, hyphens, and spaces")

    @validator('id')
    def validate_id(cls, v):
        """Validate that ID is not empty."""
        if not v.strip():
            raise ValueError('Item ID cannot be empty')
        return v

class PurchaseOrderItem(BaseModel):
    """Model for a single item in a purchase order."""
    item: ItemId = Field(..., description="Item with its ID")
    quantity: int = Field(..., description="Quantity of the item", ge=0)
    rate: Optional[float] = Field(None, description="Rate per unit of the item", ge=0)

    @validator('rate')
    def validate_rate(cls, v):
        """Validate that rate is either None or a positive float."""
        if v is not None and v <= 0:
            raise ValueError('Rate must be positive if provided')
        return v

class PurchaseOrderResponse(BaseModel):
    """Model for the complete purchase order response."""
    items: List[PurchaseOrderItem] = Field(..., description="List of items in the purchase order")

class DocumentProcessor:
    def __init__(self, api_key: str, confidence_threshold: float = 0.7, model_name: Optional[str] = None):
        """
        Initialize the DocumentProcessor with Gemini API key.
        
        Args:
            api_key (str): Google Gemini API key
            confidence_threshold (float): Minimum confidence score to consider a document as a purchase order
            model_name (str, optional): Name of the fine-tuned model to use. If None, uses the base model.
            
        Raises:
            ValueError: If API key is invalid or empty
        """
        if not api_key or not isinstance(api_key, str):
            raise ValueError("Invalid API key")
            
        if not 0 <= confidence_threshold <= 1:
            raise ValueError("Confidence threshold must be between 0 and 1")
            
        self.confidence_threshold = confidence_threshold
        genai.configure(api_key=api_key)
        
        # Initialize the model - use fine-tuned model if provided, otherwise use base model
        self.model_name = model_name if model_name else 'gemini-2.0-flash'
        self.model = genai.GenerativeModel(self.model_name)
        
        self.temp_dir = tempfile.mkdtemp()

    def convert_to_image(self, document: io.BytesIO) -> Image.Image:
        """
        Convert a single PDF document (as BytesIO) to an image.
        
        Args:
            document (io.BytesIO): BytesIO object containing the PDF data
            
        Returns:
            Image.Image: Image of the document
            
        Raises:
            ValueError: If document conversion fails
            TypeError: If document is not a BytesIO object
        """
        if not isinstance(document, io.BytesIO):
            raise TypeError("document must be a BytesIO object")
        
        try:
            # Convert PDF to image
            images = convert_from_bytes(document.read())
            if not images:
                raise ValueError("No pages found in PDF")
            # For now, just return the first page
            return images[0]
            
        except Exception as e:
            raise ValueError(f"Error converting document to image: {str(e)}")

    def verify_document(self, document: io.BytesIO) -> VerificationResult:
        """
        Verify if the document is a purchase order and return confidence score.
        
        Args:
            document (io.BytesIO): Document in BytesIO format
            
        Returns:
            VerificationResult: Result of the verification
            
        Raises:
            ValueError: If verification fails
            TypeError: If document is not a BytesIO object
        """
        
        image = self.convert_to_image(document)
        if not isinstance(image, Image.Image):
            raise TypeError("image must be a PIL Image")
            
        try:
            prompt = """
            Analyze this image and determine if it is a purchase order.
            Consider the following characteristics:
            1. Presence of purchase order number
            2. Item listings with quantities and prices
            3. Vendor/supplier information
            5. Total amount
            
            Return a JSON response with:
            {
                "is_purchase_order": boolean,
                "confidence": number between 0 and 1,
                "reason": "explanation of your decision"
            }
            
            Instructions:
            1. Analyze the image and determine if it is a purchase order
            2. If it is a purchase order, return True for is_purchase_order
            3. If it is not a purchase order, return False for is_purchase_order
            4. Return a confidence score between 0 and 1
            5. Return an explanation for your decision
            6. Just return the JSON response, do not include any other text or explanations
            7. Do not include any tags like ```json or ``` in your response.
            """
            
            response = self.model.generate_content([prompt, image])
            content = response.text.strip()
            
            # Remove any markdown code block markers
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"Raw response from Gemini: {content}")
                raise ValueError(f"Invalid JSON response from Gemini: {str(e)}")
            
            # Validate required fields
            required_fields = ["is_purchase_order", "confidence", "reason"]
            missing_fields = [field for field in required_fields if field not in result]
            if missing_fields:
                raise ValueError(f"Missing required fields in response: {missing_fields}")
            
            # Validate confidence is a number between 0 and 1
            if not isinstance(result["confidence"], (int, float)) or not 0 <= result["confidence"] <= 1:
                raise ValueError("Confidence must be a number between 0 and 1")
            
            # Validate is_purchase_order is a boolean
            if not isinstance(result["is_purchase_order"], bool):
                raise ValueError("is_purchase_order must be a boolean")
            
            # Validate reason is a string
            if not isinstance(result["reason"], str):
                raise ValueError("reason must be a string")
            
            return VerificationResult(**result)
            
        except Exception as e:
            print(f"Error in verification: {str(e)}")
            # Return a default low-confidence result instead of raising an error
            return VerificationResult(
                is_purchase_order=False,
                confidence=0.0,
                reason=f"Verification failed: {str(e)}"
            )

    def extract_items(self, document: io.BytesIO) -> List[Dict[str, Any]]:
        """
        Extract items from the purchase order using Gemini model.
        
        Args:
            document (io.BytesIO): Document in BytesIO format
            
        Returns:
            List[Dict[str, Any]]: Extracted and validated items
            
        Raises:
            ValueError: If extraction or validation fails
            TypeError: If document is not a BytesIO object
        """
        
        image = self.convert_to_image(document)
        
        if not isinstance(image, Image.Image):
            raise TypeError("image must be a PIL Image")
            
        try:
            # Create the prompt
            prompt = """
            Input Image:
            
            Now, please analyze this purchase order and extract all items in the following format:
            [
                {
                    "item": { "id": "string" },
                    "quantity": number,
                    "rate": number
                }
            ]
            
            Important:
            1. Return ONLY a valid JSON array
            2. Each item must have an id and quantity
            3. Some IDs might contain multiple periods like 105415.1000.1000. Add the complete IDs with all the periods.
            4. All IDs must be returned as strings (enclosed in quotes)
            5. Do not include any additional text or explanations
            6. In the quantity field, I want the unit quantity, so if the quantity is 2 and there are 100 units in the unit, then the quantity should be 200
            7. Validate that the ID is complete and correct before including it
            8. If no items are found, return an empty array: []
            9. If quantity is not available, use 0 as the default value
            10. If rate is not available, use null
            
            **Very Important:** Some entries in the item field there may have multiple numbers, so include only one per item entry.
            """
            
            # Generate content with the model
            try:
                response = self.model.generate_content([prompt, image])
            except Exception as e:
                raise ValueError(f"Error generating content with Gemini: {str(e)}")
            
            # Parse and return items
            try:
                content = response.text.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                # Parse JSON response
                try:
                    items = json.loads(content)
                except json.JSONDecodeError as e:
                    print(f"Raw response from Gemini: {content}")
                    raise ValueError(f"Invalid JSON response from Gemini: {str(e)}")
                
                # Ensure items is a list
                if not isinstance(items, list):
                    items = [items] if items else []
                
                # Pre-process items before validation
                processed_items = []
                for item in items:
                    try:
                        # Skip if item is not a dictionary
                        if not isinstance(item, dict):
                            continue
                            
                        # Skip if item doesn't have required fields
                        if 'item' not in item or not isinstance(item['item'], dict) or 'id' not in item['item']:
                            continue
                            
                        # Create processed item with default values
                        processed_item = {
                            'item': {
                                'id': str(item['item']['id']).strip()
                            },
                            'quantity': 0,
                            'rate': None
                        }
                        
                        # Handle quantity
                        if 'quantity' in item:
                            quantity = item['quantity']
                            if isinstance(quantity, (int, float)):
                                processed_item['quantity'] = int(quantity)
                            elif isinstance(quantity, str):
                                try:
                                    processed_item['quantity'] = int(float(quantity))
                                except (ValueError, TypeError):
                                    pass
                                    
                        # Handle rate
                        if 'rate' in item:
                            rate = item['rate']
                            if rate is not None:
                                if isinstance(rate, (int, float)):
                                    processed_item['rate'] = float(rate)
                                elif isinstance(rate, str):
                                    try:
                                        processed_item['rate'] = float(rate)
                                    except:
                                        processed_item['rate'] = None
                                # Ensure rate is positive
                                if processed_item['rate'] is not None and processed_item['rate'] <= 0:
                                    processed_item['rate'] = None
                            else:
                                processed_item['rate'] = None
                                
                        # Only add items with valid IDs
                        if processed_item['item']['id']:
                            processed_items.append(processed_item)
                            
                    except Exception as e:
                        print(f"Error processing item: {str(e)}")
                        continue
                
                return processed_items
                
            except Exception as e:
                raise ValueError(f"Error parsing response: {str(e)}")
            
        except Exception as e:
            raise ValueError(f"Error extracting items: {str(e)}")

    def process_document(self, document: io.BytesIO) -> Tuple[Optional[List[Dict[str, Any]]], Optional[VerificationResult]]:
        """
        Process a single document and extract purchase order items.
        
        Args:
            document (io.BytesIO): Document in BytesIO format
            
        Returns:
            Tuple[Optional[List[Dict[str, Any]]], Optional[VerificationResult]]: 
                - List of items if successful, None if there was an error
                - Verification result if successful, None if there was an error
        """
        if not isinstance(document, io.BytesIO):
            raise TypeError("document must be a BytesIO object")
            
        try:
            # Verify if it's a purchase order
            verification = self.verify_document(document)
            
            # Only proceed with extraction if confidence is above threshold
            if verification.is_purchase_order and verification.confidence >= self.confidence_threshold:
                items = self.extract_items(document)
                return items, verification
            else:
                return None, verification
            
        except Exception as e:
            print(f"Error processing document: {str(e)}")
            return None, None

    def __del__(self):
        """Clean up temporary files when the object is destroyed."""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
        except:
            pass 