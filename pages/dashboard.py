import streamlit as st
import matplotlib.pyplot as plt

from matrix_report import apply_manual_override
from analytics import (
    compute_kpi,
    build_daily_trend,
    build_status_distribution,
    render_heatmap,
)


def page_dashboard():
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown("## 📊 Executive Dashboard")
    st.markdown(
        '<div class="alert-info">'
        "Ringkasan performa absensi secara cepat — gunakan filter untuk analisis unit / pegawai."
        "</div>",
        unsafe_allow_html=True,
    )
    st.write("")

    # ===============================
    # Load data
    # ===============================
    df = st.session_state.get("df")
    if df is None or df.empty:
        st.markdown(
            '<div class="alert-warn">⚠️ Belum ada data. Silakan upload pada menu Upload.</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # ===============================
    # Apply manual override first
    # ===============================
    df_preview = apply_manual_override(df, st.session_state.get("manual_override_df"))
    fdf = df_preview.copy()

    # ===============================
    # Filter tools (Enterprise)
    # ===============================
    st.markdown("### 🔎 Filter (Opsional)")
    col1, col2, col3 = st.columns([2.2, 2.0, 2.0])

    with col1:
        if "Nama" in fdf.columns:
            emp_list = sorted(fdf["Nama"].dropna().unique().tolist())
            emp_filter = st.multiselect("Filter Pegawai", emp_list, default=[], key="dash_emp_filter")
        else:
            emp_filter = []
            st.caption("Kolom Nama tidak ditemukan")

    with col2:
        if "Unit" in fdf.columns:
            unit_list = sorted(fdf["Unit"].dropna().unique().tolist())
            unit_filter = st.multiselect("Filter Unit", unit_list, default=[], key="dash_unit_filter")
        else:
            unit_filter = []
            st.caption("Kolom Unit tidak ditemukan")

    with col3:
        batas_masuk = st.session_state.get("batas_masuk", "07:30:00")
        st.caption(f"⏰ Batas Masuk digunakan untuk KPI terlambat: **{batas_masuk}**")

    # Apply filters
    if emp_filter and "Nama" in fdf.columns:
        fdf = fdf[fdf["Nama"].isin(emp_filter)]

    if unit_filter and "Unit" in fdf.columns:
        fdf = fdf[fdf["Unit"].isin(unit_filter)]

    st.divider()

    # ===============================
    # KPI
    # ===============================
    batas_masuk = st.session_state.get("batas_masuk", "07:30:00")
    kpi = compute_kpi(fdf, st.session_state.get("manual_override_df"), batas_masuk=batas_masuk)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Data", f"{kpi['total_rows']:,}")
    k2.metric("Pegawai", f"{kpi['pegawai']:,}")
    k3.metric("Hadir", f"{kpi['hadir']:,}")
    k4.metric("Terlambat", f"{kpi['terlambat']:,}")
    k5.metric("Override", f"{kpi['override']:,}")

    st.divider()

    # ===============================
    # Trend + Distribution
    # ===============================
    cA, cB = st.columns([2.3, 1.4])

    with cA:
        st.markdown("### 📈 Trend Kehadiran Harian")
        trend = build_daily_trend(fdf)
        if trend is None or trend.empty:
            st.info("Trend tidak tersedia.")
        else:
            fig = plt.figure(figsize=(10, 3.2))
            plt.plot(trend["Tanggal"], trend["Hadir"], marker="o")
            plt.title("Total Hadir per Hari", fontweight="bold")
            plt.xlabel("Tanggal")
            plt.ylabel("Hadir")
            plt.xticks(rotation=35)
            plt.tight_layout()
            st.pyplot(fig)

    with cB:
        st.markdown("### 🧾 Distribusi Status")
        dist = build_status_distribution(fdf)
        if dist is None or dist.empty:
            st.info("Distribusi status tidak tersedia.")
        else:
            fig = plt.figure(figsize=(6, 3.2))
            plt.bar(dist["Status"], dist["Jumlah"])
            plt.title("Status Count", fontweight="bold")
            plt.xlabel("Status")
            plt.ylabel("Jumlah")
            plt.tight_layout()
            st.pyplot(fig)

    st.divider()

    # ===============================
    # Heatmap
    # ===============================
    st.markdown("### 🔥 Heatmap Jam Masuk (Hari vs Jam)")
    try:
        # render_heatmap supports render_heatmap(st, df) OR render_heatmap(df)
        render_heatmap(st, fdf)
    except Exception as e:
        st.warning("Heatmap gagal ditampilkan.")
        st.caption(str(e))

    st.divider()

    # ===============================
    # Viewer
    # ===============================
    st.markdown("### 🔍 Data Viewer (Preview 200 baris)")
    st.dataframe(fdf.head(200), use_container_width=True, height=420)

    st.markdown("</div>", unsafe_allow_html=True)
