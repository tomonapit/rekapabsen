import base64
import pandas as pd
import streamlit.components.v1 as components

def safe_dt(x):
    return pd.to_datetime(x, errors="coerce")

def render_pdf(pdf_path, height=880):
    with open(pdf_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")

    pdf_display = f"""
    <div class="pdf-frame">
        <iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="{height}"></iframe>
    </div>
    """
    components.html(pdf_display, height=height + 30, scrolling=True)
