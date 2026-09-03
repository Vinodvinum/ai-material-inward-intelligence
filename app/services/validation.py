def validate(fields: dict, material: dict | None, purchase_orders: list[dict], ocr_confidence: float, match_score: float) -> dict:
    checks = {}
    reasons = []
    checks["part_number_present"] = bool(fields.get("part_number"))
    checks["lot_present"] = bool(fields.get("lot_number"))
    checks["quantity_valid"] = isinstance(fields.get("quantity"), int) and fields["quantity"] > 0
    checks["material_match"] = material is not None and match_score >= 0.90
    po = next((p for p in purchase_orders if p["po_number"].upper() == str(fields.get("po_number", "")).upper()), None) if fields.get("po_number") else None
    checks["po_found"] = po is not None
    checks["po_material_match"] = bool(po and material and po["material_id"] == material["id"])
    checks["supplier_match"] = bool(po and material and po["supplier_id"] == material["supplier_id"])

    if not checks["part_number_present"]: reasons.append("Part number is missing")
    if not checks["lot_present"]: reasons.append("Lot number is missing")
    if not checks["quantity_valid"]: reasons.append("Quantity is missing or invalid")
    if not checks["material_match"]: reasons.append("Material could not be confidently matched to master data")
    if not checks["po_found"]: reasons.append("Purchase order was not found")
    if po and not checks["po_material_match"]: reasons.append("Material does not match the purchase order")
    if po and not checks["supplier_match"]: reasons.append("Supplier does not match the purchase order/material")
    if ocr_confidence < 0.90: reasons.append("OCR confidence is below the auto-validation threshold")
    if match_score < 0.90: reasons.append("Material match confidence is below the auto-validation threshold")

    hard_pass = all(checks.values())
    overall_confidence = min(ocr_confidence, match_score)
    review_required = (not hard_pass) or overall_confidence < 0.90

    # PoC policy: unresolved validation failures are routed to human review rather than silently rejected.
    status = "VALIDATED" if hard_pass and not review_required else "REVIEW_REQUIRED"
    return {
        "checks": checks,
        "po": po,
        "overall_confidence": overall_confidence,
        "review_required": review_required,
        "status": status,
        "reasons": reasons,
    }
