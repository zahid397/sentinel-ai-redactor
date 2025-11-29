import spacy
import re
import hashlib

# --- Safe Model Loading ---
def load_nlp():
    """
    Attempts to load the efficient English model.
    Falls back to a blank model to prevent App Crash in Cloud.
    """
    try:
        # ✅ FIX: Use 'sm' (Small) instead of 'trf' (Transformer)
        # 'trf' is too big for free cloud environments and causes crashes.
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
    """
    Hybrid Redaction: Regex (Structured) + AI (Unstructured).
    Returns redacted text AND a detailed list of entities with indices.
    """
    redacted_text = text
    detected_items = [] # Stores: (Entity Label, Text, Start, End)

    # --- 1. Regex Patterns (Robust & Fast) ---
    patterns = {
        "URL": r'(https?://\S+|www\.\S+)',
        "EMAIL_ADDRESS": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "PHONE_NUMBER": r'\+?\d[\d\s().-]{7,}\d',
        "IP_ADDRESS": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        "CREDIT_CARD": r'\b(?:\d[ -]*?){13,16}\b',
        "DATE_TIME": r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}:\d{2}' # Basic patterns
    }

    # Apply Regex First
    for label, pattern in patterns.items():
        if label in selected_entities:
            # Using finditer to handle multiple occurrences
            for match in re.finditer(pattern, redacted_text):
                original_chunk = match.group()
                
                # Double check to prevent overlapping masking issues
                if "[" in original_chunk and "]" in original_chunk:
                    continue

                detected_items.append({
                    "Entity": label,
                    "Text": original_chunk,
                    "Start": match.start(),
                    "End": match.end()
                })
                
                mask = get_masked_text(original_chunk, label, masking_style)
                # Replace only first occurrence to fit loop logic safely
                redacted_text = redacted_text.replace(original_chunk, mask, 1)

    # --- 2. AI Detection (Contextual) ---
    SPACY_MAPPING = {
        "PERSON": "PERSON", "GPE": "LOCATION", "LOC": "LOCATION",
        "ORG": "ORGANIZATION", "DATE": "DATE_TIME", "TIME": "DATE_TIME"
    }

    # Only run AI if model loaded correctly
    if "ner" in nlp.pipe_names:
        doc = nlp(redacted_text)
        ai_replacements = []
        for ent in doc.ents:
            hackathon_label = SPACY_MAPPING.get(ent.label_, ent.label_)
            if hackathon_label in selected_entities:
                if masking_style == "Tags" and ent.text.startswith("["): continue
                if masking_style == "Blackout" and "█" in ent.text: continue
                
                ai_replacements.append((ent.text, hackathon_label, ent.start_char, ent.end_char))
        
        for text_chunk, label, start, end in ai_replacements:
            mask = get_masked_text(text_chunk, label, masking_style)
            redacted_text = redacted_text.replace(text_chunk, mask, 1)
            
            detected_items.append({
                "Entity": label,
                "Text": text_chunk,
                "Start": start,
                "End": end
            })
    
    return redacted_text, detected_items

def calculate_similarity(text1, text2):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, text1, text2).ratio() * 100
    
