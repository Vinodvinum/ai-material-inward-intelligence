# AI-Assisted Material Inward Intelligence — PoC

A focused proof-of-concept for converting an incoming electronics-material label image into a validated, traceable digital material record.

## Scope

Image upload → preprocessing → OCR → field extraction → normalization → material matching → PO validation → confidence → human review → UID → traceability record.

This is an independent PoC aligned with the publicly visible problem space of manufacturing material inward/traceability. It is **not** Mysoreminds' internal implementation and does not use customer data.

## Architecture

- **Vercel / Next.js**: polished product-facing web UI in `web/`
- **Streamlit**: engineering/operator console in `app/ui/streamlit_app.py`
- **FastAPI**: shared backend API
- **OpenCV**: image preprocessing
- **Tesseract OCR**: OCR adapter (optional at runtime; UI also supports pasted OCR text for environments without Tesseract)
- **Rule-based extraction + RapidFuzz**: deterministic field parsing and material matching
- **SQLAlchemy**: persistence layer
- **SQLite**: local development/demo only
- **PostgreSQL**: recommended persistent database for hosted deployment

Both UIs use the same FastAPI business pipeline rather than maintaining duplicate logic.

## Local Run

```bash
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt
```

If Tesseract is installed and on PATH, OCR from images works automatically. Otherwise, paste OCR text in the Streamlit UI to exercise the rest of the pipeline.

Start API:

```bash
uvicorn app.main:app --reload --port 8000
```

Start Streamlit in another terminal:

```bash
streamlit run app/ui/streamlit_app.py
```

Start the Next.js UI:

```bash
cd web
npm install
npm run dev
```

## Streamlit Deployment

**Main Streamlit entry point:**

```text
app/ui/streamlit_app.py
```

Deploy the repository through Streamlit Community Cloud and select the above file as the Main file path.

Important: Streamlit is only the UI. It needs the FastAPI backend URL if the UI is configured to call a hosted backend. Do not deploy Streamlit itself as the FastAPI backend.

## Vercel Deployment

The Vercel application is the Next.js project under:

```text
web/
```

When importing the GitHub repository into Vercel:

1. Select `Vinodvinum/ai-material-inward-intelligence`.
2. Set **Root Directory** to `web`.
3. Framework should be detected as **Next.js**.
4. Add environment variable:

```text
NEXT_PUBLIC_API_URL=<your hosted FastAPI URL>
```

5. Deploy.

The Vercel page can load independently, but image processing requires a reachable hosted FastAPI backend. The backend must also have CORS configured to allow the Vercel domain.

## Backend Deployment

The FastAPI application entry point is:

```text
app.main:app
```

A typical production start command is:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

For hosted persistence, set:

```text
DATABASE_URL=<PostgreSQL connection string>
```

Keep SQLite for local development only.

## API

- `GET /health`
- `POST /demo/seed`
- `POST /inward/process` — multipart image + optional OCR text
- `GET /materials`
- `GET /purchase-orders`
- `GET /receipts`
- `GET /receipts/{uid}`

## Engineering Notes

The pipeline deliberately uses deterministic validation for business rules. OCR/extraction produces candidate information; it does not silently override manufacturing master data. Low-confidence or ambiguous cases are routed to human review.

This repository contains synthetic/demo data only and makes no claim to reproduce Mysoreminds' internal architecture or implementation.
