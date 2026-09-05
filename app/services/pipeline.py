import re
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image
from rapidfuzz import process, fuzz

from app.config import OCR_ENABLED, TESSERACT_CMD

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

FIELD_PATTERNS = {
    "manufacturer": [r"manufacturer\s*[:\-]\s*(.+)", r"maker\s*[:\-]\s*(.+)"],
    "part_number": [r"part\s*(?:no|number)\s*[:\-]\s*([A-Za-z0-9._\-/]+)", r"p/?n\s*[:\-]\s*([A-Za-z0-9._\-/]+)"],
    "lot_number": [r"lot\s*(?:no|number)?\s*[:\-]\s*([A-Za-z0-9._\-/]+)"],
    "quantity": [r"qty\s*[:\-]\s*([0-9,]+)", r"quantity\s*[:\-]\s*([0-9,]+)"],
    "date_code": [r"date\s*code\s*[:\-]\s*([A-Za-z0-9._\-/]+)", r"dc\s*[:\-]\s*([A-Za-z0-9._\-/]+)"],
    "po_number": [r"(?:po|purchase\s*order)\s*(?:no|number)?\s*[:\-]\s*([A-Za-z0-9._\-/]+)"],
}


@dataclass
class OCRResult:
    text: str
    confidence: float
    source: str


def preprocess(image_bytes: bytes) -> list[np.ndarray]:
    """Create several OCR-friendly variants so labels work across lighting/layouts."""
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Invalid image")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    denoised = cv2.GaussianBlur(gray, (3, 3), 0)
    otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    adaptive = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 11
    )
    return [gray, otsu, adaptive]


def _tesseract_pass(image: np.ndarray, psm: int) -> OCRResult:
    data = pytesseract.image_to_data(
        Image.fromarray(image),
        config=f"--oem 3 --psm {psm}",
        output_type=pytesseract.Output.DICT,
    )
    words, confs = [], []
    for word, conf in zip(data["text"], data["conf"]):
        word = word.strip()
        if not word:
            continue
        words.append(word)
        try:
            value = float(conf)
            if value >= 0:
                confs.append(value / 100.0)
        except (TypeError, ValueError):
            continue

    text = " ".join(words).strip()
    confidence = sum(confs) / len(confs) if confs else 0.0
    return OCRResult(text, confidence, "tesseract")


def run_ocr(image_bytes: Optional[bytes], supplied_text: Optional[str] = None) -> OCRResult:
    if supplied_text and supplied_text.strip():
        return OCRResult(supplied_text.strip(), 1.0, "manual_ocr_text")
    if not image_bytes:
        raise ValueError("Provide an image or OCR text")
    if not OCR_ENABLED:
        raise RuntimeError("OCR is disabled")

    try:
        variants = preprocess(image_bytes)
        attempts = []
        for variant in variants:
            for psm in (6, 11, 12):
                result = _tesseract_pass(variant, psm)
                if result.text:
                    attempts.append(result)

        if not attempts:
            raise RuntimeError("Tesseract returned no readable text from the supplied image")

        # Prefer usable text first, then the highest OCR confidence.
        return max(attempts, key=lambda r: (len(r.text) > 0, r.confidence, len(r.text)))
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"OCR failed. Install Tesseract or paste OCR text. Details: {exc}")


def extract_fields(text: str) -> dict:
    normalized = re.sub(r"\s+", " ", text.replace("|", " ")).strip()
    result = {}
    for field, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, normalized, flags=re.I)
            if match:
                result[field] = match.group(1).strip().strip(".,;")
                break
    if "quantity" in result:
        try:
            result["quantity"] = int(result["quantity"].replace(",", ""))
        except ValueError:
            result["quantity"] = None
    return result


def normalize_fields(fields: dict) -> dict:
    out = dict(fields)
    for key in ("manufacturer", "part_number", "lot_number", "date_code", "po_number"):
        if out.get(key):
            out[key] = re.sub(r"\s+", "", out[key]).upper() if key != "manufacturer" else out[key].strip()
    return out


def match_material(part_number: str, materials: list[dict]) -> dict:
    if not part_number or not materials:
        return {"match": None, "score": 0.0, "candidates": []}
    choices = {m["part_number"]: m for m in materials}
    exact = choices.get(part_number.upper())
    if exact:
        return {"match": exact, "score": 1.0, "candidates": [exact]}
    matches = process.extract(part_number.upper(), list(choices), scorer=fuzz.ratio, limit=3)
    candidates = [choices[name] for name, score, _ in matches]
    best = matches[0] if matches else None
    return {"match": choices[best[0]] if best else None, "score": (best[1] / 100.0 if best else 0.0), "candidates": candidates}
