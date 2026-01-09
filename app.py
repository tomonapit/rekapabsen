import streamlit as st
import pandas as pd

from config import APP_TITLE, APP_USERS
from state import init_session_state
from ui import inject_css, render_topbar

from pages.dashboard import page_dashboard
from pages.upload import page_upload
from pages.review import page_review
from pages.generate import page_generate
from pages.download import page_download
from pages.verify import page_verify



# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(
    page_title=f"{APP_TITLE} | RSUP Jayapura",
    layout="wide",
    page_icon="🏥",
    initial_sidebar_state="expanded",
)

inject_css()
init_session_state(st)


# =========================================================
# AUTH UI
# =========================================================
def login_ui():
    st.markdown("## 🔐 Secure Access")

    u = st.text_input("Username", value="", key="login_username")
    p = st.text_input("Password", value="", type="password", key="login_password")

    if st.button("Masuk", use_container_width=True, key="btn_login"):
        if u in APP_USERS and APP_USERS[u] == p:
            st.session_state["logged_in"] = True
            st.session_state["username"] = u
            st.success("✅ Login berhasil")
            st.rerun()
        else:
            st.error("❌ Username atau password salah")


def logout():
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.rerun()


if not st.session_state.get("logged_in", False):
    login_ui()
    st.stop()


# =========================================================
# TOPBAR + LOGOUT
# =========================================================
colL, colR = st.columns([7, 2.2])

with colL:
    render_topbar(st.session_state.get("username", ""))

with colR:
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button("🚪 Logout", use_container_width=True, key="btn_logout_top"):
        logout()
    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# SIDEBAR: POLICY + ENTERPRISE OVERRIDE
