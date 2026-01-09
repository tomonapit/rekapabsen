import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def safe_dt(x):
    try:
        return pd.to_datetime(x, errors="coerce")
    except:
        return pd.NaT


def compute_kpi(df: pd.DataFrame, manual_df=None, batas_masuk="07:30:00"):
    if df is None or df.empty:
        return {
            "total_rows": 0,
            "pegawai": 0,
            "hadir": 0,
            "terlambat": 0,
            "absen": 0,
            "override": len(manual_df) if manual_df is not None else 0,
        }

    df = df.copy()

    total_rows = len(df)
    pegawai = df["Nama"].nunique() if "Nama" in df.columns else 0

    if "Scan Masuk" not in df.columns:
        df["Scan Masuk"] = None

    hadir = int(df["Scan Masuk"].notna().sum())
    absen = int(df["Scan Masuk"].isna().sum())

    terlambat = 0
    try:
        masuk_dt = safe_dt(df["Scan Masuk"])
        masuk_str = masuk_dt.dt.strftime("%H:%M:%S")
        batas_str = str(batas_masuk).strip()

        if len(batas_str) == 5:
            batas_str = batas_str + ":00"
        if len(batas_str) != 8:
            batas_str = "07:30:00"

        terlambat = int((masuk_str > batas_str).sum())
    except Exception:
        terlambat = 0

    override_count = len(manual_df) if manual_df is not None else 0

    return {
        "total_rows": int(total_rows),
        "pegawai": int(pegawai),
        "hadir": int(hadir),
        "terlambat": int(terlambat),
        "absen": int(absen),
        "override": int(override_count),
    }


def build_daily_trend(df: pd.DataFrame):
    if df is None or df.empty or "Tanggal" not in df.columns:
        return pd.DataFrame()

    tmp = df.copy()
    tmp["Tanggal"] = safe_dt(tmp["Tanggal"]).dt.date

    if "Scan Masuk" in tmp.columns:
        tmp["Hadir"] = safe_dt(tmp["Scan Masuk"]).notna().astype(int)
    else:
        tmp["Hadir"] = 0

    trend = tmp.groupby("Tanggal")["Hadir"].sum().reset_index().sort_values("Tanggal")
    return trend


def build_status_distribution(df: pd.DataFrame):
    if df is None or df.empty:
        return pd.DataFrame(columns=["Status", "Jumlah"])

    if "Status" in df.columns:
        dist = df["Status"].astype(str).str.upper().value_counts().reset_index()
        dist.columns = ["Status", "Jumlah"]
        return dist

    tmp = df.copy()
    if "Scan Masuk" in tmp.columns:
        tmp["Status"] = tmp["Scan Masuk"].apply(lambda x: "H" if pd.notna(x) else "A")
    else:
        tmp["Status"] = "A"

    dist = tmp["Status"].value_counts().reset_index()
    dist.columns = ["Status", "Jumlah"]
    return dist


def render_heatmap(*args):
    """
    Bisa dipanggil:
        render_heatmap(df)
        render_heatmap(st, df)

    Jika dikasih st -> langsung st.pyplot(fig)
    Jika tanpa st -> return fig
    """

    st_obj = None
    df = None

    if len(args) == 1:
        df = args[0]
    elif len(args) == 2:
        st_obj = args[0]
        df = args[1]
    else:
        return None

    if df is None or df.empty:
        return None

    if "Tanggal" not in df.columns or "Scan Masuk" not in df.columns:
        return None

    tmp = df.dropna(subset=["Tanggal", "Scan Masuk"]).copy()
    tmp["Tanggal"] = pd.to_datetime(tmp["Tanggal"], errors="coerce")
    tmp["ScanMasuk_dt"] = pd.to_datetime(tmp["Scan Masuk"], errors="coerce")
    tmp = tmp.dropna(subset=["ScanMasuk_dt"])

    if tmp.empty:
        return None

    tmp["Hour"] = tmp["ScanMasuk_dt"].dt.hour
    tmp["Day"] = tmp["Tanggal"].dt.day_name()

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    tmp["Day"] = pd.Categorical(tmp["Day"], categories=day_order, ordered=True)

    pivot = tmp.pivot_table(index="Day", columns="Hour", values="Nama", aggfunc="count", fill_value=0)

    fig = plt.figure(figsize=(12.8, 4.6))
    plt.imshow(pivot.values, aspect="auto")
    plt.yticks(range(len(pivot.index)), pivot.index)
    plt.xticks(range(len(pivot.columns)), pivot.columns)
    plt.title("Heatmap Kehadiran (Hari vs Jam Scan Masuk)", pad=12, fontweight="bold")
    plt.xlabel("Jam")
    plt.ylabel("Hari")
    plt.colorbar(label="Jumlah Scan")
    plt.tight_layout()

    if st_obj is not None:
        st_obj.pyplot(fig)
        return None

    return fig


