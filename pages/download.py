import os
import base64
import streamlit as st
import streamlit.components.v1 as components


# =========================================================
# PDF Preview Helper
# =========================================================
def render_pdf(pdf_path, height=900):
    if not os.path.exists(pdf_path):
        st.error("PDF tidak ditemukan.")
        return

    with open(pdf_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")

    pdf_display = f"""
    <div class="pdf-frame">
        <iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="{height}"></iframe>
    </div>
    """
    components.html(pdf_display, height=height + 30, scrolling=True)


# =========================================================
# DOWNLOAD PAGE
# =========================================================
def page_download():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## 📥 Download & Preview Output (Enterprise)")
    st.write("")

    if not st.session_state.get("generated"):
        st.markdown('<div class="alert-warn">⚠️ Belum ada report yang di-generate.</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    paths = st.session_state.get("paths", {})
    pdf_dir = paths.get("pdf_dir", "")
    summary_path = paths.get("summary_path", "")
    matrix_path = paths.get("matrix_path", "")
    matrix_per_path = paths.get("matrix_per_path", "")
    combined_path = paths.get("combined_path", "")
    zip_path = paths.get("zip_path", "")

    # ---------------------------------------------------------
    # DOWNLOAD BUTTONS
    # ---------------------------------------------------------
    st.markdown("### ⬇️ Download Output")
    c1, c2, c3, c4, c5 = st.columns(5)

    # Summary Rekap
    with c1:
        if summary_path and os.path.exists(summary_path):
            with open(summary_path, "rb") as f:
                st.download_button(
                    "📊 Summary Rekap (Excel)",
                    f,
                    file_name=os.path.basename(summary_path),
                    use_container_width=True,
                )
        else:
            st.info("Summary tidak tersedia")

    # Matrix Rekap
    with c2:
        if matrix_path and os.path.exists(matrix_path):
            with open(matrix_path, "rb") as f:
                st.download_button(
                    "📅 Matrix Rekap (Excel)",
                    f,
                    file_name=os.path.basename(matrix_path),
                    use_container_width=True,
                )
        else:
            st.info("Matrix rekap tidak ada")

    # Matrix per Pegawai
    with c3:
        if matrix_per_path and os.path.exists(matrix_per_path):
            with open(matrix_per_path, "rb") as f:
                st.download_button(
                    "👥 Matrix per Pegawai",
                    f,
                    file_name=os.path.basename(matrix_per_path),
                    use_container_width=True,
                )
        else:
            st.info("Matrix per pegawai tidak ada")

    # PDF Gabungan
    with c4:
        if combined_path and os.path.exists(combined_path):
            with open(combined_path, "rb") as f:
                st.download_button(
                    "📄 PDF Gabungan",
                    f,
                    file_name=os.path.basename(combined_path),
                    use_container_width=True,
                )
        else:
            st.info("PDF gabungan tidak dibuat")

    # ZIP Semua PDF
    with c5:
        if zip_path and os.path.exists(zip_path):
            with open(zip_path, "rb") as f:
                st.download_button(
                    "🗂️ ZIP Semua PDF",
                    f,
                    file_name=os.path.basename(zip_path),
                    use_container_width=True,
                )
        else:
            st.info("ZIP belum tersedia")

    st.divider()

    # ---------------------------------------------------------
    # PDF Preview Section
    # ---------------------------------------------------------
    st.markdown("### 👁️ Preview PDF Pegawai")

    if pdf_dir and os.path.exists(pdf_dir):
        pdf_files = sorted([f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")])

        if not pdf_files:
            st.warning("Tidak ada file PDF di folder output.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        selected_pdf = st.selectbox("Pilih PDF Pegawai", pdf_files, key="select_preview_pdf")
        full_path = os.path.join(pdf_dir, selected_pdf)

        colA, colB = st.columns([2, 5])

        with colA:
            with open(full_path, "rb") as f:
                st.download_button(
                    "⬇️ Download PDF Ini",
                    f,
                    file_name=selected_pdf,
                    use_container_width=True,
                )

            st.markdown(
                '<div class="alert-info">Tip: gunakan Dashboard & Review untuk cek data sebelum download semua.</div>',
                unsafe_allow_html=True,
            )

            st.markdown("#### 📂 Lokasi Output")
            st.code(paths.get("out_folder", "-"))

        with colB:
            render_pdf(full_path, height=900)

    else:
        st.markdown(
            '<div class="alert-warn">⚠️ Folder PDF tidak ditemukan. Cek ulang proses generate.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
