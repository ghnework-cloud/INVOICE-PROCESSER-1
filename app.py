import streamlit as st
import tempfile, os, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="Invoice Processor",
    page_icon="📦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=IBM+Plex+Sans:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; background-color: #0a0a0a; color: #f0f0f0; }
.main { background: #0a0a0a; }
.block-container { padding-top: 2rem; max-width: 720px; }
.app-header { display: flex; align-items: center; gap: 14px; padding-bottom: 20px; border-bottom: 1px solid #1e1e1e; margin-bottom: 28px; }
.logo { width: 44px; height: 44px; background: #F5C518; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: 700; color: #000; }
.app-title { font-size: 22px; font-weight: 700; color: #fff; }
.app-sub { font-size: 14px; color: #555; }
.stButton > button { background: #F5C518 !important; color: #000 !important; font-weight: 700 !important; border: none !important; border-radius: 6px !important; padding: 0.6rem 1.4rem !important; font-size: 15px !important; }
.log-box { background: #111; border: 1px solid #222; border-radius: 8px; padding: 1rem; font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #aaa; max-height: 300px; overflow-y: auto; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="app-header">
  <div class="logo">📦</div>
  <div>
    <div class="app-title">Invoice Processor</div>
    <div class="app-sub">Amazon Seller — Auto-classify &amp; stamp invoices</div>
  </div>
</div>
""", unsafe_allow_html=True)

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

    if st.button("▶  PROCESS INVOICES"):
        with st.spinner("Processing…"):
            try:
                from processor import parse_pdf, build_output_pdf, double_check

                # Save uploaded PDF to temp file
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_in:
                    tmp_in.write(uploaded.getvalue())
                    in_path = tmp_in.name

                out_path = in_path.replace(".pdf", "_PROCESSED.pdf")

                # Process — parse_pdf returns list of invoice dicts
                groups = parse_pdf(open(in_path, 'rb').read())

                log_lines = []
                log_lines.append(f"✓  Found {len(groups)} shipments ({sum(1 for g in groups)} total pages)")

                for g in groups:
                    tag = "✓" if g["code"] != "UNCLASSIFIED" else "✗"
                    log_lines.append(
                        f"  {tag}  {g['inv_num']:12s} → {g['product']:30s} qty={g['qty']}"
                    )

                problems = double_check(groups)

                if problems:
                    st.warning(f"⚠️ {len(problems)} issue(s) found — review below (output still generated)")
                    for p in problems:
                        st.warning(f"  {p}")

                build_output_pdf(in_path, out_path, groups)

                st.success(f"✅ Processing complete!")
                log_lines.append(f"\n{'─'*60}")
                log_lines.append(f"Found {len(groups)} elements ({len(groups)} total pages)")
                for g in groups:
                    log_lines.append(f"  {g['inv_num']:12s}  {g['product']:30s}  qty={g['qty']}")

                st.markdown(f"<div class='log-box'>{'<br>'.join(log_lines)}</div>", unsafe_allow_html=True)

                with open(out_path, "rb") as f:
                    st.download_button(
                        "⬇ DOWNLOAD PROCESSED PDF",
                        data=f.read(),
                        file_name=f"{uploaded.name.replace('.pdf', '')}_PROCESSED.pdf",
                        mime="application/pdf"
                    )

                os.unlink(in_path)
                os.unlink(out_path)

            except Exception as e:
                st.error(f"Error: {e}")
                import traceback
                st.code(traceback.format_exc())
