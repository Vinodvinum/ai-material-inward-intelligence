from datetime import datetime
from uuid import uuid4
from fastapi import Depends, FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.db.database import get_db, init_db
from app.models.models import Material, PurchaseOrder, Receipt
from app.schemas import Health, ProcessResult
from app.seed import seed
from app.services.pipeline import run_ocr, extract_fields, normalize_fields, match_material
from app.services.validation import validate

app = FastAPI(title="AI-Assisted Material Inward Intelligence", version="0.2.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db(); seed()

def material_dict(m):
    return {"id": m.id, "material_code": m.material_code, "part_number": m.part_number, "manufacturer": m.manufacturer, "description": m.description, "supplier_id": m.supplier_id}

def po_dict(p):
    return {"id": p.id, "po_number": p.po_number, "supplier_id": p.supplier_id, "material_id": p.material_id, "expected_quantity": p.expected_quantity, "status": p.status}

@app.get("/health", response_model=Health)
def health(): return {"status": "ok"}

@app.post("/demo/seed")
def reseed(): seed(); return {"status": "ready"}

@app.get("/materials")
def materials(db: Session = Depends(get_db)):
    return [material_dict(m) for m in db.query(Material).all()]

@app.get("/purchase-orders")
def purchase_orders(db: Session = Depends(get_db)):
    return [po_dict(p) for p in db.query(PurchaseOrder).all()]

@app.get("/receipts")
def receipts(db: Session = Depends(get_db)):
    return [{c.name: getattr(r,c.name) for c in Receipt.__table__.columns} for r in db.query(Receipt).order_by(Receipt.created_at.desc()).all()]

@app.get("/receipts/{uid}")
def receipt(uid: str, db: Session = Depends(get_db)):
    r = db.query(Receipt).filter(Receipt.uid == uid).first()
    if not r: raise HTTPException(404, "Receipt not found")
    return {c.name: getattr(r,c.name) for c in Receipt.__table__.columns}

@app.post("/inward/process", response_model=ProcessResult)
async def process_inward(image: UploadFile | None = File(default=None), ocr_text: str | None = Form(default=None), persist: bool = Form(default=True), db: Session = Depends(get_db)):
    image_bytes = await image.read() if image else None
    try:
        ocr = run_ocr(image_bytes, ocr_text)
        extracted = normalize_fields(extract_fields(ocr.text))
        mats = [material_dict(m) for m in db.query(Material).all()]
        match = match_material(extracted.get("part_number", ""), mats)
        pos = [po_dict(p) for p in db.query(PurchaseOrder).all()]
        validation = validate(extracted, match.get("match"), pos, ocr.confidence, match.get("score",0))
        uid = None
        persisted = False
        if persist and validation["status"] == "VALIDATED":
            uid = f"MAT-{datetime.utcnow():%Y%m%d}-{uuid4().hex[:8].upper()}"
            m = match["match"]
            r = Receipt(uid=uid, po_number=validation["po"]["po_number"], material_code=m["material_code"], part_number=m["part_number"], manufacturer=extracted.get("manufacturer",m["manufacturer"]), lot_number=extracted["lot_number"], quantity=extracted["quantity"], date_code=extracted.get("date_code"), confidence=validation["overall_confidence"], validation_status=validation["status"], review_required=0)
            db.add(r); db.commit(); persisted = True
        return {"uid":uid,"ocr_text":ocr.text,"ocr_confidence":ocr.confidence,"extracted":extracted,"material_match":match,"validation":validation,"persisted":persisted}
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc))
