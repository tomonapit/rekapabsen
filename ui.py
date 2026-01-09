import streamlit as st
from config import APP_TITLE, APP_SUBTITLE, APP_ORG

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

:root{
    --bg:#0b1220;
    --card:#0f172a;
    --text:#f8fafc;
    --muted:rgba(248,250,252,0.78);
    --line:rgba(255,255,255,0.12);
    --accent:#4f46e5;
}

html, body, [class*="css"] {
    font-family: 'Inter', system-ui !important;
    background: var(--bg) !important;
    color: var(--text) !important;
}

.block-container {
    padding-top: 1rem !important;
    padding-left: 1.4rem !important;
    padding-right: 1.4rem !important;
}

/* Alerts (restored) */
.alert-info {
    background: rgba(79,70,229,0.18);
    border: 1px solid rgba(79,70,229,0.32);
    padding: 14px 16px;
    border-radius: 16px;
    color: var(--text);
}
.alert-warn {
    background: rgba(245,158,11,0.18);
    border: 1px solid rgba(245,158,11,0.32);
    padding: 14px 16px;
    border-radius: 16px;
    color: var(--text);
}
.alert-success {
    background: rgba(34,197,94,0.18);
    border: 1px solid rgba(34,197,94,0.32);
    padding: 14px 16px;
    border-radius: 16px;
    color: var(--text);
}

.topbar {
    background: linear-gradient(135deg, #111827 0%, #0f172a 50%, #0b1220 100%);
    padding: 22px 26px;
    border-radius: 20px;
    border: 1px solid var(--line);
    box-shadow: 0 22px 70px rgba(0,0,0,0.35);
    margin-bottom: 16px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:18px;
}
.topbar h1 {
    font-size: 30px;
    margin:0;
    font-weight: 950;
    letter-spacing: -0.6px;
    color: var(--text);
}
.topbar p {
    margin: 6px 0 0 0;
    color: var(--muted);
    font-size: 13px;
}
.badge {
    background: rgba(255,255,255,0.10);
    border: 1px solid var(--line);
    padding: 7px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
    color: var(--text);
}

.card {
    background: rgba(255,255,255,0.04);
    border-radius: 20px;
    border: 1px solid var(--line);
    box-shadow: 0 18px 55px rgba(0,0,0,0.28);
    padding: 18px;
}
.glass {
    background: linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.06));
    border-radius: 20px;
    border: 1px solid var(--line);
    box-shadow: 0 18px 70px rgba(0,0,0,0.30);
    backdrop-filter: blur(10px);
    padding: 18px;
}

.logout-btn button {
    background: linear-gradient(135deg, #ef4444, #fb7185) !important;
}
.pdf-frame iframe { border-radius: 18px !important; border: none !important; }
</style>
"""

def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)

def render_topbar(username: str):
    st.markdown(
        f"""
        <div class="topbar">
            <div>
                <h1>{APP_TITLE} <span class="badge">{APP_ORG}</span></h1>
                <p>{APP_SUBTITLE} • Enterprise Dashboard Edition</p>
            </div>
            <div>
                <span class="badge">User: {username}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
