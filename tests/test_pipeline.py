from app.services.pipeline import extract_fields, normalize_fields, match_material
from app.services.validation import validate


def test_extract_and_normalize():
    text = "Manufacturer: ABC Electronics\nPart No: r10k-0603\nLot: L20260901\nQty: 5,000\nDate Code: 260901\nPO: PO-2026-00127"
    f = normalize_fields(extract_fields(text))
    assert f["part_number"] == "R10K-0603"
    assert f["lot_number"] == "L20260901"
    assert f["quantity"] == 5000
    assert f["po_number"] == "PO-2026-00127"


def test_extracts_fields_when_ocr_drops_colons():
    text = "Supplier: ABC Electronics\nPart Number RIOK 0803\nMaterial Code RES-10K 0603\nQuantity 5000\nPO Number PO-2026-00127\nLotNNumber:LOT-2026-0905-A"
    f = normalize_fields(extract_fields(text))
    assert f["quantity"] == 5000
    assert f["po_number"] == "PO-2026-00127"
    assert f["lot_number"] == "LOT-2026-0905-A"
    assert f["material_code"] == "RES-10K0603"


def test_exact_match():
    mats = [{"id":1,"material_code":"RES-10K-0603","part_number":"R10K-0603","manufacturer":"ABC ELECTRONICS","description":"10K","supplier_id":1}]
    result = match_material("R10K-0603", mats)
    assert result["score"] == 1.0
    assert result["match"]["material_code"] == "RES-10K-0603"


def test_material_code_can_rescue_noisy_part_number():
    mats = [{"id":1,"material_code":"RES-10K-0603","part_number":"R10K-0603","manufacturer":"ABC ELECTRONICS","description":"10K","supplier_id":1}]
    result = match_material("RIOK0803", mats, "RES-10K0603")
    assert result["score"] == 1.0
    assert result["match"]["material_code"] == "RES-10K-0603"
    assert result["match_basis"] == "material_code_exact"


def test_validation_passes():
    fields = {"part_number":"R10K-0603","lot_number":"L1","quantity":5000,"po_number":"PO-1"}
    material = {"id":1,"material_code":"RES","part_number":"R10K-0603","manufacturer":"ABC","supplier_id":1}
    pos = [{"id":1,"po_number":"PO-1","supplier_id":1,"material_id":1,"expected_quantity":5000,"status":"OPEN"}]
    v = validate(fields, material, pos, 0.99, 1.0)
    assert v["status"] == "VALIDATED"
    assert v["reasons"] == []


def test_validation_routes_missing_data_to_review():
    fields = {"part_number":"R10K-0603","lot_number":"","quantity":5000,"po_number":"PO-1"}
    material = {"id":1,"material_code":"RES","part_number":"R10K-0603","manufacturer":"ABC","supplier_id":1}
    pos = [{"id":1,"po_number":"PO-1","supplier_id":1,"material_id":1,"expected_quantity":5000,"status":"OPEN"}]
    v = validate(fields, material, pos, 0.99, 1.0)
    assert v["status"] == "REVIEW_REQUIRED"
    assert v["review_required"] is True
    assert "Lot number is missing" in v["reasons"]


def test_validation_routes_wrong_po_material_to_review():
    fields = {"part_number":"R10K-0603","lot_number":"L1","quantity":5000,"po_number":"PO-2"}
    material = {"id":1,"material_code":"RES","part_number":"R10K-0603","manufacturer":"ABC","supplier_id":1}
    pos = [{"id":2,"po_number":"PO-2","supplier_id":1,"material_id":99,"expected_quantity":5000,"status":"OPEN"}]
    v = validate(fields, material, pos, 0.99, 1.0)
    assert v["status"] == "REVIEW_REQUIRED"
    assert "Material does not match the purchase order" in v["reasons"]
