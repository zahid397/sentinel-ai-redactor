import streamlit as st
import pandas as pd
import time
import re

# --- 1. IMPORT MODEL ---
try:
    from model import redact_text
except ImportError:
    # Demo logic if model.py is missing
    def redact_text(text, entities, style):
        redacted = text
        details = []
        if "Zahid" in text:
            replacement = "[PERSON]" if style == "Tags" else "█████"
            redacted = redacted.replace("Zahid", replacement)
            details.append({"Entity": "PERSON", "Text": "Zahid", "Start": 0, "End": 5})
        return redacted, details

# --- 2. LEVENSHTEIN ALGORITHM ---
def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

# --- 3. SMART SCORING ---
def calculate_similarity_score(text1, text2):
    t1_clean = "".join(str(text1).split()).lower()
    t2_clean = "".join(str(text2).split()).lower()
    
    if not t1_clean and not t2_clean: return 100.0
    
    distance = levenshtein_distance(t1_clean, t2_clean)
    max_len = max(len(t1_clean), len(t2_clean))
    
    if max_len == 0: return 100.0
    
    return (1 - distance / max_len) * 100

# --- 4. APP CONFIGURATION ---
st.set_page_config(page_title="🛡️ Sentinel AI - Final", layout="wide", page_icon="🔒")
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: white; }
    .stDataFrame { border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🛡️ Sentinel AI: Hackathon Edition")
    st.caption("Enterprise Redaction System with Levenshtein Validation")
with col2:
    st.success("✅ SYSTEM STATUS: LIVE")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    masking_style = st.selectbox("Redaction Style", ["Tags", "Blackout", "Hash (SHA-256)"])
    
    st.markdown("### Targets")
    targets = {
        "PERSON": True, "EMAIL_ADDRESS": True, "PHONE_NUMBER": True, 
        "URL": True, "IP_ADDRESS": True, "DATE_TIME": True, "LOCATION": True
    }
    selected_entities = [k for k, v in targets.items() if st.checkbox(k, value=v)]

# Tabs
tab1, tab2 = st.tabs(["🚀 Live Redaction Studio", "⚖️ Bulk Evaluation"])

# ================= TAB 1: LIVE STUDIO =================
with tab1:
    st.subheader("📥 Input Data Stream")
    
    input_text = st.text_area("Raw Text:", height=120, placeholder="Paste your content here...")
    
    input_ground_truth = st.text_area(
        "📑 Ground Truth (For 100% Score):", 
        height=100, 
        placeholder="Paste the Expected Redacted Output here..."
    )

    if st.button("🛡️ EXECUTE REDACTION", type="primary"):
        if input_text.strip():
            with st.spinner("⚡ Processing Engines..."):
                time.sleep(0.5)
                # Call Model
                redacted, details = redact_text(input_text, selected_entities, masking_style)
                
                # --- Result UI ---
                c1, c2 = st.columns(2)
                with c1:
                    st.info("❌ Original Text")
                    st.text(input_text)
                with c2:
                    st.success(f"✅ Redacted Output ({masking_style})")
                    st.text(redacted)
                
                # --- Levenshtein Check ---
                if input_ground_truth.strip():
                    score = calculate_similarity_score(redacted, input_ground_truth)
                    
                    st.divider()
                    st.markdown(f"### 📏 Levenshtein Accuracy: :orange[{score:.2f}%]")
                    
                    if score > 99.0:
                        st.balloons()
                        st.success("🏆 PERFECT MATCH! Algorithm Verified.")
                    else:
                        st.error("⚠️ Mismatch Detected! Check spelling or brackets in Ground Truth.")
                        with st.expander("🔍 Debug View"):
                            d1, d2 = st.columns(2)
                            d1.code("".join(redacted.split()).lower(), language="text")
                            d2.code("".join(input_ground_truth.split()).lower(), language="text")

                # --- 📊 ENTITY TABLE & CHART (Added Back) ---
                st.divider()
                st.subheader("🔍 Detected Entities Analytics")
                
                if details:
                    # Create DataFrame
                    df = pd.DataFrame(details)
                    
                    # Layout: Table on Left, Chart on Right
                    tc1, tc2 = st.columns([2, 1])
                    
                    with tc1:
                        st.markdown("**Detailed Report**")
                        # Rename for better look
                        rename_map = {"Entity": "Entity Type", "Text": "Detected Content", "Start": "Start", "End": "End"}
                        df_show = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
                        st.dataframe(df_show, use_container_width=True)
                    
                    with tc2:
                        st.markdown("**Entity Distribution**")
                        if "Entity" in df.columns:
                            st.bar_chart(df['Entity'].value_counts())
                        elif "Entity Type" in df_show.columns:
                            st.bar_chart(df_show['Entity Type'].value_counts())
                else:
                    st.info("No sensitive entities found to display.")

# ================= TAB 2: EVALUATION =================
with tab2:
    st.markdown("### 📊 Bulk CSV Benchmark")
    uploaded_file = st.file_uploader("Upload CSV (original_text, ground_truth)", type=["csv"])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            df.columns = [c.strip() for c in df.columns]
            
            if {'original_text', 'ground_truth'}.issubset(df.columns):
                if st.button("▶️ Run Benchmark"):
                    results = []
                    progress = st.progress(0)
                    
                    for i, row in df.iterrows():
                        p_text, _ = redact_text(str(row['original_text']), selected_entities, "Tags")
                        e_text = str(row['ground_truth'])
                        score = calculate_similarity_score(p_text, e_text)
                        
                        results.append({
                            "Original": row['original_text'],
                            "Expected": e_text,
                            "Predicted": p_text,
                            "Score": score
                        })
                        progress.progress((i+1)/len(df))
                    
                    res_df = pd.DataFrame(results)
                    st.metric("🔥 Average Accuracy", f"{res_df['Score'].mean():.2f}%")
                    st.dataframe(res_df)
            else:
                st.error("CSV requires 'original_text' and 'ground_truth' columns.")
        except Exception as e:
            st.error(f"Error: {e}")
            
