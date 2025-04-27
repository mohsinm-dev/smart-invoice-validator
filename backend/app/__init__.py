from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

def create_app():
    app = FastAPI(
        title="Smart Invoice Platform API",
        description="API for managing contracts and processing invoices",
        version="0.1.0"
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    from app.api.routes import api_router
    app.include_router(api_router, prefix=settings.API_PREFIX) 
    
    @app.get("/")
    def root():
        return {"message": "Welcome to Smart Invoice Platform API"}
    
    return app