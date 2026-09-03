from pydantic import BaseModel, Field
from typing import Optional

class ProcessResult(BaseModel):
    uid: Optional[str] = None
    ocr_text: str
    ocr_confidence: float = Field(ge=0, le=1)
    extracted: dict
    material_match: Optional[dict] = None
    validation: dict
    persisted: bool = False

class Health(BaseModel):
    status: str
