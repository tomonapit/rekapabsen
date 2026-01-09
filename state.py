import pandas as pd
from config import DEFAULT_BATAS_MASUK, DEFAULT_BATAS_PULANG

DEFAULT_MANUAL_OVERRIDE_DF = pd.DataFrame(
    columns=["Nama", "NIK", "Tanggal", "Status Manual", "Catatan"]
)

DEFAULT_STATE = {
    "df": None,
    "generated": False,
    "paths": {},
    "out_folder": "",
    "selected_emp_for_preview": "",
    "manual_override_df": DEFAULT_MANUAL_OVERRIDE_DF,
    "batas_masuk": DEFAULT_BATAS_MASUK,
    "batas_pulang": DEFAULT_BATAS_PULANG,
    "logged_in": False,
    "username": "",
}

def init_session_state(st):
    for k, v in DEFAULT_STATE.items():
        if k not in st.session_state:
            st.session_state[k] = v
