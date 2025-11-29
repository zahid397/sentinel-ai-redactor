import spacy
import re
import hashlib

# -------------------------------
# Safe SpaCy Load
# -------------------------------
def load_nlp():
    try:
        return spacy.load("en_core_web_sm")
    except:
        return spacy.blank("en")

nlp = load_nlp()


# -------------------------------
# Mask Generator
# -------------------------------
def get_masked_text(text, label, style="Tags"):
    if style == "Tags":
        return f"[{label}]"
    elif style == "Blackout":
        return "█" * len(text)
    elif style == "Asterisks":
        return "*" * len(text)
    elif style == "Hash (SHA-256)":
        return hashlib.sha256(text.encode()).hexdigest()[:10]
    return f"[{label}]"


# -------------------------------
# PII Redaction
# -------------------------------
def redact_text(text, selected_entities, masking_style="Tags"):
    redacted_text = text
    detected_items = []

    # Regex entities
    patterns = {
        "URL": r'(https?://\S+|www\.\S+)',
        "EMAIL_ADDRESS": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        "PHONE_NUMBER": r'\+?\d[\d\s().-]{7,}\d',
        "IP_ADDRESS": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        "CREDIT_CARD": r'\b(?:\d[ -]*?){13,16}\b',
        "DATE_TIME": r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}:\d{2}'
    }

    for label, pattern in patterns.items():
        if label in selected_entities:
            for match in re.finditer(pattern, redacted_text):
                chunk = match.group()
                mask = get_masked_text(chunk, label, masking_style)

                detected_items.append({"Entity": label, "Text": chunk})
                redacted_text = redacted_text.replace(chunk, mask, 1)

    # AI detection
    SPACY_MAPPING = {
        "PERSON": "PERSON",
        "GPE": "LOCATION",
        "LOC": "LOCATION",
        "ORG": "ORGANIZATION",
        "DATE": "DATE_TIME",
        "TIME": "DATE_TIME"
    }

    doc = nlp(redacted_text)

    for ent in doc.ents:
        mapped = SPACY_MAPPING.get(ent.label_, ent.label_)
        if mapped in selected_entities:
            mask = get_masked_text(ent.text, mapped, masking_style)
            detected_items.append({"Entity": mapped, "Text": ent.text})
            redacted_text = redacted_text.replace(ent.text, mask, 1)

    return redacted_text, detected_items


# -------------------------------
# Similarity
# -------------------------------
from difflib import SequenceMatcher

def calculate_similarity(a, b):
    return round(SequenceMatcher(None, a, b).ratio() * 100, 2)
