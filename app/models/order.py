from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    
    # Order details
    order_number = Column(String(100), unique=True, nullable=False)
    content_type = Column(String(100), nullable=False)  # 'portrait', 'video', 'ar_content'
    
    # Status tracking
    status = Column(String(50), default="pending")  # pending, processing, completed, cancelled
    payment_status = Column(String(50), default="unpaid")  # unpaid, paid, refunded
    
    # Financial information
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="USD")
    
    # Subscription information
    subscription_end = Column(DateTime)
    
    # Additional information
    description = Column(Text)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    company = relationship("Company", backref="orders")
    client = relationship("Client", backref="orders")