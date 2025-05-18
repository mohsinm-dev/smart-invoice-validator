import os
import json
import re
from typing import Dict, Optional, List, Tuple, Any
from datetime import date, datetime
import google.generativeai as genai
from pdf2image import convert_from_bytes
from PIL import Image
from pathlib import Path
import io
from loguru import logger
from pydantic import ValidationError
from ..config import settings
from ..models.document_models import (
    ExtractedInvoiceModel,
    ExtractedContractModel,
    InvoiceItemModel
)
from .constants import (
    EXTRACT_INVOICE_DATA_PROMPT,
    EXTRACT_CONTRACT_DATA_PROMPT,
    EXTRACT_SERVICES_PROMPT,
    PROCESS_INVOICE_PROMPT,
    UNIFIED_DOCUMENT_ITEM_EXTRACTION_PROMPT,
    SUPPORTED_DOCUMENT_FILE_TYPES,
    SUPPORTED_INVOICE_FILE_TYPES
)

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel(settings.GEMINI_MODEL)

class DocumentProcessor:
    """Process and extract data from invoice documents."""
    
    def __init__(self):
        self.model = model
        logger.info("DocumentProcessor initialized with Gemini model")
    
    def process_document(self, file_content: bytes, file_name: str) -> Optional[ExtractedInvoiceModel]:
        """
        Process a document file and extract its data.
        
        Args:
            file_content: The binary content of the file
            file_name: The name of the file
            
        Returns:
            Extracted data as an ExtractedInvoiceModel or None if an error occurs.
        """
        logger.info(f"Processing document: {file_name}")
        extracted_model: Optional[ExtractedInvoiceModel] = None
        
        file_ext = Path(file_name).suffix.lower()

        if file_ext not in SUPPORTED_DOCUMENT_FILE_TYPES:
            logger.error(f"Unsupported file format: {file_name}")
            # Instead of returning a dict, we could raise an error or return None
            # For consistency, let's aim to return None or the model
            return None

        try:
            if file_ext == '.pdf':
                logger.info("Converting PDF to images")
                images = self._convert_pdf_to_images(file_content)
                if not images:
                    logger.error("Failed to convert PDF to images")
                    return None
                
                image_bytes = self._get_image_bytes(images[0])
                if not image_bytes:
                    logger.error("Failed to convert image to bytes")
                    return None
                
                extracted_model = self._extract_data_from_image(image_bytes)
            
            elif file_ext in ['.jpg', '.jpeg', '.png']:
                logger.info("Processing image file directly")
                extracted_model = self._extract_data_from_image(file_content)
            
        except Exception as e:
            logger.error(f"Error processing document ({file_name}): {str(e)}")
            return None # Return None on error
            
        return extracted_model
    
    def process_contract(self, file_content: bytes, file_name: str) -> Optional[ExtractedContractModel]:
        """
        Process a contract document file and extract services and supplier information.
        
        Args:
            file_content: The binary content of the file
            file_name: The name of the file
            
        Returns:
            Extracted contract data as ExtractedContractModel or None if an error occurs.
        """
        logger.info(f"Processing contract document: {file_name}")
        contract_model_data: Optional[Dict[str, Any]] = None
        file_ext = Path(file_name).suffix.lower()

        if file_ext not in SUPPORTED_DOCUMENT_FILE_TYPES:
            logger.error(f"Unsupported contract file format: {file_name}")
            return None

        try:
            if file_ext == '.pdf':
                logger.info("Converting contract PDF to images")
                images = self._convert_pdf_to_images(file_content)
                if not images:
                    logger.error("Failed to convert contract PDF to images")
                    return None
                
                image_bytes_first_page = self._get_image_bytes(images[0])
                if not image_bytes_first_page:
                    logger.error("Failed to convert contract image (first page) to bytes")
                    return None
                
                contract_model_data = self._extract_contract_data_from_image_raw(image_bytes_first_page)
                
                if contract_model_data and len(images) > 1:
                    logger.info(f"Processing {len(images) -1} additional pages for service details")
                    all_additional_services_raw: List[Dict] = [] # Store raw dicts first
                    
                    for i in range(1, len(images)):
                        page_image_bytes = self._get_image_bytes(images[i])
                        if page_image_bytes:
                            page_services_raw = self._extract_services_from_image_raw(page_image_bytes)
                            if page_services_raw and isinstance(page_services_raw, list):
                                all_additional_services_raw.extend(page_services_raw)
                    
                    if all_additional_services_raw:
                        # Transform additional services to InvoiceItemModel compatible structure
                        transformed_additional_services = [
                            {"description": s.get("service_name"), "unit_price": s.get("unit_price"), "quantity": s.get("quantity", 1.0)}
                            for s in all_additional_services_raw if s.get("service_name") and s.get("unit_price") is not None
                        ]
                        
                        if "services" not in contract_model_data or not contract_model_data["services"]:
                            contract_model_data["items"] = transformed_additional_services # Changed key to 'items'
                        elif isinstance(contract_model_data.get("services"), list):
                            # Transform existing services and extend
                            existing_services_raw = contract_model_data.pop("services") # Remove old 'services'
                            transformed_existing_services = [
                                {"description": s.get("service_name"), "unit_price": s.get("unit_price"), "quantity": s.get("quantity", 1.0)}
                                for s in existing_services_raw if s.get("service_name") and s.get("unit_price") is not None
                            ]
                            if "items" not in contract_model_data: # Ensure 'items' key exists
                                contract_model_data["items"] = []
                            contract_model_data["items"].extend(transformed_existing_services)
                            contract_model_data["items"].extend(transformed_additional_services)
                        if "services" in contract_model_data: # cleanup, should be removed by pop
                            del contract_model_data["services"]

            elif file_ext in ['.jpg', '.jpeg', '.png']:
                logger.info("Processing contract image file directly")
                contract_model_data = self._extract_contract_data_from_image_raw(file_content)
            
            else: # Should be caught by earlier check, but as a safeguard
                logger.error(f"Unsupported contract file format: {file_name}")
                return None

            if contract_model_data:
                # Add filename-derived supplier name if not found by Gemini
                if not contract_model_data.get("supplier_name"):
                    supplier_name_from_file = Path(file_name).stem.replace('_', ' ').replace('-', ' ')
                    contract_model_data["supplier_name"] = supplier_name_from_file
                    logger.info(f"Using filename as supplier name for contract: {supplier_name_from_file}")

                # Transform services in contract_model_data to items before validation
                if "services" in contract_model_data and isinstance(contract_model_data["services"], list):
                    raw_services = contract_model_data.pop("services") # Remove old 'services' key
                    transformed_items = [
                        {"description": s.get("service_name"), "unit_price": s.get("unit_price"), "quantity": s.get("quantity", 1.0)}
                        for s in raw_services if s.get("service_name") and s.get("unit_price") is not None
                    ]
                    contract_model_data["items"] = transformed_items
                elif "services" in contract_model_data: # if services is not a list or empty, remove it
                     del contract_model_data["services"]


                # Ensure 'items' field exists and is a list, even if empty
                if "items" not in contract_model_data or not isinstance(contract_model_data.get("items"), list):
                    contract_model_data["items"] = []
                    
                return ExtractedContractModel.model_validate(contract_model_data)
            return None

        except ValidationError as ve:
            logger.error(f"Pydantic validation error processing contract ({file_name}): {ve}")
            return None
        except Exception as e:
            logger.error(f"Error processing contract document ({file_name}): {str(e)}")
            return None
    
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
    
    def _parse_gemini_json_response(self, response_text: str) -> Optional[Any]:
        """Helper to parse JSON from Gemini's response text."""
        text = response_text.strip()
        
        # Handle potential markdown code blocks
        if text.startswith("```json"):
            text = text[len("```json"):].strip()
            if text.endswith("```"):
                text = text[:-len("```")].strip()
        elif text.startswith("```"):
             text = text[len("```"):].strip()
             if text.endswith("```"):
                text = text[:-len("```")].strip()
        
        parsed_data = None
        
        # Attempt to parse directly as JSON, assuming it could be an object or an array
        if text: # Ensure text is not empty after stripping
            try:
                # Determine if it's likely an object or array based on first non-whitespace char
                first_char = text.lstrip()[0] if text.lstrip() else ''
                
                if first_char == '{' or first_char == '[':
                    parsed_data = json.loads(text)
                else:
                    # If it doesn't start with { or [, it's unlikely to be valid JSON payload we expect.
                    # However, the old logic specifically looked for start/end tokens.
                    # For now, let's stick to direct parsing if it looks like JSON.
                    # If LLM includes preamble text before JSON, this direct parse might fail.
                    # The markdown stripping should handle most of that.
                    logger.warning(f"Response text after markdown stripping does not start with '{{' or '['. Attempting parse anyway. Content: '{text[:500]}'")
                    # Try parsing anyway, json.loads can be forgiving with whitespace.
                    parsed_data = json.loads(text)

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON directly from response: {e}. Content: '{text[:500]}'")
            except Exception as e_gen: # Catch any other unexpected errors during parsing attempt
                logger.error(f"Unexpected error during JSON parsing: {e_gen}. Content: '{text[:500]}'")

        if parsed_data is None:
             logger.warning(f"Could not parse any valid JSON from response after stripping markdown. Original content snippet: '{response_text[:500]}'")

        return parsed_data

    def _extract_data_from_image(self, image_bytes: bytes) -> Optional[ExtractedInvoiceModel]:
        """Extract invoice data from an image using Gemini and parse with Pydantic."""
        try:
            response = self.model.generate_content(
                [
                    EXTRACT_INVOICE_DATA_PROMPT,
                    {"mime_type": "image/png", "data": image_bytes}
                ]
            )
            raw_data = self._parse_gemini_json_response(response.text)
            if raw_data and isinstance(raw_data, dict):
                # Add raw_text if not present from Gemini for Pydantic model
                if "raw_text" not in raw_data:
                     raw_data["raw_text"] = response.text[:1000] # Store a snippet
                return ExtractedInvoiceModel.model_validate(raw_data)
            else:
                logger.warning(f"Could not parse valid dict for invoice from Gemini response. Raw: {response.text[:500]}")
                # Create a minimal model with raw_text if parsing fails
                return ExtractedInvoiceModel(raw_text=response.text)

        except ValidationError as ve:
            logger.error(f"Pydantic validation error during invoice data extraction: {ve}")
            # Optionally return a model with the error or raw_text
            return ExtractedInvoiceModel(raw_text=str(ve))
        except Exception as e:
            logger.error(f"Gemini invoice data extraction error: {str(e)}")
            return ExtractedInvoiceModel(raw_text=f"Extraction error: {str(e)}")
            
    def _extract_contract_data_from_image_raw(self, image_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Extract contract data from an image using Gemini, returns raw Dict."""
        try:
            response = self.model.generate_content(
                [
                    EXTRACT_CONTRACT_DATA_PROMPT,
                    {"mime_type": "image/png", "data": image_bytes}
                ]
            )
            
            raw_data = self._parse_gemini_json_response(response.text)
            if isinstance(raw_data, dict):
                return raw_data
            else:
                logger.warning(f"Could not parse valid dict for contract from Gemini. Raw: {response.text[:500]}")
                return {"error": "Failed to parse contract data from AI response", "raw_text": response.text}

        except Exception as e:
            logger.error(f"Gemini contract data extraction error: {str(e)}")
            return {"error": f"Error extracting data from contract document: {str(e)}"}
    
    def _extract_services_from_image_raw(self, image_bytes: bytes) -> Optional[List[Dict[str, Any]]]:
        """Extract services and pricing information from an image, returns raw List[Dict]."""
        try:
            response = self.model.generate_content(
                [
                    EXTRACT_SERVICES_PROMPT,
                    {"mime_type": "image/png", "data": image_bytes}
                ]
            )
            
            raw_services_data = self._parse_gemini_json_response(response.text)
            if isinstance(raw_services_data, list):
                # Further validation could be done here to ensure items are dicts
                return raw_services_data
            elif isinstance(raw_services_data, dict) and "services" in raw_services_data and isinstance(raw_services_data["services"], list):
                 # sometimes Gemini wraps it in a "services" key
                return raw_services_data["services"]
            else:
                logger.warning(f"Could not parse valid list of services from Gemini. Raw: {response.text[:500]}")
                return []
            
        except Exception as e:
            logger.error(f"Service extraction error: {str(e)}")
            return [] # Return empty list on error
    
    def stitch_document(self, file_content: bytes, file_type: str) -> Optional[bytes]:
        """
        Convert a document (PDF or image) to a single vertically stitched PNG image.
        If it's a PDF, all pages are stitched together.
        If it's an image, it's converted to PNG format.

        Args:
            file_content: The binary content of the file.
            file_type: The type of the file (e.g., 'pdf', 'jpg', 'png').

        Returns:
            Bytes of the single PNG image, or None if an error occurs.
        """
        logger.info(f"Stitching document of type: {file_type}")
        normalized_file_type = file_type.lower().lstrip('.')

        if normalized_file_type == 'pdf':
            try:
                images = self._convert_pdf_to_images(file_content)
                if not images:
                    logger.error("PDF conversion yielded no images for stitching.")
                    return None
                
                if len(images) == 1:
                    logger.info("Single page PDF, converting to PNG directly.")
                    return self._get_image_bytes(images[0])

                logger.info(f"Stitching {len(images)} pages from PDF.")
                # Ensure all images are in RGB mode for consistency before stitching
                rgb_images = []
                for img in images:
                    if img.mode == 'RGBA':
                        # Create a white background image
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        # Paste the RGBA image onto the white background
                        background.paste(img, mask=img.split()[3]) # Use alpha channel as mask
                        rgb_images.append(background)
                    elif img.mode == 'P': # Palette mode
                        rgb_images.append(img.convert('RGB'))
                    elif img.mode != 'RGB':
                        rgb_images.append(img.convert('RGB'))
                    else:
                        rgb_images.append(img)
                
                images = rgb_images # Use the converted images

                max_width = max(img.width for img in images)
                total_height = sum(img.height for img in images)
                
                stitched_image = Image.new('RGB', (max_width, total_height), (255, 255, 255))
                
                current_y = 0
                for img in images:
                    stitched_image.paste(img, (0, current_y))
                    current_y += img.height
                
                return self._get_image_bytes(stitched_image)

            except Exception as e:
                logger.error(f"Error stitching PDF document: {str(e)}")
                return None
                
        elif normalized_file_type in ['jpg', 'jpeg', 'png']:
            logger.info(f"Converting image file type '{normalized_file_type}' to PNG bytes.")
            try:
                image = Image.open(io.BytesIO(file_content))
                # Convert to RGB if it has an alpha channel or is palette based for consistency with stitched PDFs
                if image.mode == 'RGBA':
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[3])
                    image = background
                elif image.mode == 'P':
                    image = image.convert('RGB')
                elif image.mode != 'RGB': # Other modes like L (grayscale), CMYK etc.
                    image = image.convert('RGB')
                return self._get_image_bytes(image)
            except Exception as e:
                logger.error(f"Error converting image '{normalized_file_type}' to PNG: {str(e)}")
                return None
        else:
            logger.error(f"Unsupported file type for stitching: {normalized_file_type}")
            return None

    @staticmethod
    async def process_invoice(file_content: bytes, file_type: str) -> Optional[ExtractedInvoiceModel]:
        """
        Static method for backward compatibility.
        Processes an invoice file and extract relevant information.
        """
        # This static method might be called from elsewhere.
        # It now returns an Optional[ExtractedInvoiceModel]
        processor = DocumentProcessor()
        return await processor.process_invoice_async(file_content, file_type)
            
    async def process_invoice_async(self, file_content: bytes, file_type: str) -> Optional[ExtractedInvoiceModel]:
        """Process an invoice file and extract relevant information using Pydantic."""
        try:
            logger.info(f"Async processing invoice file of type: {file_type}")
            
            if not file_content:
                logger.error("Empty file content provided to process_invoice_async")
                return None # Return None for invalid input
                
            file_type_lower = file_type.lower()
            if file_type_lower not in SUPPORTED_INVOICE_FILE_TYPES:
                logger.error(f"Unsupported file type for async invoice processing: {file_type}")
                return None

            image_to_process: Optional[Image.Image] = None

            if file_type_lower in ['jpg', 'jpeg', 'png']:
                image_to_process = Image.open(io.BytesIO(file_content))
            elif file_type_lower == 'pdf':
                images = self._convert_pdf_to_images(file_content)
                if not images:
                    logger.error("Could not extract any images from PDF for async processing")
                    return None
                image_to_process = images[0]
            elif file_type_lower in ['doc', 'docx']:
                # Placeholder for doc/docx - For now, cannot process, return None or error model
                logger.warning(f"DOC/DOCX processing is not fully implemented, returning placeholder for {file_type}")
                # Return a minimal model indicating non-processing
                return ExtractedInvoiceModel(
                    invoice_number="DOC_UNPROCESSED",
                    supplier_name="DOC_UNPROCESSED",
                    raw_text="DOC/DOCX file received but not processed by vision model."
                )

            if not image_to_process:
                logger.error("No image could be prepared for Gemini processing.")
                return None

            # Send to Gemini for processing
            response = self.model.generate_content([PROCESS_INVOICE_PROMPT, image_to_process])
            
            raw_data = self._parse_gemini_json_response(response.text)

            if raw_data and isinstance(raw_data, dict):
                 # Add raw_text if not present from Gemini for Pydantic model
                if "raw_text" not in raw_data: # Pydantic model expects it
                     raw_data["raw_text"] = response.text[:1000] # Store a snippet
                
                # Add default for items if missing before validation
                if "items" not in raw_data or not isinstance(raw_data.get("items"), list):
                    raw_data["items"] = []
                
                return ExtractedInvoiceModel.model_validate(raw_data)
            else:
                logger.warning(f"Could not parse valid dict for async invoice from Gemini. Raw: {response.text[:500]}")
                return ExtractedInvoiceModel(raw_text=response.text) # Return minimal model with raw text

        except ValidationError as ve:
            logger.error(f"Pydantic validation error during async invoice processing: {ve}")
            return ExtractedInvoiceModel(raw_text=f"Validation Error: {str(ve)}")
        except Exception as e:
            logger.error(f"Error processing invoice async: {str(e)}")
            return ExtractedInvoiceModel(raw_text=f"Processing Error: {str(e)}")

    # Overload process_invoice for file path to maintain compatibility if it was used.
    # Note: The original had two `process_invoice` methods, one static (content, type)
    # and one instance (file_path).
    # The static one is kept. This one is for the instance method with file_path.
    async def process_invoice(self, file_path: str) -> Optional[ExtractedInvoiceModel]:
        """Process an invoice file from a file path."""
        try:
            logger.info(f"Processing invoice file from path: {file_path}")
            
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None # Return None if file not found
                
            file_extension = Path(file_path).suffix.lower().replace('.', '') # Get 'pdf', not '.pdf'
            if file_extension not in SUPPORTED_INVOICE_FILE_TYPES:
                logger.error(f"Unsupported file type from path: {file_extension}")
                return None
            
            with open(file_path, 'rb') as file:
                file_content = file.read()
                
            return await self.process_invoice_async(file_content, file_extension)
            
        except Exception as e:
            logger.error(f"Error processing invoice from file path '{file_path}': {str(e)}")
            # Return a minimal model indicating the error
            return ExtractedInvoiceModel(raw_text=f"File Path Processing Error: {str(e)}")