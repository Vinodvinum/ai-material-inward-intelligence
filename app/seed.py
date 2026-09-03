from app.db.database import SessionLocal, init_db
from app.models.models import Supplier, Material, PurchaseOrder

def seed():
    init_db()
    db = SessionLocal()
    try:
        if db.query(Supplier).count(): return
        s1 = Supplier(supplier_code="SUP-001", name="ABC Electronics")
        s2 = Supplier(supplier_code="SUP-002", name="Global Components")
        db.add_all([s1, s2]); db.flush()
        m1 = Material(material_code="RES-10K-0603", part_number="R10K-0603", manufacturer="ABC ELECTRONICS", description="10K Ohm resistor, 0603", supplier_id=s1.id)
        m2 = Material(material_code="CAP-100N-0603", part_number="C100N-0603", manufacturer="GLOBAL COMPONENTS", description="100nF capacitor, 0603", supplier_id=s2.id)
        m3 = Material(material_code="IC-STM32-001", part_number="STM32F103C8T6", manufacturer="ST MICRO", description="MCU", supplier_id=s1.id)
        db.add_all([m1,m2,m3]); db.flush()
        db.add_all([
            PurchaseOrder(po_number="PO-2026-00127", supplier_id=s1.id, material_id=m1.id, expected_quantity=5000),
            PurchaseOrder(po_number="PO-2026-00128", supplier_id=s2.id, material_id=m2.id, expected_quantity=3000),
            PurchaseOrder(po_number="PO-2026-00129", supplier_id=s1.id, material_id=m3.id, expected_quantity=1000),
        ])
        db.commit()
    finally:
        db.close()
