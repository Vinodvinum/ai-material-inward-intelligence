# AI-Assisted Material Inward Intelligence — PoC

A focused proof-of-concept for converting an incoming electronics-material label image into a validated, traceable digital material record.

## Scope

Image upload → preprocessing → OCR → field extraction → normalization → material matching → PO validation → confidence → human review → UID → traceability record.

This is an independent PoC aligned with the publicly visible problem space of manufacturing material inward/traceability. It is **not** Mysoreminds' internal implementation and does not use customer data.

## Architecture

- **Streamlit**: operator UI
- **FastAPI**: backend API
- **OpenCV**: image preprocessing
- **Tesseract OCR**: OCR adapter (optional at runtime; UI also supports pasted OCR text for environments without Tesseract)
- **Rule-based extraction + RapidFuzz**: deterministic field parsing and material matching
- **SQLAlchemy**: persistence layer
- **SQLite by default**: easy local demo; can be switched to PostgreSQL with `DATABASE_URL`

## Run

```bash
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt
```

If Tesseract is installed and on PATH, OCR from images works automatically. Otherwise, paste OCR text in the UI to exercise the rest of the pipeline.

Start API:

```bash
uvicorn app.main:app --reload --port 8000
```

Start UI in another terminal:

```bash
streamlit run app/ui/streamlit_app.py
```

Open the URLs printed by the commands.

## Demo data

The app seeds sample suppliers, materials and purchase orders on first run. You can also use the API endpoint `/demo/seed`.

## API

- `GET /health`
- `POST /demo/seed`
- `POST /inward/process` — multipart image + optional OCR text
- `GET /materials`
- `GET /purchase-orders`
- `GET /receipts`
- `GET /receipts/{uid}`

## Engineering notes

The pipeline deliberately uses deterministic validation for business rules. AI/OCR produces candidate information; it does not silently override manufacturing master data. Low-confidence or ambiguous cases are routed to human review.
