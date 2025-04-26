from fastapi import UploadFile, HTTPException, status
import os

from app.models.invoice import ExtractedInvoice
from app.services.ocr_service import extract_invoice_data
from app.utils.file_handlers import save_upload_file_temporarily, cleanup_temp_files

async def process_invoice(file: UploadFile) -> ExtractedInvoice:
    """Process uploaded invoice file using OCR"""
    temp_file_path = None
    try:
        # Save the uploaded file temporarily
        temp_file_path = await save_upload_file_temporarily(file)
        
        # Get file extension
        file_extension = os.path.splitext(file.filename)[1].lower().lstrip(".")
        
        # Extract data using OCR service
        invoice_data = await extract_invoice_data(temp_file_path, file_extension)
        
        return invoice_data
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process invoice: {str(e)}"
        )
    
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            cleanup_temp_files(temp_file_path)