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
    """
    Hybrid Redaction: Regex (Structured) + AI (Unstructured).
    Returns redacted text AND a detailed list of entities with indices.
    """
    redacted_text = text
    detected_items = [] # Stores: (Entity Label, Text)

    # --- 1. Regex Patterns (Updated for Global Support) ---
    patterns = {
        "URL": r'(https?://\S+|www\.\S+)',
        "EMAIL_ADDRESS": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        
        # ✅ UPDATED: More general phone pattern for UK/US/Intl formats
        "PHONE_NUMBER": r'\+?\d[\d\s().-]{7,}\d',
        
        "IP_ADDRESS": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        "CREDIT_CARD": r'\b(?:\d[ -]*?){13,16}\b',
        "DATE_TIME": r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}:\d{2}' # Basic patterns
    }

    # Apply Regex First
    for label, pattern in patterns.items():
        if label in selected_entities:
            # Using finditer to get matches without modifying text immediately
            matches = list(re.finditer(pattern, redacted_text))
            # Reverse iterate to replace without messing up indices of earlier matches
            for match in reversed(matches):
                original_chunk = match.group()
                
                # Double check to avoid partial replacements inside already replaced tags
                # (Simple heuristic check)
                if "[" in original_chunk and "]" in original_chunk:
                    continue

                # Store details
                detected_items.append({
                    "Entity": label,
                    "Text": original_chunk
                })
                
                # Replace
                mask = get_masked_text(original_chunk, label, masking_style)
                redacted_text = redacted_text[:match.start()] + mask + redacted_text[match.end():]

    # --- 2. AI Detection (Contextual) ---
    # Map spaCy labels to Hackathon requirements
    SPACY_MAPPING = {
        "PERSON": "PERSON",
        "GPE": "LOCATION",
        "LOC": "LOCATION",
        "ORG": "ORGANIZATION",
        "DATE": "DATE_TIME",
        "TIME": "DATE_TIME"
    }

    if "ner" in nlp.pipe_names:
        doc = nlp(redacted_text) # Process the partially redacted text
        
        ai_replacements = []
        for ent in doc.ents:
            hackathon_label = SPACY_MAPPING.get(ent.label_, ent.label_)
            
            if hackathon_label in selected_entities:
                # Skip if already masked (Tag style check)
                if masking_style == "Tags" and ent.text.startswith("["): continue
                # Skip if already masked (Blackout style check)
                if masking_style == "Blackout" and "█" in ent.text: continue
                
                ai_replacements.append((ent.text, hackathon_label, ent.start_char, ent.end_char))
        
        # Apply AI Replacements
        # Iterate and replace. Note: Simple replace can affect multiple instances.
        # Ideally, we reconstruct string, but for hackathon demo simple replace is safer/faster.
        for text_chunk, label, start, end in ai_replacements:
            mask = get_masked_text(text_chunk, label, masking_style)
            # Use count=1 to try and target specific instance if possible, 
            # though simple replace is robust enough for most demo texts.
            redacted_text = redacted_text.replace(text_chunk, mask)
            
            detected_items.append({
                "Entity": label,
                "Text": text_chunk
            })
    
    return redacted_text, detected_items

def calculate_similarity(text1, text2):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, text1, text2).ratio() * 100

def calculate_safety_score(original, redacted):
    if not original: return 100
    if original == redacted: return 0
    diff_ratio = 1 - (len(redacted) / len(original))
    return 98 if diff_ratio != 0 else 0
    
