# Phase 4 Build Notes

## Implemented
- FastAPI service with health, seed, master-data and inward-processing endpoints
- Streamlit operator UI
- OpenCV preprocessing
- Tesseract OCR adapter with manual OCR-text fallback
- Regex-based structured field extraction
- Field normalization
- Exact/fuzzy material matching
- Deterministic PO/material/supplier/quantity validation
- Confidence and human-review routing
- UID generation for validated receipts
- SQLite persistence via SQLAlchemy
- PostgreSQL-ready DATABASE_URL configuration
- Automated tests for extraction, matching and validation

## Deliberate limitations
- Demo master data is synthetic.
- OCR is not an AI/LLM model; extraction is deterministic for PoC reliability.
- No real ERP/MES or machine integration.
- No production authentication/authorization yet.
- No actual Mysoreminds customer data or internal code.