# =========================================================
with st.sidebar:
    st.markdown("## ⚙️ Enterprise Control Panel")

    # ---------------------------
    # PERIODE & POLICY
    # ---------------------------
    st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
    st.markdown("### Periode & Policy")

    st.session_state["use_gabung"] = st.checkbox(
        "Buat PDF Gabungan",
        value=st.session_state.get("use_gabung", True),
        key="sb_use_gabung",
    )

    st.session_state["periode"] = st.text_input(
        "Periode (contoh: Desember 2025)",
        value=st.session_state.get("periode", ""),
        key="sb_periode",
    )

    st.session_state["catatan"] = st.text_area(
        "Catatan (opsional)",
        value=st.session_state.get("catatan", ""),
        key="sb_catatan",
    )

    st.session_state["batas_masuk"] = st.text_input(
        "Batas Masuk Normal",
        value=st.session_state.get("batas_masuk", "07:30:00"),
        key="sb_batas_masuk",
    )

    st.session_state["batas_pulang"] = st.text_input(
        "Batas Pulang Normal",
        value=st.session_state.get("batas_pulang", "16:00:00"),
        key="sb_batas_pulang",
    )

    st.caption("TL1: 1-30 | TL2: 31-60 | TL3: >= 61 (fixed)")
    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------
    # MANUAL OVERRIDE ENTERPRISE
    # ---------------------------
    st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
    st.markdown("### Manual Override (Enterprise)")

    if "manual_override_df" not in st.session_state:
        st.session_state["manual_override_df"] = pd.DataFrame(
            columns=["Nama", "NIK", "Tanggal", "Status Manual", "Catatan"]
        )

    df_manual = st.session_state["manual_override_df"]
    df_data = st.session_state.get("df")

    # Import override from excel
    st.markdown("#### 📥 Import Override (Excel)")
    override_file = st.file_uploader("Upload Excel Override", type=["xlsx"], key="upload_override_excel")
    if override_file:
        try:
            df_import = pd.read_excel(override_file)
            df_import.columns = [c.strip() for c in df_import.columns]
            required = {"Nama", "Tanggal", "Status Manual"}
            if not required.issubset(set(df_import.columns)):
                st.error("Excel wajib punya kolom: Nama, Tanggal, Status Manual (NIK & Catatan opsional)")
            else:
                if "NIK" not in df_import.columns:
                    df_import["NIK"] = ""
                if "Catatan" not in df_import.columns:
                    df_import["Catatan"] = ""

                df_import["Tanggal"] = pd.to_datetime(df_import["Tanggal"], errors="coerce").dt.date
                df_import["Status Manual"] = df_import["Status Manual"].astype(str).str.upper().str.strip()
                df_import = df_import.dropna(subset=["Tanggal"])
                st.session_state["manual_override_df"] = pd.concat([df_manual, df_import], ignore_index=True)
                st.success(f"✅ Import sukses: {len(df_import)} baris override masuk.")
        except Exception as e:
            st.error(f"Gagal import override: {e}")

    st.divider()

    # Add override manual
    st.markdown("#### ➕ Tambah Override Manual")

    if df_data is not None and "Nama" in df_data.columns:
        pegawai_list = sorted(df_data["Nama"].dropna().unique().tolist())
        nama_manual = st.selectbox("Nama Pegawai", pegawai_list, key="mo_nama_select")
    else:
        nama_manual = st.text_input("Nama Pegawai", placeholder="contoh: Andi", key="mo_nama_input")

    nik_manual = st.text_input("NIK (opsional)", value="", key="mo_nik")
    tanggal_manual = st.date_input("Tanggal Override", key="mo_tgl")
    status_manual = st.selectbox("Status Manual", ["S", "I", "C", "DL"], key="mo_status")
    catatan_manual = st.text_area("Catatan", placeholder="opsional", key="mo_catatan")

    if st.button("✅ Simpan Override", use_container_width=True, key="btn_add_override"):
        if not str(nama_manual).strip():
            st.error("Nama wajib diisi.")
        else:
            nik_fix = str(nik_manual).strip()

            # auto nik
            if (not nik_fix) and df_data is not None and "NIK" in df_data.columns and "Nama" in df_data.columns:
                try:
                    nik_fix = (
                        df_data[df_data["Nama"] == nama_manual]["NIK"]
                        .dropna()
                        .astype(str)
                        .iloc[0]
                    )
                except Exception:
                    nik_fix = ""

            new_row = {
                "Nama": str(nama_manual).strip(),
                "NIK": nik_fix,
                "Tanggal": tanggal_manual,
                "Status Manual": status_manual,
                "Catatan": str(catatan_manual).strip(),
            }

            st.session_state["manual_override_df"] = pd.concat(
                [st.session_state["manual_override_df"], pd.DataFrame([new_row])],
                ignore_index=True,
            )
            st.success("✅ Override tersimpan!")

    st.divider()

    # View + delete override per row
    if not st.session_state["manual_override_df"].empty:
        st.markdown("#### 📌 Daftar Override (Edit / Hapus)")

        df_view = st.session_state["manual_override_df"].copy()
        df_view["Tanggal"] = pd.to_datetime(df_view["Tanggal"], errors="coerce").dt.date

        # show editable table
        edited = st.data_editor(
            df_view,
            use_container_width=True,
            height=250,
            num_rows="dynamic",
            key="editor_override_table",
        )

        # apply edits
        if st.button("💾 Simpan Perubahan Override", use_container_width=True, key="btn_save_override_edit"):
            st.session_state["manual_override_df"] = edited
            st.success("✅ Perubahan override tersimpan!")

        # delete row
        idx_del = st.number_input("Hapus Override Index (lihat nomor baris)", min_value=0, step=1, key="del_override_idx")
        if st.button("🗑️ Hapus Baris Override", use_container_width=True, key="btn_delete_override_row"):
            try:
                st.session_state["manual_override_df"] = st.session_state["manual_override_df"].drop(index=int(idx_del)).reset_index(drop=True)
                st.success("✅ Baris override berhasil dihapus.")
            except Exception:
                st.error("Index tidak valid.")

        if st.button("🧹 Reset Semua Override", use_container_width=True, key="btn_reset_override"):
            st.session_state["manual_override_df"] = st.session_state["manual_override_df"].iloc[0:0]
            st.warning("Override direset (kosong).")

    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------
    # LOGOUT BACKUP
    # ---------------------------
    st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
    st.markdown("### Logout")
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button("🚪 Logout (Sidebar)", use_container_width=True, key="btn_logout_sidebar"):
        logout()
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# MAIN NAVIGATION
# =========================================================
nav = st.radio(
    "Navigation",
   ["📊 Dashboard", "📤 Upload", "🔎 Review & Analytics", "⚡ Generate Report", "📥 Download & Arsip", "✅ Verifikasi QR"]
,
    horizontal=True,
    key="nav_main",
)

st.write("")

# =========================================================
# ROUTING PAGES
# =========================================================
if nav == "📊 Dashboard":
    page_dashboard()
elif nav == "📤 Upload":
    page_upload()
elif nav == "🔎 Review & Analytics":
    page_review()
elif nav == "⚡ Generate Report":
    page_generate()
elif nav == "📥 Download & Arsip":
    page_download()
elif nav == "✅ Verifikasi QR":
    page_verify()

