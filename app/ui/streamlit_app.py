import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
st.set_page_config(page_title="Material Inward Intelligence", layout="wide")
st.title("AI-Assisted Material Inward Intelligence")
st.caption("Independent PoC: capture → OCR → extract → map → validate → UID → traceability")

with st.sidebar:
    st.header("System")
    st.write(f"API: `{API_URL}`")
    try:
        r = requests.get(f"{API_URL}/health", timeout=3)
        st.success("Backend connected" if r.ok else "Backend error")
    except Exception:
        st.error("Start FastAPI first")

st.subheader("1. Capture incoming material")
upload = st.file_uploader("Upload a material label image", type=["png","jpg","jpeg"])
ocr_text = st.text_area("Optional: paste OCR text (useful if Tesseract is not installed)", height=150, placeholder="Manufacturer: ABC Electronics\nPart No: R10K-0603\nLot: L20260901\nQty: 5000\nDate Code: 260901\nPO: PO-2026-00127")

if upload:
    st.image(upload, caption="Uploaded label", width=500)

if st.button("Process Material", type="primary", disabled=not (upload or ocr_text.strip())):
    files = {"image": (upload.name, upload.getvalue(), upload.type)} if upload else None
    data = {"ocr_text": ocr_text, "persist": "true"}
    with st.spinner("Processing..."):
        try:
            resp = requests.post(f"{API_URL}/inward/process", files=files, data=data, timeout=60)
            if not resp.ok:
                st.error(resp.text); st.stop()
            result = resp.json()
        except Exception as exc:
            st.error(f"Request failed: {exc}"); st.stop()

    st.subheader("2. Extraction")
    c1,c2,c3 = st.columns(3)
    c1.metric("OCR confidence", f"{result['ocr_confidence']*100:.1f}%")
    c2.metric("Match score", f"{result['material_match']['score']*100:.1f}%")
    c3.metric("Validation", result['validation']['status'])

    st.write("**Extracted fields**")
    st.json(result["extracted"])
    st.write("**OCR text**")
    st.code(result["ocr_text"] or "No OCR text")

    st.subheader("3. Material mapping")
    mm = result["material_match"]
    if mm.get("match"):
        st.write(mm["match"])
    else:
        st.warning("No material match")

    st.subheader("4. Validation")
    checks = result["validation"]["checks"]
    for name, passed in checks.items():
        st.write(("✅ " if passed else "❌ ") + name.replace("_", " ").title())

    if result["validation"]["review_required"]:
        st.warning("Human review required. The record was not silently persisted as a validated receipt.")
    elif result["persisted"]:
        st.success(f"Material validated and persisted. UID: {result['uid']}")

st.divider()
st.subheader("Traceability records")
try:
    records = requests.get(f"{API_URL}/receipts", timeout=3).json()
    if records:
        st.dataframe(records, use_container_width=True)
    else:
        st.info("No validated receipts yet.")
except Exception:
    st.info("Start the backend to view records.")
