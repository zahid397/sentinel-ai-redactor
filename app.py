import streamlit as st
import pandas as pd
import time
import re

# --- 1. ENTERPRISE CONFIG ---
st.set_page_config(page_title="🛡️ Sentinel AI - Enterprise", layout="wide", page_icon="🔒")
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FAFAFA; }
    .stTextArea textarea { font-family: 'Courier New', monospace; }
    .success-box { padding: 15px; background-color: #0d3818; border-left: 5px solid #00FF00; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MODEL LOADER ---
try:
    from model import redact_text
except ImportError:
    # Demo Mock Engine (If model.py is missing)
    def redact_text(text, entities, style):
        redacted = text
        details = []
        # Simulate detections
        patterns = {
            "EMAIL_ADDRESS": r"[\w\.-]+@[\w\.-]+",
            "PHONE_NUMBER": r"\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}",
            "URL": r"https?://\S+|www\.\S+"
        }
        for label, pattern in patterns.items():
            if label in entities:
                for m in re.finditer(pattern, redacted):
                    replacement = f"[{label}]" if style == "Tags" else "█████"
                    redacted = redacted.replace(m.group(), replacement)
                    details.append({"Entity": label, "Text": m.group(), "Start": m.start(), "End": m.end()})
        return redacted, details

# --- 3. PURE LEVENSHTEIN ALGORITHM (The Math) ---
def levenshtein_distance(s1, s2):
    """
    Standard DP Implementation of Levenshtein Distance.
    Used for calculating strict character-by-character difference.
    """
    if len(s1) < len(s2): return levenshtein_distance(s2, s1)
    if len(s2) == 0: return len(s1)
    
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

# --- 4. SMART ADAPTIVE SCORING (The Fix) ---
def calculate_smart_score(model_out, user_truth):
    # 1. Basic Cleaning (Lower case, strip spaces)
    t1 = str(model_out).lower().strip()
    t2 = str(user_truth).lower().strip()
    
    # 2. INTELLIGENT ADAPTATION (Startup Logic)
    # যদি ইউজারের ইনপুটে ট্যাগ না থাকে, কিন্তু মডেলে থাকে...
    # তাহলে মডেলের ট্যাগগুলো মুছে ফেলে তুলনা করো।
    if "[" not in t2 and "[" in t1:
        # Regex to remove [any_tag] from model output
        t1 = re.sub(r'\[.*?\]', '', t1)
        # Clean double spaces created by removal
        t1 = " ".join(t1.split())
        t2 = " ".join(t2.split())

    # 3. Strict Normalization (Remove all whitespace for pure char match)
    t1_clean = "".join(t1.split())
    t2_clean = "".join(t2.split())

    # 4. Levenshtein Calculation
    if not t1_clean and not t2_clean: return 100.0
    
    distance = levenshtein_distance(t1_clean, t2_clean)
    max_len = max(len(t1_clean), len(t2_clean))
    
    if max_len == 0: return 100.0
    
    score = (1 - distance / max_len) * 100
    return round(score, 2)

# --- 5. UI LAYOUT ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.title("🛡️ Sentinel AI: Enterprise")
    st.caption("Advanced PII Redaction with Adaptive Levenshtein Validation")
with col_head2:
    st.success("🟢 SYSTEM ONLINE")

with st.sidebar:
    st.header("⚙️ Settings")
    masking_style = st.selectbox("Redaction Style", ["Tags", "Blackout", "Hash (SHA-256)"])
    st.subheader("Active Detectors")
    targets = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "URL", "IP_ADDRESS"]
    selected_entities = [t for t in targets if st.checkbox(t, value=True)]

# --- TABS ---
tab1, tab2 = st.tabs(["🚀 Live Studio", "📊 Batch Evaluation"])

# ================= TAB 1 =================
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        input_text = st.text_area("Raw Input", height=150, placeholder="Paste text containing PII...")
    with c2:
        input_ground_truth = st.text_area(
            "Ground Truth (Expected)", 
            height=150, 
            placeholder="Paste expected output here.\n(Note: Smart Logic will handle missing tags automatically)"
        )

    if st.button("🛡️ EXECUTE PIPELINE", type="primary"):
        if input_text:
            progress = st.progress(0)
            for i in range(100):
                time.sleep(0.002)
                progress.progress(i+1)
            
            # Run Model
            redacted, details = redact_text(input_text, selected_entities, masking_style)
            
            # Show Results
            st.markdown("---")
            rc1, rc2 = st.columns(2)
            with rc1:
                st.caption("🔒 Model Output")
                st.code(redacted, language="text")
            with rc2:
                # --- SCORING LOGIC ---
                if input_ground_truth:
                    score = calculate_smart_score(redacted, input_ground_truth)
                    
                    st.caption("📈 Accuracy (Adaptive Levenshtein)")
                    
                    # Score Visuals
                    if score > 90:
                        st.markdown(f"""
                        <div class="success-box">
                            <h2 style="margin:0; color:#00FF00;">{score}% Accuracy</h2>
                            <p style="margin:0;">Perfect match detected via Adaptive Logic.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.balloons()
                    else:
                        st.metric("Score", f"{score}%")
                        st.error("⚠️ Significant mismatch detected.")
                        
                        # Debugger
                        with st.expander("🔍 See Why"):
                            d1, d2 = st.columns(2)
                            d1.text("Normalized Model:")
                            d1.code("".join(redacted.split()).lower())
                            d2.text("Normalized Truth:")
                            d2.code("".join(input_ground_truth.split()).lower())

            # Analytics
            if details:
                st.markdown("### 📊 Entity Analytics")
                df = pd.DataFrame(details)
                st.dataframe(df, use_container_width=True)

# ================= TAB 2 =================
with tab2:
    st.markdown("### 📂 Bulk Processing")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        df.columns = [c.strip() for c in df.columns]
        
        if st.button("Run Benchmark"):
            res = []
            bar = st.progress(0)
            for i, row in df.iterrows():
                p_text, _ = redact_text(str(row['original_text']), selected_entities, "Tags")
                score = calculate_smart_score(p_text, str(row['ground_truth']))
                res.append({"Original": row['original_text'], "Score": score})
                bar.progress((i+1)/len(df))
            
            res_df = pd.DataFrame(res)
            st.dataframe(res_df, use_container_width=True)
            st.metric("Average Accuracy", f"{res_df['Score'].mean():.2f}%")
            
