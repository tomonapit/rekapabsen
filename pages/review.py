import streamlit as st
from matrix_report import apply_manual_override, build_employee_matrix_row
from analytics import render_heatmap

def page_review():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## 🔎 Review & Matrix Analytics")
    st.write("")

    df = st.session_state.get("df")
    if df is None:
        st.markdown('<div class="alert-warn">⚠️ Belum ada data. Upload dulu.</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    batas_masuk = st.session_state.get("batas_masuk", "07:30:00")
    batas_pulang = st.session_state.get("batas_pulang", "16:00:00")

    # ✅ APPLY OVERRIDE HERE
    df_preview = apply_manual_override(df, st.session_state["manual_override_df"])

    # Debug optional
    # st.write("Override count:", (df_preview["Manual Status"] != "").sum())

    emp_list = sorted(df_preview["Nama"].dropna().unique().tolist())
    selected_emp = st.selectbox("Pilih Pegawai (Matrix Preview)", emp_list)

    st.divider()
    st.markdown("### 📅 Matrix Preview Pegawai")
    mx_emp = build_employee_matrix_row(df_preview, selected_emp, batas_masuk, batas_pulang)
    st.dataframe(mx_emp, use_container_width=True, height=300)

    st.divider()
    st.markdown("### 🔥 Heatmap Jam Masuk")
    render_heatmap(st, df_preview)

    st.markdown("</div>", unsafe_allow_html=True)
