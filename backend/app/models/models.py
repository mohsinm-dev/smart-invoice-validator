from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(String(36), primary_key=True, index=True)
    supplier_name = Column(String, index=True)
    items = Column(JSON)  # Store items as JSON array
    document_path = Column(String, nullable=True)  # Path to uploaded document
    is_manual = Column(Boolean, default=False)  # Whether contract was manually entered
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    invoices = relationship("Invoice", back_populates="contract")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, index=True)
    contract_id = Column(String(36), ForeignKey("contracts.id"), nullable=True)
    supplier_name = Column(String, index=True)
    items = Column(JSON)  # Store line items as JSON
    document_path = Column(String)  # Path to uploaded document
    is_valid = Column(Boolean, default=False)  # Whether document is a valid invoice
    validation_message = Column(String, nullable=True)  # Message from validation
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contract = relationship("Contract", back_populates="invoices") 