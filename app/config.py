import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./material_inward.db")
OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() == "true"
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "").strip()

# Public PoC: allow browser clients from Vercel/preview aliases without
# requiring a matching Render environment variable. No credentials/cookies
# are used by this API. Restrict this to explicit origins before production.
CORS_ORIGINS = ["*"]
