# =========================================================
# MESIN AI PACE / AI-ABSEN - CORE ENGINE
# Fix Pack FINAL:
# - standardize_columns robust (imports re)
# - safe_dt parses date+time, time-only, excel time
# - generate_reports premium PDF (header/footer/QR) fixed indentation and returns
# - Scan Masuk / Scan Pulang displayed as HH:MM in PDF
# =========================================================

import os
import io
import re
import base64
import hashlib
from datetime import datetime, date, time, timedelta
from typing import Optional, Dict, List, Tuple
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


# =========================================================
# COLUMN STANDARDIZER
# =========================================================
def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize various attendance export formats to a fixed schema.

    Guarantees these columns exist:
      - Nama, NIK, Unit, GOL, Tanggal, Scan Masuk, Scan Pulang

    Also parses:
      - Tanggal -> datetime64[ns]
      - Scan Masuk/Pulang -> datetime64[ns] (time preserved)
    """
    if df is None or df.empty:
        return df
    df = df.copy()

    def _norm(s: str) -> str:
        s = str(s)
        s = s.replace("\n", " ").replace("\r", " ")
        s = re.sub(r"\s+", " ", s).strip()
        return s

    df.columns = [_norm(c) for c in df.columns]
    col_map = {c.lower().strip(): c for c in df.columns}

    aliases: Dict[str, str] = {}

    for k in ["nama", "nama pegawai", "pegawai", "employee", "name"]:
        aliases[k] = "Nama"
    for k in ["nik", "nip", "id", "id pegawai", "employee id", "no pegawai"]:
        aliases[k] = "NIK"
    for k in ["unit", "bagian", "departemen", "department", "ruangan", "instalasi"]:
        aliases[k] = "Unit"
    for k in ["gol", "golongan", "grade", "level", "pangkat"]:
        aliases[k] = "GOL"
    for k in ["tanggal", "tgl", "date", "tanggal absen", "tanggal absensi"]:
        aliases[k] = "Tanggal"
    for k in [
        "scan masuk", "scan masuk 1", "scan masuk1",
        "jam masuk", "jam masuk 1", "jam masuk1",
        "check in", "checkin", "clock in", "in", "masuk",
    ]:
        aliases[k] = "Scan Masuk 1"
    for k in [
        "scan pulang", "scan pulang 1", "scan pulang1",
        "jam pulang", "jam pulang 1", "jam pulang1",
        "check out", "checkout", "clock out", "out", "pulang",
    ]:
        aliases[k] = "Scan Pulang 1"

    rename_dict = {}
    for low, original in col_map.items():
        if low in aliases:
            rename_dict[original] = aliases[low]
    df = df.rename(columns=rename_dict)

    def _find_col_contains(keywords):
        for c in df.columns:
            cl = c.lower()
            for kw in keywords:
                if kw in cl:
                    return c
        return None

    if "Scan Masuk" not in df.columns:
        guess_in = _find_col_contains(["masuk", "check in", "clock in"])
        if guess_in:
            df = df.rename(columns={guess_in: "Scan Masuk"})

    if "Scan Pulang" not in df.columns:
        guess_out = _find_col_contains(["pulang", "check out", "clock out"])
        if guess_out:
            df = df.rename(columns={guess_out: "Scan Pulang"})

    required = ["Nama", "NIK", "Unit", "GOL", "Tanggal", "Scan Masuk", "Scan Pulang"]
    for c in required:
        if c not in df.columns:
            df[c] = None

    for c in ["Nama", "NIK", "Unit", "GOL"]:
        df[c] = df[c].astype(str).str.strip()
        df[c] = df[c].replace({"nan": "", "None": ""})

    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce", dayfirst=True)

    df["Scan Masuk"] = safe_dt(df["Scan Masuk"], time_only=True)
    df["Scan Pulang"] = safe_dt(df["Scan Pulang"], time_only=True)

    return df


def to_time(v):
    """Convert Timestamp/datetime/time/string/excel fraction -> datetime.time"""
    if v is None or (isinstance(v, float) and pd.isna(v)) or pd.isna(v):
        return None

    if isinstance(v, time):
        return v

    if isinstance(v, (pd.Timestamp, datetime)):
        return v.time()

    if isinstance(v, (int, float)) and 0 <= float(v) < 1:
        secs = int(round(float(v) * 24 * 3600))
        hh = secs // 3600
        mm = (secs % 3600) // 60
        ss = secs % 60
        return time(hh, mm, ss)

    s = str(v).strip()
    if not s:
        return None

    dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
    if pd.isna(dt):
        return None
    return dt.time()


def minutes_between(t1: time, t2: time) -> int:
    """Return minutes difference t2 - t1"""
    if t1 is None or t2 is None:
        return 0
    dt1 = datetime.combine(datetime.today(), t1)
    dt2 = datetime.combine(datetime.today(), t2)
    return int((dt2 - dt1).total_seconds() // 60)

# =========================================================
# DATETIME PARSER (FIX)
# =========================================================
def safe_dt(x, time_only: bool = False):
    """
    Robust datetime parser for Series or scalar.

    Supports:
    - full datetime strings
    - time-only strings HH:MM or HH:MM:SS
    - Excel float time (0.0-1.0) or Excel datetime numeric

    If time_only=True => returns python datetime.time objects
    """

    def _parse_one(v):
        if v is None or (isinstance(v, float) and pd.isna(v)) or v == "":
            return pd.NaT

        # Excel time fraction
        if isinstance(v, (int, float)) and not pd.isna(v):
            if 0 <= float(v) < 1:
                secs = int(round(float(v) * 24 * 3600))
                hh = secs // 3600
                mm = (secs % 3600) // 60
                ss = secs % 60
                return time(hh, mm, ss) if time_only else pd.Timestamp(f"1900-01-01 {hh:02d}:{mm:02d}:{ss:02d}")
            dt = pd.to_datetime(v, errors="coerce", unit="D", origin="1899-12-30")
            return dt.time() if time_only else dt

        # already datetime-like
        if isinstance(v, pd.Timestamp):
            return v.time() if time_only else v
        if isinstance(v, datetime):
            return v.time() if time_only else pd.Timestamp(v)
        if isinstance(v, time):
            return v

        s = str(v).strip()
        if not s:
            return pd.NaT

        # time-only format
        if re.match(r"^\d{1,2}:\d{2}(:\d{2})?$", s):
            if len(s.split(":")) == 2:
                s += ":00"
            hh, mm, ss = map(int, s.split(":"))
            return time(hh, mm, ss) if time_only else pd.Timestamp(f"1900-01-01 {hh:02d}:{mm:02d}:{ss:02d}")

        # datetime format
        dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
        return dt.time() if time_only else dt

    if isinstance(x, pd.Series):
        return x.apply(_parse_one)
    return _parse_one(x)



# =========================================================
# PDF PREMIUM UTILITIES
# =========================================================
def _safe_logo_reader(logo_bytes: Optional[bytes], logo_path: Optional[str]):
    try:
        if logo_bytes:
            return ImageReader(io.BytesIO(logo_bytes))
        if logo_path and os.path.exists(logo_path):
            return ImageReader(logo_path)
    except Exception:
        return None
    return None


def _checksum_payload(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()[:16]


def build_qr_payload(nama: str, nik: str, periode: str, secret_key: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    raw = f"{nama}|{nik}|{periode}|{ts}|{secret_key}"
    checksum = _checksum_payload(raw)
    payload = (
        f"APP=MESIN AI PACE\n"
        f"NAMA={nama}\n"
        f"NIK={nik}\n"
        f"PERIODE={periode}\n"
        f"GENERATED_AT={ts}\n"
        f"CHECKSUM={checksum}"
    )
    return payload


def draw_watermark(c: canvas.Canvas, doc, text: str):
    if not text:
        return
    width, height = doc.pagesize
    c.saveState()
    c.setFont("Helvetica-Bold", 42)
    c.setFillColor(colors.Color(0, 0, 0, alpha=0.08))
    c.translate(width / 2, height / 2)
    c.rotate(35)
    c.drawCentredString(0, 0, text)
    c.restoreState()


def draw_header_footer_premium(
    c: canvas.Canvas,
    doc,
    kop_nama: str,
    kop_alamat: str,
    kop_kontak: str,
    no_dok: str,
    logo_bytes: Optional[bytes] = None,
    logo_path: Optional[str] = None,
    watermark_text: str = "",
):
    width, height = doc.pagesize
    left = doc.leftMargin
    right = width - doc.rightMargin

    draw_watermark(c, doc, watermark_text)

    c.setFillColor(colors.HexColor("#F3F6FB"))
    c.rect(0, height - 2.8 * cm, width, 2.8 * cm, fill=1, stroke=0)

    logo = _safe_logo_reader(logo_bytes, logo_path)
    if logo:
        c.drawImage(logo, left, height - 2.45 * cm, width=2.2 * cm, height=2.2 * cm, mask="auto")

    x_text = left + 2.45 * cm
    y_text = height - 1.05 * cm

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 12)
    for i, line in enumerate(str(kop_nama).split("\n")):
        c.drawString(x_text, y_text - (i * 0.45 * cm), line)

    c.setFont("Helvetica", 8.5)
    c.setFillColor(colors.HexColor("#334155"))
    addr_y = y_text - (len(str(kop_nama).split("\n")) * 0.50 * cm)
    for i, line in enumerate(str(kop_alamat).split("\n")):
        c.drawString(x_text, addr_y - (i * 0.36 * cm), line)

    cont_y = addr_y - (len(str(kop_alamat).split("\n")) * 0.40 * cm) - 0.05 * cm
    if kop_kontak:
        c.drawString(x_text, cont_y, kop_kontak)

    c.setStrokeColor(colors.HexColor("#0F172A"))
    c.setLineWidth(1.6)
    c.line(left, height - 2.95 * cm, right, height - 2.95 * cm)

    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.8)
    c.line(left, height - 3.10 * cm, right, height - 3.10 * cm)

    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.8)
    c.line(left, doc.bottomMargin - 0.25 * cm, right, doc.bottomMargin - 0.25 * cm)

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#475569"))
    printed = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.drawString(left, doc.bottomMargin - 0.7 * cm, f"No. Dok: {no_dok} | Dicetak: {printed}")

    page = c.getPageNumber()
    c.drawRightString(right, doc.bottomMargin - 0.7 * cm, f"Halaman {page}")


# =========================================================
# STYLES
# =========================================================
def build_styles():
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "title",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=6,
        alignment=1,
    )
    sub = ParagraphStyle(
        "sub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#334155"),
        spaceAfter=8,
        alignment=1,
    )
    header = ParagraphStyle(
        "header",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )
    return title, sub, header, styles["Normal"]



def _fmt_time(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)) or pd.isna(v):
        return "-"

    try:
        # ✅ kalau sudah time object
        if isinstance(v, time):
            return v.strftime("%H:%M")

        # ✅ kalau Timestamp / datetime
        if isinstance(v, (pd.Timestamp, datetime)):
            return v.strftime("%H:%M")

        # ✅ excel fraction time 0.0-1.0
        if isinstance(v, (int, float)) and 0 <= float(v) < 1:
            secs = int(round(float(v) * 24 * 3600))
            hh = secs // 3600
            mm = (secs % 3600) // 60
            return f"{hh:02d}:{mm:02d}"

        # ✅ kalau string atau lainnya
        s = str(v).strip()
        if not s:
            return "-"

        # coba parse datetime atau time
        dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if pd.isna(dt):
            return "-"

        return dt.strftime("%H:%M")

    except Exception:
        return "-"



# =========================================================
# KPI BOX + SIGNATURE + QR
# =========================================================
def build_kpi_box(page_width: float, nik: str, nama: str, unit: str, gol: str, periode: str, kpi: dict) -> Table:
    data = [
        ["NIK", nik or "-", "Nama", nama],
        ["Unit", unit or "-", "Gol", gol or "-"],
        ["Periode", periode, "Total Hadir", str(kpi.get("hadir", 0))],
        ["Total Telat (menit)", str(kpi.get("telat", 0)), "Total Lembur (jam)", str(kpi.get("lembur", 0))],
        ["Hari Tidak Lengkap", str(kpi.get("tl", 0)), "Catatan", kpi.get("catatan", "-")],
    ]
    tbl = Table(data, colWidths=[page_width * 0.16, page_width * 0.34, page_width * 0.16, page_width * 0.34])
    tbl.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F7FAFF")),
            ("BOX", (0, 0), (-1, -1), 1.0, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#E2E8F0")),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#0F172A")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    return tbl


def build_signature_block(page_width: float, ttd_label: str, ttd_jabatan: str, ttd_nama: str, kota="Jayapura") -> Table:
    today = datetime.now().strftime("%d %B %Y")
    data = [
        [f"{kota}, {today}"],
        [ttd_label + ","],
        [ttd_jabatan],
        [""],
        [""],
        ["__________________________"],
        [ttd_nama],
    ]
    tbl = Table(data, colWidths=[page_width])
    tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, 2), "Helvetica"),
        ("FONTNAME", (0, 6), (-1, 6), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 2), 10),
        ("FONTSIZE", (0, 6), (-1, 6), 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return tbl


def build_qr_block(qr_payload: str) -> Table:
    try:
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics.barcode.qr import QrCodeWidget

        qrw = QrCodeWidget(qr_payload)
        bounds = qrw.getBounds()
        size = 2.8 * cm
        w = bounds[2] - bounds[0]
        h = bounds[3] - bounds[1]
        d = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
        d.add(qrw)
        tbl = Table([[d]], colWidths=[size], rowHeights=[size])
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5E1")),
        ]))
        return tbl
    except Exception:
        return Table([[Paragraph("QR Error", getSampleStyleSheet()["Normal"])]], colWidths=[3 * cm])


def draw_employee_report_premium(
    elements: list,
    g: pd.DataFrame,
    nik: str,
    nama: str,
    unit: str,
    gol: str,
    periode: str,
    catatan: str,
    ttd_nama: str,
    ttd_jabatan: str,
    ttd_label: str,
    use_landscape: bool = True,
    matrix_elements: Optional[list] = None,
    qr_payload: str = "",
):
    title_style, sub_style, header_style, _ = build_styles()
    page_width = (landscape(A4)[0] if use_landscape else A4[0]) - (1.6 * cm * 2)

    # ✅ Pastikan kolom wajib ada
    for col in ["Tanggal", "Scan Masuk_dt", "Scan Pulang_dt", "Telat (Menit)", "Lembur (Jam)", "Status Scan"]:
        if col not in g.columns:
            g[col] = pd.NA

    hadir = int(g["Scan Masuk_dt"].notna().sum())
    tl = int(((g["Scan Masuk_dt"].isna()) | (g["Scan Pulang_dt"].isna())).sum())
    telat = int(pd.to_numeric(g["Telat (Menit)"], errors="coerce").fillna(0).sum())
    lembur = float(pd.to_numeric(g["Lembur (Jam)"], errors="coerce").fillna(0).sum().round(2))

    kpi = {"hadir": hadir, "tl": tl, "telat": telat, "lembur": lembur, "catatan": catatan if catatan else "-"}

    elements += [
        Spacer(1, 0.4 * cm),
        Paragraph("REKAP ABSENSI PEGAWAI", title_style),
        Paragraph(f"Periode: {periode}", sub_style),
        Spacer(1, 0.3 * cm),
        build_kpi_box(page_width, nik, nama, unit, gol, periode, kpi),
        Spacer(1, 0.35 * cm),
        Paragraph("Rincian Kehadiran", header_style),
    ]

    table_data = [["No", "Tanggal", "Masuk", "Pulang", "Telat (m)", "Lembur (j)", "Status"]]

    g = g.sort_values("Tanggal").copy()

    # ✅ FIX: gunakan to_dict agar key tetap sesuai (kolom dengan spasi aman)
    for i, r in enumerate(g.to_dict("records"), start=1):
        dt = pd.to_datetime(r.get("Tanggal"), errors="coerce")
        tanggal = "-" if pd.isna(dt) else dt.strftime("%d/%m/%Y")

        masuk = _fmt_time(r.get("Scan Masuk_dt"))
        pulang = _fmt_time(r.get("Scan Pulang_dt"))

        telat_val = pd.to_numeric(r.get("Telat (Menit)", 0), errors="coerce")
        lembur_val = pd.to_numeric(r.get("Lembur (Jam)", 0), errors="coerce")
        status_val = r.get("Status Scan", "-")

        telat_str = "-" if pd.isna(telat_val) else str(int(telat_val))
        lembur_str = "-" if pd.isna(lembur_val) else f"{float(lembur_val):.2f}"
        status = "-" if pd.isna(status_val) else str(status_val)

        table_data.append([str(i), tanggal, masuk, pulang, telat_str, lembur_str, status])

    detail_tbl = Table(
        table_data,
        colWidths=[
            page_width * 0.06,
            page_width * 0.14,
            page_width * 0.13,
            page_width * 0.13,
            page_width * 0.10,
            page_width * 0.10,
            page_width * 0.34,
        ],
    )

    detail_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFF")]),
        ("ALIGN", (0, 1), (5, -1), "CENTER"),
        ("ALIGN", (6, 1), (6, -1), "LEFT"),
    ]))

    elements.append(detail_tbl)
    elements.append(Spacer(1, 0.45 * cm))

    sign_tbl = build_signature_block(page_width * 0.62, ttd_label, ttd_jabatan, ttd_nama)
    qr_tbl = build_qr_block(qr_payload)
    bottom_tbl = Table([[qr_tbl, sign_tbl]], colWidths=[page_width * 0.38, page_width * 0.62])
    bottom_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    elements.append(bottom_tbl)

    if matrix_elements:
        elements.append(PageBreak())
        elements.extend(matrix_elements)
        elements.append(Spacer(1, 0.2 * cm))


def generate_reports(
    df: pd.DataFrame,
    outdir: str,
    periode: str,
    catatan: str = "",
    gabung: bool = True,
    ttd_nama: str = "",
    ttd_jabatan: str = "",
    ttd_label: str = "Mengetahui",
    batas_masuk: str = "07:30:00",
    batas_pulang: str = "16:00:00",
    use_landscape: bool = True,
    matrix_elements_map: Optional[Dict[str, list]] = None,
    kop_nama: str = "",
    kop_alamat: str = "",
    kop_kontak: str = "",
    no_dok: str = "",
    logo_bytes: Optional[bytes] = None,
    logo_path: Optional[str] = None,
    watermark_text: str = "",
    qr_secret_key: str = "RSUPJAYAPURA_2025_OSDM",
):
    os.makedirs(outdir, exist_ok=True)
    pdf_dir = os.path.join(outdir, "PDF_PEGAWAI")
    os.makedirs(pdf_dir, exist_ok=True)

    df = df.copy()

    # ✅ Tanggal selalu Timestamp
    df["Tanggal"] = safe_dt(df["Tanggal"], time_only=False)
    df = df.dropna(subset=["Tanggal"])

    for col in ["Nama", "NIK", "Unit", "GOL"]:
        if col not in df.columns:
            df[col] = ""

    # ✅ Scan masuk/pulang selalu Timestamp
    df["Scan Masuk_dt"] = safe_dt(df["Scan Masuk"], time_only=False)
    df["Scan Pulang_dt"] = safe_dt(df["Scan Pulang"], time_only=False)

        # ✅ Batas masuk/pulang harus time-only
    batas_masuk_t = safe_dt(batas_masuk, time_only=True)
    batas_pulang_t = safe_dt(batas_pulang, time_only=True)

    # ✅ Scan time-only untuk hitungan
    df["Scan Masuk_t"] = df["Scan Masuk_dt"].apply(to_time)
    df["Scan Pulang_t"] = df["Scan Pulang_dt"].apply(to_time)

    # ✅ Hitung Telat (Menit)
    def _telat(row):
        scan_t = row.get("Scan Masuk_t", None)
        if scan_t is None or batas_masuk_t is None:
            return 0
        try:
            return max(0, minutes_between(batas_masuk_t, scan_t))
        except Exception:
            return 0

    # ✅ Hitung Lembur (Jam)
    def _lembur(row):
        scan_t = row.get("Scan Pulang_t", None)
        if scan_t is None or batas_pulang_t is None:
            return 0
        try:
            lembur_menit = max(0, minutes_between(batas_pulang_t, scan_t))
            return round(lembur_menit / 60, 2)
        except Exception:
            return 0

    df["Telat (Menit)"] = df.apply(_telat, axis=1)
    df["Lembur (Jam)"] = df.apply(_lembur, axis=1)

    # ✅ Status scan
    def _status_scan(row):
        if row.get("Scan Masuk_dt") is None or pd.isna(row.get("Scan Masuk_dt")):
            return "Tidak Lengkap (TL)"
        if row.get("Scan Pulang_dt") is None or pd.isna(row.get("Scan Pulang_dt")):
            return "Tidak Lengkap (TL)"
        return "Lengkap"

    df["Status Scan"] = df.apply(_status_scan, axis=1)


    # ---------------------------------------------------------
    # ✅ SUMMARY REKAP
    # ---------------------------------------------------------
    summary_df = (
        df.groupby(["Nama", "NIK", "Unit", "GOL"])
        .agg(
            Hadir=("Scan Masuk_dt", lambda x: x.notna().sum()),
            TL=("Status Scan", lambda x: (x.str.contains("TL")).sum()),
            Telat=("Telat (Menit)", "sum"),
            Lembur=("Lembur (Jam)", "sum"),
        )
        .reset_index()
    )

    summary_path = os.path.join(outdir, f"SUMMARY_REKAP_{periode.replace(' ', '_')}.xlsx")
    summary_df.to_excel(summary_path, index=False)

    # ---------------------------------------------------------
    # ✅ GENERATE PDF PER PEGAWAI
    # ---------------------------------------------------------
    pdf_paths: List[str] = []
    employees = sorted(df["Nama"].dropna().unique().tolist())

    for nama in employees:
        g = df[df["Nama"] == nama].copy()
        if g.empty:
            continue

        nik = str(g["NIK"].dropna().astype(str).iloc[0]) if g["NIK"].dropna().any() else ""
        unit = str(g["Unit"].dropna().astype(str).iloc[0]) if g["Unit"].dropna().any() else ""
        gol = str(g["GOL"].dropna().astype(str).iloc[0]) if g["GOL"].dropna().any() else ""

        emp_pdf = os.path.join(pdf_dir, f"{nama.replace('/', '-')}.pdf")
        pdf_paths.append(emp_pdf)

        pagesize = landscape(A4) if use_landscape else A4
        doc = SimpleDocTemplate(
            emp_pdf,
            pagesize=pagesize,
            leftMargin=1.6 * cm,
            rightMargin=1.6 * cm,
            topMargin=3.5 * cm,
            bottomMargin=1.6 * cm,
        )

        elements: List = []
        qr_payload = build_qr_payload(nama, nik, periode, qr_secret_key)

        mx_elements = None
        if matrix_elements_map and nama in matrix_elements_map:
            mx_elements = matrix_elements_map[nama]

        draw_employee_report_premium(
            elements=elements,
            g=g,
            nik=nik,
            nama=nama,
            unit=unit,
            gol=gol,
            periode=periode,
            catatan=catatan,
            ttd_nama=ttd_nama,
            ttd_jabatan=ttd_jabatan,
            ttd_label=ttd_label,
            use_landscape=use_landscape,
            matrix_elements=mx_elements,
            qr_payload=qr_payload,
        )

        def _on_page(c, d):
            try:
                c.setAuthor("MESIN AI PACE")
                c.setTitle(f"Rekap Absensi - {nama}")
                c.setSubject(qr_payload)
                c.setKeywords(f"RSUP Jayapura, OSDM, {periode}")
            except Exception:
                pass

            draw_header_footer_premium(
                c,
                d,
                kop_nama=kop_nama,
                kop_alamat=kop_alamat,
                kop_kontak=kop_kontak,
                no_dok=no_dok,
                logo_bytes=logo_bytes,
                logo_path=logo_path,
                watermark_text=watermark_text,
            )

        doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)

    # ---------------------------------------------------------
    # ✅ PDF GABUNGAN
    # ---------------------------------------------------------
    combined_path = ""
    if gabung and pdf_paths:
        try:
            from PyPDF2 import PdfMerger
            combined_path = os.path.join(outdir, f"PDF_GABUNGAN_{periode.replace(' ', '_')}.pdf")
            merger = PdfMerger()
            for pth in pdf_paths:
                merger.append(pth)
            merger.write(combined_path)
            merger.close()
        except Exception:
            combined_path = ""

    return summary_path, pdf_dir, combined_path
