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
    "manufacturer": [r"manufacturer\s*(?:[:\-]\s*|\s+)([^\n]+)", r"maker\s*(?:[:\-]\s*|\s+)([^\n]+)"],
    "part_number": [r"part\s*(?:no|number)\s*(?:[:\-]\s*|\s+)([A-Za-z0-9._\-/]+(?:\s+[A-Za-z0-9._\-/]+)?)", r"p/?n\s*(?:[:\-]\s*|\s+)([A-Za-z0-9._\-/]+(?:\s+[A-Za-z0-9._\-/]+)?)"],
    "material_code": [r"material\s*(?:code|no|number)\s*(?:[:\-]\s*|\s+)([A-Za-z0-9._\-/]+(?:\s+[A-Za-z0-9._\-/]+)?)"],
    "lot_number": [r"lot\s*(?:no|number)?\s*(?:[:\-]\s+|[:\-]|\s+)([A-Za-z0-9._\-/]+)", r"lotnnumber\s*(?:[:\-]\s*|\s+)([A-Za-z0-9._\-/]+)"],
    "quantity": [r"(?:qty|quantity)\s*(?:[:\-]\s*|\s+)([0-9,]+)"],
    "date_code": [r"date\s*code\s*(?:[:\-]\s*|\s+)([A-Za-z0-9._\-/]+)", r"dc\s*(?:[:\-]\s*|\s+)([A-Za-z0-9._\-/]+)"],
    "po_number": [r"(?:po|purchase\s*order)\s*(?:no|number)?\s*(?:[:\-]\s*|\s+)([A-Za-z0-9._\-/]+)"],
}


@dataclass
class OCRResult:
    text: str
    confidence: float
    source: str


def preprocess(image_bytes: bytes) -> list[np.ndarray]:
    """Create OCR-friendly variants for common label lighting/layout conditions."""
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Invalid image")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    denoised = cv2.GaussianBlur(clahe, (3, 3), 0)
    otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    adaptive = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)
    return [gray, clahe, otsu, adaptive]


def _data_ocr(image: np.ndarray, psm: int) -> OCRResult:
    data = pytesseract.image_to_data(
        Image.fromarray(image),
        config=f"--oem 3 --psm {psm}",
        output_type=pytesseract.Output.DICT,
    )
    words, confs = [], []
    for word, conf in zip(data.get("text", []), data.get("conf", [])):
        word = str(word).strip()
        if not word:
            continue
        words.append(word)
        try:
            value = float(conf)
            if value >= 0:
                confs.append(value / 100.0)
        except (TypeError, ValueError):
            continue
    return OCRResult(" ".join(words).strip(), sum(confs) / len(confs) if confs else 0.0, "tesseract_data")


def _text_ocr(image: np.ndarray, psm: int) -> OCRResult:
    text = pytesseract.image_to_string(Image.fromarray(image), config=f"--oem 3 --psm {psm}").strip()
    return OCRResult(text, 0.0, "tesseract_text")


def run_ocr(image_bytes: Optional[bytes], supplied_text: Optional[str] = None) -> OCRResult:
    if supplied_text and supplied_text.strip():
        return OCRResult(supplied_text.strip(), 1.0, "manual_ocr_text")
    if not image_bytes:
        raise ValueError("Provide an image or OCR text")
    if not OCR_ENABLED:
        raise RuntimeError("OCR is disabled")

    try:
        variants = preprocess(image_bytes)
        data_attempts: list[OCRResult] = []
        text_attempts: list[OCRResult] = []
        for variant in variants:
            for psm in (6, 11, 12):
                data_result = _data_ocr(variant, psm)
                if data_result.text:
                    data_attempts.append(data_result)
                text_result = _text_ocr(variant, psm)
                if text_result.text:
                    text_attempts.append(text_result)

        if not data_attempts and not text_attempts:
            raise RuntimeError("Tesseract returned no readable text from the supplied image")

        best_data = max(data_attempts, key=lambda r: (r.confidence, len(r.text)), default=None)
        best_text = max(text_attempts, key=lambda r: (len(r.text), r.confidence), default=None)
        text = best_text.text if best_text else best_data.text
        confidence = best_data.confidence if best_data else 0.0
        return OCRResult(text, confidence, "tesseract_hybrid")
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"OCR failed. Install Tesseract or paste OCR text. Details: {exc}")


def extract_fields(text: str) -> dict:
    cleaned = text.replace("|", " ")
    result = {}
    for field, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, cleaned, flags=re.I)
            if match:
                value = match.group(1).strip().strip(".,;")
                value = re.split(r"\s+(?=(?:manufacturer|maker|part\s*(?:no|number)|material\s*(?:code|no|number)|lot(?:\s*(?:no|number))?|qty|quantity|date\s*code|dc|po|purchase\s*order)\b)", value, maxsplit=1, flags=re.I)[0]
                result[field] = value
                break
    if "quantity" in result:
        try:
            result["quantity"] = int(result["quantity"].replace(",", ""))
        except ValueError:
            result["quantity"] = None
    return result


def normalize_fields(fields: dict) -> dict:
    out = dict(fields)
    for key in ("manufacturer", "part_number", "material_code", "lot_number", "date_code", "po_number"):
        if out.get(key):
            out[key] = re.sub(r"\s+", "", str(out[key])).upper() if key != "manufacturer" else str(out[key]).strip()
    return out


def _canonical_code(value: str | None) -> str:
    """Normalize separators/spaces so OCR variants such as RES-10K0603 match RES-10K-0603."""
    if not value:
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def match_material(part_number: str, materials: list[dict], material_code: str | None = None) -> dict:
    if not materials:
        return {"match": None, "score": 0.0, "candidates": []}

    if material_code:
        code = _canonical_code(material_code)
        exact_code = next(
            (m for m in materials if _canonical_code(str(m.get("material_code", ""))) == code),
            None,
        )
        if exact_code:
            return {"match": exact_code, "score": 1.0, "candidates": [exact_code], "match_basis": "material_code_exact"}

    if not part_number:
        return {"match": None, "score": 0.0, "candidates": []}

    choices = {m["part_number"]: m for m in materials}
    exact = choices.get(part_number.upper())
    if exact:
        return {"match": exact, "score": 1.0, "candidates": [exact], "match_basis": "part_number_exact"}

    matches = process.extract(part_number.upper(), list(choices), scorer=fuzz.ratio, limit=3)
    candidates = [choices[name] for name, score, _ in matches]
    best = matches[0] if matches else None
    return {
        "match": choices[best[0]] if best else None,
        "score": (best[1] / 100.0 if best else 0.0),
        "candidates": candidates,
        "match_basis": "part_number_fuzzy" if best else None,
    }
