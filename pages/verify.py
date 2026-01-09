import streamlit as st
import hashlib
from PyPDF2 import PdfReader
from config import QR_SECRET_KEY


# =========================================================
# Helpers
# =========================================================
def parse_payload(payload: str) -> dict:
    """
    Payload format stored in PDF metadata Subject:
        APP=MESIN AI PACE
        NAMA=...
        NIK=...
        PERIODE=...
        GENERATED_AT=...
        CHECKSUM=...
    """
    result = {}
    for line in str(payload).splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def calc_checksum(nama: str, nik: str, periode: str, generated_at: str, secret_key: str) -> str:
    raw = f"{nama}|{nik}|{periode}|{generated_at}|{secret_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()[:16]


# =========================================================
# PAGE
# =========================================================
def page_verify():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## ✅ Verifikasi Dokumen PDF (QR Audit)")

    st.markdown(
        '<div class="alert-info">'
        'Upload PDF pegawai hasil sistem. Sistem akan membaca metadata QR payload dan mengecek checksum. '
        'Jika dokumen diubah, checksum akan gagal.'
        "</div>",
        unsafe_allow_html=True,
    )

    pdf_file = st.file_uploader("📄 Upload PDF Pegawai", type=["pdf"], key="upload_pdf_verify")

    if not pdf_file:
        st.markdown("</div>", unsafe_allow_html=True)
        return

    try:
        reader = PdfReader(pdf_file)
        meta = reader.metadata or {}

        payload = ""
        if "/Subject" in meta:
            payload = meta.get("/Subject", "")

        if not payload:
            st.error("⚠️ Payload QR tidak ditemukan di metadata PDF.")
            st.info("Pastikan PDF benar-benar di-generate dari MESIN AI PACE versi audit.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        # Parse payload
        data = parse_payload(payload)

        required = ["APP", "NAMA", "NIK", "PERIODE", "GENERATED_AT", "CHECKSUM"]
        missing = [r for r in required if r not in data]

        if missing:
            st.error(f"⚠️ Payload tidak lengkap. Missing: {missing}")
            st.code(payload)
            st.markdown("</div>", unsafe_allow_html=True)
            return

        # Compute checksum
        expected = calc_checksum(
            nama=data["NAMA"],
            nik=data["NIK"],
            periode=data["PERIODE"],
            generated_at=data["GENERATED_AT"],
            secret_key=QR_SECRET_KEY,
        )

        # Compare
        if expected == data["CHECKSUM"]:
            st.success("✅ VALID — Dokumen asli dan tidak berubah.")
        else:
            st.error("❌ INVALID — Dokumen telah berubah / secret key tidak cocok.")
            st.write(f"Checksum PDF: **{data['CHECKSUM']}**")
            st.write(f"Checksum Expected: **{expected}**")

        # Show payload details
        st.divider()
        st.markdown("### 📌 Detail QR Payload (Metadata)")
        st.json(data)

        st.markdown("### 📄 Raw Payload")
        st.code(payload)

    except Exception as e:
        st.error(f"❌ Gagal membaca PDF: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
