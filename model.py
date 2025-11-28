import spacy
import re
import hashlib

# --- 🟢 UPDATED: Safe Model Loading Logic ---
def load_nlp():
    """
    Attempts to load the efficient English model.
    Falls back to a blank model to prevent App Crash in Cloud.
    """
    try:
        # Cloud/Hackathon এর জন্য 'sm' (Small) মডেল বেস্ট
        return spacy.load("en_core_web_sm")
    except Exception as e:
        print(f"⚠️ Model load failed: {e}. Using Blank Fallback.")
        # Fallback → blank English model (no crash, basic tokenization)
        return spacy.blank("en")

# Initialize NLP
nlp = load_nlp()

def get_masked_text(text, label, style="Tags"):
    """Returns text masked in the chosen style."""
    if style == "Tags":
        return f"[{label}]"
    elif style == "Blackout":
        return "█" * len(text)  # Visual redaction
    elif style == "Asterisks":
        return "*" * len(text)  # Obfuscation
    elif style == "Hash (SHA-256)":
        # Secure anonymization for analytics
        return hashlib.sha256(text.encode()).hexdigest()[:10]
    return f"[{label}]"

def redact_text(text, selected_entities, masking_style="Tags"):
    doc = nlp(text)
    redacted_text = text
    detected_items = []

    # --- 1. Regex Patterns (Robust & Fast) ---
    patterns = {
        "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "PHONE": r'\b(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})\b',
        "IP_ADDRESS": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        "CREDIT_CARD": r'\b(?:\d[ -]*?){13,16}\b'
    }

    for label, pattern in patterns.items():
        if label in selected_entities:
            matches = re.finditer(pattern, redacted_text)
            for match in matches:
                original_chunk = match.group()
                # Apply selected masking style
                mask = get_masked_text(original_chunk, label, masking_style)
                redacted_text = redacted_text.replace(original_chunk, mask)
                detected_items.append((original_chunk, label))

    # --- 2. AI Detection (Contextual) ---
    # Re-process text to find context-based entities (Name, Org, Location)
    # Only runs if model loaded successfully (blank model won't find ents)
    if "ner" in nlp.pipe_names: 
        doc = nlp(redacted_text) 
        
        ai_replacements = []
        for ent in doc.ents:
            if ent.label_ in selected_entities:
                # Avoid re-masking already masked items
                if masking_style == "Tags" and ent.text.startswith("["): continue
                if masking_style == "Blackout" and "█" in ent.text: continue
                
                ai_replacements.append((ent.text, ent.label_))
                detected_items.append((ent.text, ent.label_))
        
        # Apply Replacements
        for item, label in ai_replacements:
            mask = get_masked_text(item, label, masking_style)
            redacted_text = redacted_text.replace(item, mask)
    
    return redacted_text, detected_items

def calculate_safety_score(original, redacted):
    if not original: return 100
    if original == redacted: return 0
    diff_ratio = 1 - (len(redacted) / len(original))
    return 98 if diff_ratio != 0 else 0
    
