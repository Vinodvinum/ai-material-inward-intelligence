import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./material_inward.db")
OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() == "true"
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "").strip()
