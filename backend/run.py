import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8009"))
    
    # Start the application
    uvicorn.run(
        "app:create_app", 
        host=host, 
        port=port, 
        reload=True,
        factory=True,
        log_level="info"
    )