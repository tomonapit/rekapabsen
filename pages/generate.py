import os
import zipfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st
import pandas as pd

from config import (
    OUTPUT_ROOT,
    KOP_NAMA,
    KOP_ALAMAT,
    KOP_KONTAK,
    NO_DOK_DEFAULT,
    LOGO_PATH,
    WATERMARK_TEXT,
    QR_SECRET_KEY,
)

from matrix_report import (
    generate_matrix_reports,
    apply_manual_override,
    build_employee_matrix_row,
    matrix_to_reportlab_table,
)

from mesin_ai_absensi import generate_reports


# =========================================================
# Helpers
# =========================================================
def _read_logo_bytes(path: str):
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None


def page_generate():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## ⚡ Generate Report (Enterprise)")
    st.markdown(
        '<div class="alert-info">Generate Matrix Excel + PDF Premium per pegawai + QR Audit + Watermark + ZIP.</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    df = st.session_state.get("df")
    if df is None:
        st.markdown('<div class="alert-warn">⚠️ Belum ada data. Upload dulu.</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    periode = st.session_state.get("periode", "")
    catatan = st.session_state.get("catatan", "")
    use_gabung = st.session_state.get("use_gabung", True)

    batas_masuk = st.session_state.get("batas_masuk", "07:30:00")
    batas_pulang = st.session_state.get("batas_pulang", "16:00:00")

    max_workers = st.slider("⚡ Kecepatan Generate (Thread)", 1, 8, 4)

    if st.button("🚀 Generate Semua (Enterprise)", use_container_width=True, key="btn_generate_all"):
        with st.spinner("Sedang memproses… (override → matrix → pdf → zip)"):

            # ✅ APPLY OVERRIDE FIRST
            df_gen = apply_manual_override(df, st.session_state["manual_override_df"])

            periode_text = periode.strip()
            if not periode_text:
                dtmin = pd.to_datetime(df_gen["Tanggal"], errors="coerce").min()
                periode_text = dtmin.strftime("%B %Y") if not pd.isna(dtmin) else "Periode"

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_folder = os.path.join(OUTPUT_ROOT, f"{periode_text.replace(' ', '_')}__{ts}")
            os.makedirs(out_folder, exist_ok=True)

            # ✅ Generate matrix excel include override
            matrix_path, matrix_per_path, matrix_all_df = generate_matrix_reports(
                df=df_gen,
                outdir=out_folder,
                periode=periode_text,
                batas_masuk=batas_masuk,
                batas_pulang=batas_pulang,
                manual_override_df=st.session_state["manual_override_df"],
            )

            # ✅ Build matrix elements for each employee (for PDF page matrix)
            matrix_elements_map = {}
            if "Nama" in df_gen.columns:
                for nama in df_gen["Nama"].dropna().unique():
                    mx_emp = build_employee_matrix_row(df_gen, nama, batas_masuk, batas_pulang)
                    elements = matrix_to_reportlab_table(mx_emp)
                    if elements:
                        matrix_elements_map[nama] = elements

            # Logo bytes
            logo_bytes = _read_logo_bytes(LOGO_PATH)

            # =========================================================
            # PARALLEL PDF GENERATION
            # =========================================================
            st.info("⚡ Generate PDF Premium per pegawai (parallel)…")
            progress = st.progress(0)

            # Prepare output folders
            pdf_dir = os.path.join(out_folder, "PDF_PEGAWAI")
            os.makedirs(pdf_dir, exist_ok=True)

            employees = sorted(df_gen["Nama"].dropna().unique().tolist())
            total_emp = len(employees)

            errors = []
            done = 0

            def _worker_generate_one(nama: str):
                # generate_reports processes all employees by default
                # so we create single-employee DF and call generate_reports once
                df_one = df_gen[df_gen["Nama"] == nama].copy()
                if df_one.empty:
                    return None

                # matrix only for that employee
                mx_map = {}
                if nama in matrix_elements_map:
                    mx_map[nama] = matrix_elements_map[nama]

                # each employee in its own folder for safe thread output
                tmp_out = os.path.join(out_folder, "_TMP_" + nama.replace("/", "-"))
                os.makedirs(tmp_out, exist_ok=True)

                summary_path, pdf_dir_one, _ = generate_reports(
                    df=df_one,
                    outdir=tmp_out,
                    periode=periode_text,
                    catatan=catatan.strip(),
                    gabung=False,
                    ttd_nama="Peby Ratika, S.A.P.",
                    ttd_jabatan="Katimker OSDM RSUP Jayapura",
                    ttd_label="Mengetahui",
                    batas_masuk=batas_masuk,
                    batas_pulang=batas_pulang,
                    use_landscape=True,
                    matrix_elements_map=mx_map,

                    # premium params
                    kop_nama=KOP_NAMA,
                    kop_alamat=KOP_ALAMAT,
                    kop_kontak=KOP_KONTAK,
                    no_dok=NO_DOK_DEFAULT,
                    logo_bytes=logo_bytes,
                    logo_path=LOGO_PATH,
                    watermark_text=WATERMARK_TEXT,
                    qr_secret_key=QR_SECRET_KEY,
                )

                # move pdf result into main pdf_dir
                pdfs = [f for f in os.listdir(pdf_dir_one) if f.lower().endswith(".pdf")]
                if not pdfs:
                    return None
                src_pdf = os.path.join(pdf_dir_one, pdfs[0])
                dst_pdf = os.path.join(pdf_dir, pdfs[0])
                os.replace(src_pdf, dst_pdf)

                return dst_pdf

            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futures = {ex.submit(_worker_generate_one, nama): nama for nama in employees}
                for fut in as_completed(futures):
                    nama = futures[fut]
                    try:
                        fut.result()
                    except Exception as e:
                        errors.append(f"{nama}: {e}")

                    done += 1
                    progress.progress(done / max(total_emp, 1))

            # show errors if exist
            if errors:
                st.warning("⚠️ Beberapa pegawai gagal dibuatkan PDF:")
                st.code("\n".join(errors))

            st.success("✅ PDF Premium per pegawai selesai dibuat!")

            # =========================================================
            # ZIP ALL PDF
            # =========================================================
            zip_path = os.path.join(out_folder, f"PDF_Pegawai_{periode_text.replace(' ', '_')}.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                for fn in os.listdir(pdf_dir):
                    if fn.lower().endswith(".pdf"):
                        full = os.path.join(pdf_dir, fn)
                        z.write(full, arcname=fn)

            # =========================================================
            # OPTIONAL COMBINED PDF
            # =========================================================
            combined_path = ""
            if use_gabung:
                try:
                    from PyPDF2 import PdfMerger
                    combined_path = os.path.join(out_folder, f"PDF_GABUNGAN_{periode_text.replace(' ', '_')}.pdf")
                    merger = PdfMerger()
                    for fn in sorted(os.listdir(pdf_dir)):
                        if fn.lower().endswith(".pdf"):
                            merger.append(os.path.join(pdf_dir, fn))
                    merger.write(combined_path)
                    merger.close()
                except Exception:
                    combined_path = ""

            # =========================================================
            # SAVE SESSION OUTPUT
            # =========================================================
            st.session_state["generated"] = True
            st.session_state["out_folder"] = out_folder
            st.session_state["paths"] = {
                "summary_path": os.path.join(out_folder, f"SUMMARY_REKAP_{periode_text.replace(' ', '_')}.xlsx"),
                "combined_path": combined_path,
                "zip_path": zip_path,
                "pdf_dir": pdf_dir,
                "matrix_path": matrix_path,
                "matrix_per_path": matrix_per_path,
            }

            st.markdown(
                '<div class="alert-success">✅ Semua report berhasil dibuat. Silakan buka menu Download & Arsip.</div>',
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)
