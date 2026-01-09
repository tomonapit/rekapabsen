import os

APP_TITLE = "MESIN AI PACE"
APP_SUBTITLE = "Presence Analysis & Centralized Evaluation"
APP_ORG = "Rumah Sakit Umum Pusat Jayapura"

APP_USERS = {"osdm": "rsup2025", "admin": "admin123"}

OUTPUT_ROOT = os.path.join(os.getcwd(), "OUTPUT")
os.makedirs(OUTPUT_ROOT, exist_ok=True)

DEFAULT_BATAS_MASUK = "07:30:00"
DEFAULT_BATAS_PULANG = "16:00:00"

# =========================================================
# PDF Header (KOP) - Premium
# =========================================================
KOP_NAMA = "Kementerian Kesehatan RI - Rumah Sakit Umum Pusat Jayapura"
KOP_ALAMAT = "Jl. Raya Sentani - Jayapura, Kel. Argapura, Distrik Heram, Kota Jayapura, Papua - Indonesia"
KOP_KONTAK = "Telp: (0967) xxxx-xxxx  |  Email: rsupjayapura@kemkes.go.id"
NO_DOK_DEFAULT = "OSDM/ABS/001/2025"



# Assets
LOGO_PATH = "assets/logo_rs_jayapura.png"

# =========================================================
# QR Signature + Watermark (Enterprise Audit)
# =========================================================
QR_SECRET_KEY = "RSUPJAYAPURA_2025_OSDM"
WATERMARK_TEXT = "INTERNAL RSUP JAYAPURA - OSDM"
