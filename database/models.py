"""
Database models for the RTX 5090 Stock Tracker
"""

import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Retailer(Base):
    """Retailer model representing online stores like Best Buy, Newegg, etc."""
    __tablename__ = 'retailers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    website = Column(String(255), nullable=False)
    active = Column(Boolean, default=True)  # Whether this retailer should be scraped
    products = relationship("Product", back_populates="retailer")
    
    def __repr__(self):
        return f"<Retailer(name='{self.name}', website='{self.website}', active={self.active})>"

class Product(Base):
    """Product model representing RTX 5090 GPUs from different manufacturers"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    retailer_id = Column(Integer, ForeignKey('retailers.id'))
    name = Column(String(255), nullable=False)
    manufacturer = Column(String(100))
    upc = Column(String(50), nullable=True, index=True)  # Added UPC field
    url = Column(String(500), nullable=False)
    description = Column(Text)
    specifications = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    retailer = relationship("Retailer", back_populates="products")
    price_history = relationship("PriceHistory", back_populates="product")
    stock_history = relationship("StockHistory", back_populates="product")
    
    def __repr__(self):
        return f"<Product(name='{self.name}', manufacturer='{self.manufacturer}')>"

class PriceHistory(Base):
    """Price history model for tracking price changes over time"""
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    price = Column(Float)
    currency = Column(String(10), default='USD')
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    product = relationship("Product", back_populates="price_history")
    
    def __repr__(self):
        return f"<PriceHistory(product_id={self.product_id}, price={self.price}, timestamp='{self.timestamp}')>"

class StockHistory(Base):
    """Stock history model for tracking stock status changes over time"""
    __tablename__ = 'stock_history'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    in_stock = Column(Boolean)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    product = relationship("Product", back_populates="stock_history")
    
    def __repr__(self):
        return f"<StockHistory(product_id={self.product_id}, in_stock={self.in_stock}, timestamp='{self.timestamp}')>"