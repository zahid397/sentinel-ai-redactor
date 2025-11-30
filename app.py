import streamlit as st
import pandas as pd
import time
import re

# --- 1. IMPORT MODEL ---
# আপনার model.py ফাইলটি প্রজেক্ট ফোল্ডারে থাকতে হবে
try:
    from model import redact_text
except ImportError:
    # যদি model.py না পায়, তবে ডেমো হিসেবে এই ফাংশন চলবে (যাতে এরর না দেয়)
    def redact_text(text, entities, style):
        # Demo logic just for testing if file is missing
        redacted = text
        details = []
        if "Zahid" in text:
            replacement = "[PERSON]" if style == "Tags" else "█████"
            redacted = redacted.replace("Zahid", replacement)
            details.append({"Entity": "PERSON", "Text": "Zahid", "Start": 0, "End": 5})
        return redacted, details

# --- 2. LEVENSHTEIN ALGORITHM (Standard Logic) ---
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

# --- 3. SMART SCORING (With Normalization) ---
def calculate_similarity_score(text1, text2):
    # সব স্পেস এবং নিউ লাইন মুছে ফেলছি তুলনা করার জন্য
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
    st.title("🛡️ Sentinel AI")
    st.caption("Enterprise Redaction System with Levenshtein Validation")
with col2:
    st.success("✅ SYSTEM LIVE")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    masking_style = st.selectbox("Redaction Style", ["Tags", "Blackout", "Hash (SHA-256)"])
    
    st.markdown("### Targets")
    targets = {"PERSON": True, "EMAIL_ADDRESS": True, "PHONE_NUMBER": True, "URL": True}
    selected_entities = [k for k, v in targets.items() if st.checkbox(k, value=v)]

# Tabs
tab1, tab2 = st.tabs(["🚀 Live Redaction", "⚖️ Bulk Evaluation"])

# ================= TAB 1: LIVE STUDIO =================
with tab1:
    st.subheader("📥 Input Data Stream")
    
    # ইনপুট
    input_text = st.text_area("Raw Text:", height=100, placeholder="Example: Hello Zahid")
    
    # Ground Truth (Debug এর জন্য খুবই জরুরি)
    input_ground_truth = st.text_area(
        "📑 Ground Truth (Expected):", 
        height=100, 
        placeholder="Example: Hello [PERSON] (If style is Tags)"
    )

    if st.button("🛡️ RUN REDACTION", type="primary"):
        if input_text.strip():
            # মডেল রান করা
            redacted, details = redact_text(input_text, selected_entities, masking_style)
            
            # রেজাল্ট দেখানো
            c1, c2 = st.columns(2)
            with c1:
                st.info("Original")
                st.text(input_text)
            with c2:
                st.success(f"Redacted ({masking_style})")
                st.text(redacted) # st.code এর বদলে st.text দিলে কপি করতে সুবিধা হয়
            
            # --- 🔍 DEBUGGER & SCORING ---
            if input_ground_truth.strip():
                score = calculate_similarity_score(redacted, input_ground_truth)
                
                st.divider()
                st.markdown(f"### 📏 Accuracy Score: :orange[{score:.2f}%]")
                
                if score == 100.0:
                    st.balloons()
                    st.success("🏆 PERFECT MATCH! Your logic is flawless.")
                else:
                    # ১০০% না হলে লাল বক্স দেখাবে
                    st.error("⚠️ Mismatch Detected! See below to fix it:")
                    
                    # পাশাপাশি তুলনা (Comparison View)
                    d1, d2 = st.columns(2)
                    
                    # আমরা স্পেস মুছে ক্লিন করে দেখাবো কম্পিউটার কী দেখছে
                    clean_model = "".join(redacted.split()).lower()
                    clean_truth = "".join(input_ground_truth.split()).lower()
                    
                    with d1:
                        st.markdown("**Computer sees (Model Output):**")
                        st.code(clean_model, language="text")
                    with d2:
                        st.markdown("**Computer sees (Your Input):**")
                        st.code(clean_truth, language="text")
                        
                    st.warning("💡 Tip: উপরের দুটি বক্সের লেখা হুবহু এক হতে হবে। ব্র্যাকেট `[]` বা বানানে ভুল আছে কিনা দেখুন।")

# ================= TAB 2: EVALUATION =================
with tab2:
    st.markdown("### 📊 Bulk CSV Test")
    uploaded_file = st.file_uploader("Upload CSV (cols: original_text, ground_truth)", type=["csv"])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            df.columns = [c.strip() for c in df.columns]
            
            if {'original_text', 'ground_truth'}.issubset(df.columns):
                if st.button("▶️ Start Benchmark"):
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
                    st.dataframe(res_df)
                    st.metric("Average Accuracy", f"{res_df['Score'].mean():.2f}%")
            else:
                st.error("CSV must have 'original_text' and 'ground_truth' columns.")
        except Exception as e:
            st.error(f"Error: {e}")
            
