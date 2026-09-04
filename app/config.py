import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./material_inward.db")
OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() == "true"
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "").strip()

# Comma-separated browser origins. Keep '*' for local/demo use; restrict this in hosted environments.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]
