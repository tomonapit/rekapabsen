import streamlit as st
import pandas as pd
from mesin_ai_absensi import standardize_columns

@st.cache_data(show_spinner=False)
def _read_excel(file):
    return pd.read_excel(file)

def page_upload():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## 📤 Upload Data Absensi")
    st.markdown('<div class="alert-info">Upload file excel absensi (bisa multi-file). Sistem akan auto merge + standardisasi kolom.</div>', unsafe_allow_html=True)
    st.write("")

    uploaded_files = st.file_uploader(
        "Pilih file Excel absensi (bisa multi-file)",
        type=["xlsx"],
        accept_multiple_files=True
    )

    if uploaded_files:
        dfs = [_read_excel(f) for f in uploaded_files]
        df = pd.concat(dfs, ignore_index=True)
        df = standardize_columns(df)
        df["Tanggal"] = pd.to_datetime(df["Tanggal"], dayfirst=True, errors="coerce")
        st.session_state["df"] = df

        st.markdown(f'<div class="alert-success">✅ Data siap: <b>{len(df):,}</b> baris</div>', unsafe_allow_html=True)
        st.markdown("### Preview Data")
        st.dataframe(df.head(60), use_container_width=True, height=500)
    else:
        st.markdown('<div class="alert-warn">⚠️ Silakan upload minimal 1 file Excel untuk memulai.</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
