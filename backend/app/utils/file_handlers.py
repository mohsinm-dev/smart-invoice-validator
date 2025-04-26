import os
import magic
from fastapi import UploadFile, HTTPException, status
from app.config import ALLOWED_EXTENSIONS, TEMP_DIR

async def save_upload_file_temporarily(upload_file: UploadFile) -> str:
    """Save an upload file temporarily and return the path"""
    try:
        # Read a chunk of the file to detect its mime type
        chunk = await upload_file.read(2048)
        mime = magic.Magic(mime=True)
        mime_type = mime.from_buffer(chunk)
        
        # Reset file pointer
        await upload_file.seek(0)
        
        # Validate mime type
        if not mime_type.startswith(('application/pdf', 'image/')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {mime_type}"
            )
        
        # Get file extension
        file_ext = os.path.splitext(upload_file.filename)[1].lower().lstrip('.')
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file extension: {file_ext}"
            )
        
        # Generate a temporary file path
        temp_file_path = os.path.join(TEMP_DIR, f"{os.urandom(16).hex()}.{file_ext}")
        
        # Save the file
        with open(temp_file_path, "wb") as temp_file:
            # Copy file content in chunks
            await upload_file.seek(0)
            while content := await upload_file.read(1024 * 1024):  # 1MB chunks
                temp_file.write(content)
        
        return temp_file_path
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {str(e)}"
        )
    finally:
        if upload_file:
            await upload_file.close()

def cleanup_temp_files(file_path: str) -> None:
    """Remove temporary files"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning up temporary file {file_path}: {e}")