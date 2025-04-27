import os
import shutil
import tempfile
import subprocess
import re
import json
from datetime import date
from typing import Optional, List
import google.generativeai as genai
from PIL import Image
from pdf2image import convert_from_bytes

from app.models.invoice import ExtractedInvoice, InvoiceItem
from app.config import settings

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel(settings.GEMINI_MODEL)

async def extract_invoice_data(file_path: str, file_extension: str) -> ExtractedInvoice:
    """
    Extract structured data from an invoice file using Gemini,
    with robust handling for PDF rasterization and parsing errors.
    """
    # Resolve and validate the file path
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Invoice file not found: {file_path}")

    # Ensure Poppler utilities are available
    try:
        subprocess.run(["pdfinfo", "-h"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        raise EnvironmentError(
            "Poppler utilities not found. Please install poppler-utils (Linux), "
            "brew install poppler (macOS), or download Poppler for Windows and add to PATH."
        )

    try:
        # Convert PDF to image
        images = convert_from_bytes(open(file_path, 'rb').read())
        if not images:
            raise RuntimeError("No pages found in PDF")
        
        # For now, just process the first page
        image = images[0]
        
        # Create the prompt for Gemini
        prompt = """
        Analyze this image and extract the following information from the invoice:
        1. Invoice number
        2. Supplier name
        3. Issue date
        4. Due date (if available)
        5. Line items with:
           - Description
           - Quantity
           - Unit price
           - Total price
        6. Total amount
        
        Return the data in this JSON format:
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
            "total": number
        }
        
        Instructions:
        1. Extract all available information
        2. Use null for missing fields
        3. Format dates as YYYY-MM-DD
        4. Return only the JSON, no additional text
        """
        
        # Get response from Gemini
        response = model.generate_content([prompt, image])
        content = response.text.strip()
        
        # Parse the JSON response
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from Gemini: {str(e)}")
        
        # Convert the data to ExtractedInvoice
        return ExtractedInvoice(
            invoice_number=data.get("invoice_number", "Unknown"),
            supplier_name=data.get("supplier_name", "Unknown"),
            issue_date=date.fromisoformat(data.get("issue_date", date.today().isoformat())),
            due_date=date.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            items=[
                InvoiceItem(
                    description=item["description"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    total_price=item.get("total_price", item["quantity"] * item["unit_price"])
                )
                for item in data.get("items", [])
            ],
            total=data.get("total", 0.0),
            raw_text=content
        )

    except Exception as e:
        raise RuntimeError(f"Error in invoice processing: {str(e)}")
