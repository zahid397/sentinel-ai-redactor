import streamlit as st
import os
import sys
import subprocess

# --- 🚀 AUTO-FIX: Download spaCy Model at Runtime ---
# This prevents "App in the oven" hang on Streamlit Cloud by installing the model
# only when the app actually starts, not during the build process.
try:
    import spacy
    # Check if model is present
    nlp = spacy.load("en_core_web_sm")
except (OSError, ImportError):
    print("📦 Downloading spaCy model (en_core_web_sm)...")
    # Force download using subprocess to ensure correct environment
    subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    print("✅ Model installed successfully!")

# ----------------------------------------------------

import pandas as pd
from model import redact_text, calculate_safety_score
from collections import Counter
import time
from PyPDF2 import PdfReader
from fpdf import FPDF

# --- Page Config ---
st.set_page_config(page_title="🛡️ Sentinel AI - Enterprise Security", layout="wide", page_icon="🔒")

# --- Custom CSS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stAlert { border-radius: 10px; }
    .metric-box {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- Header ---
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🛡️ Sentinel AI: Enterprise Data Redaction")
    st.markdown("**Offline-First Secure Redaction System** | *Hybrid AI + Regex Engine*")
with col2:
    st.success("✅ Status: OFFLINE & SECURE")

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Masking Styles
    masking_style = st.selectbox(
        "🎨 Redaction Style",
        ["Tags", "Blackout", "Asterisks", "Hash (SHA-256)"],
        help="Choose how sensitive data appears after redaction."
    )
    
    st.divider()
    entities_to_hide = []
    
    st.markdown("### 👤 Personal Info")
    if st.checkbox("Names (PERSON)", value=True): entities_to_hide.append("PERSON")
    if st.checkbox("Locations (GPE/LOC)", value=True): entities_to_hide.extend(["GPE", "LOC"])
    if st.checkbox("Organizations (ORG)", value=True): entities_to_hide.append("ORG")
    
    st.markdown("### 💳 Sensitive Data")
    if st.checkbox("Emails", value=True): entities_to_hide.append("EMAIL_ADDRESS")
    if st.checkbox("Phone Numbers", value=True): entities_to_hide.append("PHONE_NUMBER")
    if st.checkbox("Credit Cards", value=True): entities_to_hide.append("CREDIT_CARD")
    if st.checkbox("IP Addresses", value=True): entities_to_hide.append("IP_ADDRESS")
    if st.checkbox("Dates/Times", value=True): entities_to_hide.append("DATE_TIME")
    if st.checkbox("URLs", value=True): entities_to_hide.append("URL")
    
    st.divider()
    st.caption("Powered by spaCy & Python")

# --- Main Tabs ---
tab1, tab2 = st.tabs(["📄 Live Redaction", "📏 Accuracy Benchmark"])

# ================= TAB 1: LIVE REDACTION =================
with tab1:
    st.subheader("📄 Secure Document Processor")
    
    # PDF vs Text Input
    input_mode = st.radio("Input Source:", ["Paste Text", "Upload PDF"], horizontal=True)
    
    input_text = ""
    
    if input_mode == "Upload PDF":
        uploaded_pdf = st.file_uploader("Upload PDF Document", type=["pdf"])
        if uploaded_pdf:
            try:
                reader = PdfReader(uploaded_pdf)
                text_list = []
                for page in reader.pages:
                    text_list.append(page.extract_text())
                input_text = "\n".join(text_list)
                st.info(f"✅ PDF Loaded: {len(reader.pages)} pages extracted.")
            except Exception as e:
                st.error(f"Error reading PDF: {e}")
    else:
        input_text = st.text_area("Input Stream:", height=150, placeholder="Paste confidential text here (Emails, Logs, Contracts)...")

    if st.button("🔒 Process & Redact", type="primary", use_container_width=True):
        if input_text:
            with st.spinner("⚡ Sentinel AI is processing..."):
                # --- ⏱️ Performance Timer Start ---
                start_time = time.time()
                
                # Run Model
                redacted_text, detected_list = redact_text(input_text, entities_to_hide, masking_style)
                safety_score = calculate_safety_score(input_text, redacted_text)
                
                # --- ⏱️ Performance Timer End ---
                end_time = time.time()
                processing_time = round(end_time - start_time, 4)
                
                # Metrics Logic
                num_detections = len(detected_list)
                risk_level = "CRITICAL" if num_detections > 5 else "MODERATE" if num_detections > 0 else "SAFE"
                risk_color = "red" if num_detections > 5 else "orange" if num_detections > 0 else "green"

                # Save State
                st.session_state.redacted = redacted_text
                st.session_state.detected = detected_list
                st.session_state.score = safety_score
                st.session_state.risk_level = risk_level
                st.session_state.risk_color = risk_color
                st.session_state.proc_time = processing_time
                st.session_state.original = input_text
        else:
            st.warning("⚠️ Input data required.")

    # --- Results ---
    if "redacted" in st.session_state:
        st.divider()
        
        # Top Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🔍 Threats Detected", len(st.session_state.detected))
        m2.markdown(f"#### Risk: :{st.session_state.risk_color}[{st.session_state.risk_level}]")
        m3.metric("🛡️ Privacy Score", f"{st.session_state.score}/100")
        m4.metric("⚡ Processing Time", f"{st.session_state.proc_time}s")

        # Detailed Comparison
        c1, c2 = st.columns(2)
        with c1:
            st.caption("❌ Unsafe Original")
            st.text_area("Original", value=st.session_state.original, height=250, disabled=True)
        with c2:
            st.caption(f"✅ Secure Output ({masking_style})")
            st.text_area("Redacted", value=st.session_state.redacted, height=250)

        # Download Button
        st.download_button(
            label="📥 Download Safe Text",
            data=st.session_state.redacted,
            file_name="safe_redacted.txt",
            mime="text/plain"
        )

        # --- Detailed Redaction Log ---
        with st.expander("🔍 View Redaction Log (Transparency Report)"):
            if st.session_state.detected:
                # Convert list of dicts to DataFrame for better view
                log_df = pd.DataFrame(st.session_state.detected)
                st.dataframe(log_df, use_container_width=True)
            else:
                st.info("No entities needed redaction.")

        # Analytics Chart
        st.divider()
        st.subheader("📊 Threat Vector Analytics")
        if st.session_state.detected:
            # Extract labels from the list of dicts
            labels = [item['Entity'] for item in st.session_state.detected]
            counts = Counter(labels)
            
            # Create DataFrame
            df = pd.DataFrame.from_dict(counts, orient='index', columns=['Count'])
            df.index.name = 'Entity Type'
            
            col_chart, col_data = st.columns([2, 1])
            with col_chart:
                st.bar_chart(df) 
            with col_data:
                st.dataframe(df, use_container_width=True)

# ================= TAB 2: ACCURACY BENCHMARK =================
with tab2:
    st.subheader("📏 System Accuracy Validation")
    st.markdown("Upload a labeled CSV (`text`, `expected`) to benchmark performance against ground truth.")

    uploaded_file = st.file_uploader("Upload Test Dataset", type=["csv"])

    if uploaded_file is not None:
        eval_df = pd.read_csv(uploaded_file)

        if "text" in eval_df.columns and "expected" in eval_df.columns:
            st.success(f"✅ Dataset Loaded: {len(eval_df)} samples.")
            
            if st.button("▶️ Run Benchmark"):
                with st.spinner("Running batch evaluation..."):
                    progress_bar = st.progress(0)
                    preds = []
                    
                    from model import calculate_similarity # Import helper
                    
                    results = []
                    
                    for i, row in eval_df.iterrows():
                        # Run model
                        red, _ = redact_text(str(row['text']), entities_to_hide, "Tags")
                        preds.append(red)
                        
                        # Similarity check
                        sim = calculate_similarity(red, str(row['expected']))
                        match = "✅" if sim > 95 else "⚠️"
                        
                        results.append({
                            "Original": row['text'],
                            "Expected": row['expected'],
                            "Predicted": red,
                            "Similarity": f"{sim:.1f}%",
                            "Status": match
                        })
                        
                        progress_bar.progress((i + 1) / len(eval_df))

                    eval_df["predicted"] = preds
                    
                    # Create Result DF
                    res_df = pd.DataFrame(results)
                    
                    # Calculate Average Accuracy based on Similarity
                    # Convert string percentage back to float for calculation
                    avg_acc = res_df["Similarity"].str.rstrip('%').astype(float).mean()
                    
                    st.divider()
                    ac1, ac2 = st.columns(2)
                    ac1.metric("✅ Average System Accuracy", f"{avg_acc:.2f}%")
                    ac2.metric("📂 Samples Tested", len(eval_df))
                    
                    st.subheader("📝 Evaluation Report")
                    st.dataframe(res_df, use_container_width=True)
        else:
            st.error("Invalid CSV format. Columns must be: `text`, `expected`")
            
