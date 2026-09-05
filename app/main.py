import json
from datetime import datetime
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import CORS_ORIGINS
from app.db.database import get_db, init_db
from app.models.models import InwardEvent, Material, PurchaseOrder, Receipt
from app.schemas import Health, ProcessResult
from app.seed import seed
from app.services.pipeline import extract_fields, match_material, normalize_fields, run_ocr
from app.services.validation import validate

app = FastAPI(title="AI-Assisted Material Inward Intelligence", version="0.3.0")

# Hosted deployments can restrict browser access with CORS_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.on_event("startup")
def startup():
    init_db()
    seed()


def material_dict(m):
    return {
        "id": m.id,
        "material_code": m.material_code,
        "part_number": m.part_number,
        "manufacturer": m.manufacturer,
        "description": m.description,
        "supplier_id": m.supplier_id,
    }


def po_dict(p):
    return {
        "id": p.id,
        "po_number": p.po_number,
        "supplier_id": p.supplier_id,
        "material_id": p.material_id,
        "expected_quantity": p.expected_quantity,
        "status": p.status,
    }


def event_dict(event):
    return {
        "id": event.id,
        "event_type": event.event_type,
        "uid": event.uid,
        "status": event.status,
        "confidence": event.confidence,
        "payload": json.loads(event.payload),
        "created_at": event.created_at,
    }


@app.get("/health", response_model=Health)
def health():
    return {"status": "ok"}


@app.post("/demo/seed")
def reseed():
    seed()
    return {"status": "ready"}


@app.get("/materials")
def materials(db: Session = Depends(get_db)):
    return [material_dict(m) for m in db.query(Material).all()]


@app.get("/purchase-orders")
def purchase_orders(db: Session = Depends(get_db)):
    return [po_dict(p) for p in db.query(PurchaseOrder).all()]


@app.get("/receipts")
def receipts(db: Session = Depends(get_db)):
    return [
        {c.name: getattr(r, c.name) for c in Receipt.__table__.columns}
        for r in db.query(Receipt).order_by(Receipt.created_at.desc()).all()
    ]


@app.get("/receipts/{uid}")
def receipt(uid: str, db: Session = Depends(get_db)):
    r = db.query(Receipt).filter(Receipt.uid == uid).first()
    if not r:
        raise HTTPException(404, "Receipt not found")
    return {c.name: getattr(r, c.name) for c in Receipt.__table__.columns}


@app.get("/events")
def events(limit: int = 100, db: Session = Depends(get_db)):
    """Return the most recent inward audit events."""
    limit = max(1, min(limit, 500))
    rows = (
        db.query(InwardEvent)
        .order_by(InwardEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [event_dict(event) for event in rows]


@app.get("/events/{uid}")
def events_for_uid(uid: str, db: Session = Depends(get_db)):
    rows = (
        db.query(InwardEvent)
        .filter(InwardEvent.uid == uid)
        .order_by(InwardEvent.created_at.asc())
        .all()
    )
    return [event_dict(event) for event in rows]


@app.post("/inward/process", response_model=ProcessResult)
async def process_inward(
    image: UploadFile | None = File(default=None),
    ocr_text: str | None = Form(default=None),
    persist: bool = Form(default=True),
    db: Session = Depends(get_db),
):
    image_bytes = await image.read() if image else None

    try:
        ocr = run_ocr(image_bytes, ocr_text)
        extracted = normalize_fields(extract_fields(ocr.text))
        mats = [material_dict(m) for m in db.query(Material).all()]
        match = match_material(extracted.get("part_number", ""), mats)
        pos = [po_dict(p) for p in db.query(PurchaseOrder).all()]
        validation = validate(
            extracted,
            match.get("match"),
            pos,
            ocr.confidence,
            match.get("score", 0),
        )

        uid = None
        persisted = False

        # Only a fully validated material becomes a receipt/traceability identity.
        if persist and validation["status"] == "VALIDATED":
            uid = f"MAT-{datetime.utcnow():%Y%m%d}-{uuid4().hex[:8].upper()}"
            material = match["match"]
            receipt_row = Receipt(
                uid=uid,
                po_number=validation["po"]["po_number"],
                material_code=material["material_code"],
                part_number=material["part_number"],
                manufacturer=extracted.get("manufacturer", material["manufacturer"]),
                lot_number=extracted["lot_number"],
                quantity=extracted["quantity"],
                date_code=extracted.get("date_code"),
                confidence=validation["overall_confidence"],
                validation_status=validation["status"],
                review_required=0,
            )
            db.add(receipt_row)
            db.flush()
            persisted = True

            db.add(
                InwardEvent(
                    event_type="RECEIPT_CREATED",
                    uid=uid,
                    status="VALIDATED",
                    confidence=validation["overall_confidence"],
                    payload=json.dumps(
                        {
                            "po_number": validation["po"]["po_number"],
                            "material_code": material["material_code"],
                            "part_number": material["part_number"],
                            "lot_number": extracted["lot_number"],
                            "quantity": extracted["quantity"],
                        }
                    ),
                )
            )

        # Every processing attempt gets an audit event, including review cases.
        db.add(
            InwardEvent(
                event_type="INWARD_PROCESSED",
                uid=uid,
                status=validation["status"],
                confidence=validation["overall_confidence"],
                payload=json.dumps(
                    {
                        "ocr_source": ocr.source,
                        "ocr_confidence": ocr.confidence,
                        "extracted": extracted,
                        "material_match": match,
                        "validation": validation,
                        "persist_requested": persist,
                        "persisted": persisted,
                    },
                    default=str,
                ),
            )
        )
        db.commit()

        return {
            "uid": uid,
            "ocr_text": ocr.text,
            "ocr_confidence": ocr.confidence,
            "extracted": extracted,
            "material_match": match,
            "validation": validation,
            "persisted": persisted,
        }
    except (ValueError, RuntimeError) as exc:
        db.rollback()
        raise HTTPException(400, str(exc))
    except Exception:
        db.rollback()
        raise
