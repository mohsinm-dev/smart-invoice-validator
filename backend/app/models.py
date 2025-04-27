from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(String(36), primary_key=True, index=True)
    supplier_name = Column(String(255), nullable=False)
    services = Column(JSON, nullable=False)  # Store services as JSON array
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    
    invoices = relationship("Invoice", back_populates="contract", cascade="all, delete-orphan")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, index=True)
    contract_id = Column(String(36), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=True)
    invoice_number = Column(String(255), nullable=False)
    supplier_name = Column(String(255), nullable=False)
    issue_date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    items = Column(JSON, nullable=False)  # Store items as JSON array
    subtotal = Column(Float, nullable=True)
    tax = Column(Float, nullable=True)
    total = Column(Float, nullable=False)
    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    
    contract = relationship("Contract", back_populates="invoices") 