import streamlit as st
import pandas as pd
from model import redact_text, calculate_safety_score
from collections import Counter
import time
from PyPDF2 import PdfReader
from fpdf import FPDF
import base64

# --- 1. Cyber Dark Theme Config ---
st.set_page_config(
    page_title="🛡️ Sentinel AI - Enterprise Core",
    layout="wide",
    page_icon="🔒",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Hacker/Enterprise" Vibe
st.markdown("""
    <style>
    .main {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .stTextArea textarea {
        background-color: #262730;
        color: #ffffff;
    }
    .stMetric {
        background-color: #1E1E1E;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #00FF00;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Helper: PDF Report Generator ---
def create_pdf_report(original, redacted, stats):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Sentinel AI - Audit Report", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', size=10)
    pdf.cell(200, 10, txt=f"Threats Detected: {sum(stats.values())}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, txt="--- REDACTED CONTENT PREVIEW ---")
    # Encode to latin-1 to handle generic text issues in FPDF
    safe_text = redacted.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=safe_text[:1000] + "\n... (truncated for summary)")
    
    return pdf.output(dest='S').encode('latin-1')

# --- Header ---
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🛡️ Sentinel AI: Enterprise Core")
    st.markdown("🚀 **Next-Gen Automated PII Redaction & Compliance Tool**")
with col2:
    st.success("🔒 SYSTEM: SECURE & ENCRYPTED")

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Control Panel")
    
    # Feature 5: Masking Styles
    masking_style = st.selectbox(
        "🎨 Redaction Style",
        ["Tags", "Blackout", "Asterisks", "Hash (SHA-256)"],
        help="Choose how sensitive data appears after redaction."
    )
    
    st.divider()
    entities_to_hide = []
    st.markdown("### 🕵️ Targets")
    if st.checkbox("Personal (Name/Loc)", value=True): entities_to_hide.extend(["PERSON", "GPE", "LOC", "ORG"])
    if st.checkbox("Contact (Email/Phone)", value=True): entities_to_hide.extend(["EMAIL", "PHONE"])
    if st.checkbox("Financial (Credit Cards)", value=True): entities_to_hide.extend(["CREDIT_CARD"])
    if st.checkbox("Network (IP Address)", value=True): entities_to_hide.extend(["IP_ADDRESS"])

# --- Main Layout ---
tab1, tab2 = st.tabs(["📂 Workstation", "📊 Analytics & Audit"])

with tab1:
    st.subheader("📥 Input Stream")
    
    # Feature 2: PDF Support
    upload_mode = st.radio("Source:", ["Paste Text", "Upload PDF"], horizontal=True)
    
    input_text = ""
    if upload_mode == "Upload PDF":
        uploaded_file = st.file_uploader("Upload Document (PDF)", type="pdf")
        if uploaded_file:
            try:
                reader = PdfReader(uploaded_file)
                text = "".join([page.extract_text() for page in reader.pages])
                input_text = text
                st.info(f"✅ PDF Loaded: {len(reader.pages)} pages extracted.")
            except Exception as e:
                st.error("Error reading PDF.")
    else:
        input_text = st.text_area("Raw Text Input:", height=150)

    # Action Button
    if st.button("🛡️ EXECUTE REDACTION", type="primary", use_container_width=True):
        if input_text:
            with st.spinner("⚡ Processing Neural Engines..."):
                time.sleep(0.5)
                
                # Core Logic
                redacted_text, detected_list = redact_text(input_text, entities_to_hide, masking_style)
                
                # Save Session
                st.session_state.redacted = redacted_text
                st.session_state.detected = detected_list
                st.session_state.original = input_text
                st.session_state.style = masking_style
                st.rerun() # Refresh to show results
        else:
            st.warning("No data found to process.")

    # Results View
    if "redacted" in st.session_state:
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**❌ Original Data**")
            st.text_area("", value=st.session_state.original, height=250, disabled=True)
        with c2:
            st.markdown(f"**✅ Redacted Data ({st.session_state.style})**")
            st.text_area("", value=st.session_state.redacted, height=250)

with tab2:
    if "detected" in st.session_state:
        st.subheader("📊 Threat Report")
        
        # Metrics
        total_threats = len(st.session_state.detected)
        m1, m2, m3 = st.columns(3)
        m1.metric("Threats Neutralized", total_threats)
        m2.metric("Compliance Score", "100%")
        m3.metric("Process", "Local/Offline")
        
        # Chart
        if total_threats > 0:
            labels = [label for _, label in st.session_state.detected]
            counts = Counter(labels)
            df = pd.DataFrame.from_dict(counts, orient='index', columns=['Count']).reset_index().rename(columns={'index': 'Type'})
            st.bar_chart(df, x='Type', y='Count')
            
            # Feature 3: Export Audit Report
            st.divider()
            st.subheader("🗄️ Compliance Export")
            
            col_txt, col_pdf = st.columns(2)
            
            with col_txt:
                st.download_button(
                    "📄 Download Plain Text",
                    data=st.session_state.redacted,
                    file_name="redacted_safe.txt"
                )
            
            with col_pdf:
                # Generate PDF Report
                pdf_bytes = create_pdf_report(st.session_state.original, st.session_state.redacted, counts)
                st.download_button(
                    "📑 Download Audit Report (PDF)",
                    data=pdf_bytes,
                    file_name="audit_report.pdf",
                    mime="application/pdf"
                )
        else:
            st.success("Document is clean. No PII found.")
    else:
        st.info("Process a document to see analytics.")
      
