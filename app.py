# VERSION: 20260902_121049
import streamlit as st
import tempfile, os, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="Invoice Processor",
    page_icon="▣",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=IBM+Plex+Sans:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #0a0a0a;
    color: #f0f0f0;
}

.main { background: #0a0a0a; }
.block-container { padding-top: 2rem; max-width: 720px; }

/* Header */
.app-header {
    display: flex; align-items: center; gap: 14px;
    padding-bottom: 20px;
    border-bottom: 1px solid #1e1e1e;
    margin-bottom: 28px;
}
.logo {
    width: 44px; height: 44px;
    background: #F5C518;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px; font-weight: 700; color: #000;
}
.app-title { font-size: 22px; font-weight: 700; color: #fff; }
.app-sub { font-size: 13px; color: #555; margin-top: 2px; }

/* Upload area */
[data-testid="stFileUploader"] {
    background: #111 !important;
    border: 2px dashed #2a2a2a !important;
    border-radius: 12px !important;
    padding: 8px !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #F5C518 !important;
}

/* Process button */
.stButton > button {
    background: #F5C518 !important;
    color: #000 !important;
    font-weight: 700 !important;
    font-size: 16px !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 14px 24px !important;
    width: 100% !important;
    letter-spacing: 0.5px;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: #FFD740 !important;
    transform: translateY(-1px);
}

/* Download button */
[data-testid="stDownloadButton"] > button {
    background: #22C55E !important;
    color: #000 !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
    width: 100% !important;
}

/* Log area */
.log-box {
    background: #080808;
    border: 1px solid #1a1a1a;
    border-radius: 8px;
    padding: 14px 16px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    line-height: 1.7;
    max-height: 300px;
    overflow-y: auto;
    white-space: pre;
    color: #ccc;
}

/* Status badges */
.badge-ok   { color: #22C55E; }
.badge-err  { color: #EF4444; }
.badge-warn { color: #F5C518; }
.badge-grey { color: #555; }

/* Cards */
.info-card {
    background: #111;
    border: 1px solid #1e1e1e;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.stat { font-size: 28px; font-weight: 700; color: #F5C518; }
.stat-label { font-size: 12px; color: #555; margin-top: 2px; }

/* Hide streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
  <div class="logo">▣</div>
  <div>
    <div class="app-title">Invoice Processor</div>
    <div class="app-sub">Amazon Seller — Auto-classify &amp; stamp invoices</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Upload ──────────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Drop your Amazon invoice PDF here",
    type=["pdf"],
    help="Upload your Amazon seller invoice batch PDF"
)

if uploaded:
    size_kb = len(uploaded.getvalue()) / 1024
    size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
    st.markdown(f"""
    <div class="info-card" style="display:flex;align-items:center;gap:14px;">
      <div style="font-size:28px">📄</div>
      <div>
        <div style="font-weight:600;color:#fff">{uploaded.name}</div>
        <div style="font-size:12px;color:#555;margin-top:2px">{size_str}</div>
      </div>
      <div style="margin-left:auto;color:#22C55E;font-weight:700">✓ Ready</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("⚡   PROCESS INVOICES"):
        with st.spinner("Processing…"):
            try:
                from processor import parse_pdf, build_output_pdf, double_check

                # Save uploaded PDF to temp file
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_in:
                    tmp_in.write(uploaded.getvalue())
                    in_path = tmp_in.name

                out_path = in_path.replace(".pdf", "_PROCESSED.pdf")

                # Process
                log_lines = []
                reader, groups = parse_pdf(in_path)
                log_lines.append(f"✓  Found {len(groups)} shipments ({len(reader.pages)} total pages)")

                for g in groups:
                    tag = "✓" if g["confidence"] == "HIGH" else "⚠"
                    log_lines.append(
                        f"   {g['inv_num']:12s} → {g['product']:30s} qty={g['qty']}"
                    )

                problems = double_check(groups)

                if problems:
                    st.warning(f"⚠️ {len(problems)} issue(s) found — review below (output still generated)")
                    for p in problems:
                        st.warning(f"  {p}")

                build_output_pdf(in_path, out_path, groups)

                with open(out_path, "rb") as f:
                    pdf_bytes = f.read()

                os.unlink(in_path)
                os.unlink(out_path)

                # Stats
                from pypdf import PdfReader
                import io
                pages = len(PdfReader(io.BytesIO(pdf_bytes)).pages)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"""
                    <div class="info-card" style="text-align:center">
                      <div class="stat">{len(groups)}</div>
                      <div class="stat-label">SHIPMENTS</div>
                    </div>""", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div class="info-card" style="text-align:center">
                      <div class="stat">{pages}</div>
                      <div class="stat-label">PAGES</div>
                    </div>""", unsafe_allow_html=True)
                with col3:
                    issue_label = f"⚠️ {len(problems)}" if problems else "✓"
                    issue_color = "#F59E0B" if problems else "#22C55E"
                    st.markdown(f"""
                    <div class="info-card" style="text-align:center">
                      <div class="stat" style="color:{issue_color}">{issue_label}</div>
                      <div class="stat-label">{"WARNINGS" if problems else "ZERO ISSUES"}</div>
                    </div>""", unsafe_allow_html=True)

                st.success("✅  Processing complete!")

                out_name = Path(uploaded.name).stem + "_PROCESSED.pdf"
                st.download_button(
                    label="⬇   DOWNLOAD PROCESSED PDF",
                    data=pdf_bytes,
                    file_name=out_name,
                    mime="application/pdf"
                )

                # Show log
                st.markdown("**Log:**")
                log_text = "\n".join(log_lines)
                st.markdown(f'<div class="log-box">{log_text}</div>',
                            unsafe_allow_html=True)

            except Exception as e:
                import traceback
                st.error(f"Error: {e}")
                st.code(traceback.format_exc())

else:
    # Info cards when no file selected
    st.markdown("""
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-top:8px">
      <div class="info-card" style="text-align:center">
        <div style="font-size:28px;margin-bottom:8px">🏷</div>
        <div style="font-weight:600;color:#fff;font-size:13px">Auto Classify</div>
        <div style="font-size:11px;color:#555;margin-top:4px">150+ product codes</div>
      </div>
      <div class="info-card" style="text-align:center">
        <div style="font-size:28px;margin-bottom:8px">✅</div>
        <div style="font-weight:600;color:#fff;font-size:13px">Zero Mistakes</div>
        <div style="font-size:11px;color:#555;margin-top:4px">Double-check validator</div>
      </div>
      <div class="info-card" style="text-align:center">
        <div style="font-size:28px;margin-bottom:8px">⭐</div>
        <div style="font-weight:600;color:#fff;font-size:13px">Multi-Qty Stars</div>
        <div style="font-size:11px;color:#555;margin-top:4px">Staff alert system</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-card" style="margin-top:4px">
      <div style="font-size:12px;color:#555;line-height:2">
        <span style="color:#F5C518;font-weight:700">How it works:</span><br>
        1. Upload your Amazon invoice batch PDF<br>
        2. Click <b style="color:#F5C518">⚡ PROCESS INVOICES</b><br>
        3. Download the stamped output PDF<br><br>
        <span style="color:#F5C518;font-weight:700">Box format on every invoice:</span><br>
        ████████████████████████████<br>
        █  PRODUCT CODE  |  QTY: X  █<br>
        █    ★ ★ ★  (if qty &gt; 1)    █<br>
        ████████████████████████████
      </div>
    </div>
    """, unsafe_allow_html=True)
