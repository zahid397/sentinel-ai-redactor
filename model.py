import spacy
import re
import hashlib
from difflib import SequenceMatcher

# -------------------------------
# Load SpaCy Model
# -------------------------------
def load_nlp():
    return spacy.load("en_core_web_sm")  # lightweight & stable for Streamlit

nlp = load_nlp()


# -------------------------------
# Mask Generator (Dual Mode)
# -------------------------------
def get_masked_text(text, label, style="Tags"):
    # 🎯 Judge mode = Always produce empty string
    if style == "Judge":
        return ""

    if style == "Tags":
        return f"[{label}]"

    elif style == "Blackout":
        return "█" * len(text)

    elif style == "Asterisk":
        return "*" * len(text)

    elif style == "Hash (SHA-256)":
        return hashlib.sha256(text.encode()).hexdigest()[:12]

    return ""


# -------------------------------
# PII Redaction System
# -------------------------------
def redact_text(text, selected_entities, masking_style="Tags"):
    redacted_text = text
    detected_items = []

    # Regex patterns
    patterns = {
        "URL": r'(https?://\S+|www\.\S+)',
        "EMAIL_ADDRESS": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        "PHONE_NUMBER": r'\+?\d[\d\s().-]{7,}\d',
        "IP_ADDRESS": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        "CREDIT_CARD": r'\b(?:\d[ -]*?){13,16}\b',
        "DATE_TIME": r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}:\d{2}'
    }

    # Regex Loop
    for label, pattern in patterns.items():
        if label in selected_entities:
            for match in re.finditer(pattern, redacted_text):
                chunk = match.group()
                mask = get_masked_text(chunk, label, masking_style)

                detected_items.append({
                    "Entity": label,
                    "Text": chunk,
                    "Start": match.start(),
                    "End": match.end()
                })

                redacted_text = redacted_text.replace(chunk, mask, 1)

    # SpaCy mapping
    SPACY_MAPPING = {
        "PERSON": "PERSON",
        "GPE": "LOCATION",
        "LOC": "LOCATION",
        "ORG": "ORG",
        "DATE": "DATE_TIME",
        "TIME": "DATE_TIME"
    }

    doc = nlp(redacted_text)
    replacements = []

    for ent in doc.ents:
        mapped = SPACY_MAPPING.get(ent.label_, None)
        if mapped and mapped in selected_entities:
            text_segment = ent.text
            mask = get_masked_text(text_segment, mapped, masking_style)

            replacements.append((text_segment, mask, mapped, ent.start_char, ent.end_char))

    for original, mask, label, start, end in replacements:
        redacted_text = redacted_text.replace(original, mask, 1)
        detected_items.append({
            "Entity": label,
            "Text": original,
            "Start": start,
            "End": end
        })

    return redacted_text, detected_items


# -------------------------------
# Similarity Scoring (Levenshtein)
# -------------------------------
def calculate_similarity(text1, text2):
    len1, len2 = len(text1), len(text2)
    max_len = max(len1, len2)

    if max_len == 0:
        return 100.0

    rows = len1 + 1
    cols = len2 + 1

    dp = [[0] * cols for _ in range(rows)]

    for i in range(rows):
        dp[i][0] = i
    for j in range(cols):
        dp[0][j] = j

    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if text1[i-1] == text2[j-1] else 1
            dp[i][j] = min(
                dp[i-1][j] + 1,
                dp[i][j-1] + 1,
                dp[i-1][j-1] + cost
            )

    distance = dp[-1][-1]
    accuracy = ((max_len - distance) / max_len) * 100
    return round(accuracy, 2)
