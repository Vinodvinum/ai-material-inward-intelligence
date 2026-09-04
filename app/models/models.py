from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True)
    supplier_code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    materials = relationship("Material", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True)
    material_code = Column(String(100), unique=True, nullable=False)
    part_number = Column(String(100), unique=True, nullable=False)
    manufacturer = Column(String(200), nullable=False)
    description = Column(String(300), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    supplier = relationship("Supplier", back_populates="materials")
    purchase_orders = relationship("PurchaseOrder", back_populates="material")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(Integer, primary_key=True)
    po_number = Column(String(100), unique=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    expected_quantity = Column(Integer, nullable=False)
    status = Column(String(30), default="OPEN", nullable=False)
    supplier = relationship("Supplier", back_populates="purchase_orders")
    material = relationship("Material", back_populates="purchase_orders")


class Receipt(Base):
    __tablename__ = "receipts"
    id = Column(Integer, primary_key=True)
    uid = Column(String(100), unique=True, nullable=False)
    po_number = Column(String(100), nullable=False)
    material_code = Column(String(100), nullable=False)
    part_number = Column(String(100), nullable=False)
    manufacturer = Column(String(200), nullable=False)
    lot_number = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    date_code = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=False)
    validation_status = Column(String(30), nullable=False)
    review_required = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class InwardEvent(Base):
    """Append-only audit event for the material-inward pipeline."""
    __tablename__ = "inward_events"
    id = Column(Integer, primary_key=True)
    event_type = Column(String(50), nullable=False)
    uid = Column(String(100), nullable=True)
    status = Column(String(30), nullable=False)
    confidence = Column(Float, nullable=False)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
