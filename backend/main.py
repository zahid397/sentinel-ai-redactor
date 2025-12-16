from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re
import spacy
from datetime import datetime
import os

# --- 1. SETUP & MODEL LOADING ---
app = FastAPI(title="Sentinel AI Enterprise API", version="3.0-Stable")

# Auto-download model for Azure/Cloud (Startup Script)
try:
    nlp = spacy.load("en_core_web_sm")
    print("✅ NLP Model Loaded: en_core_web_sm")
except OSError:
    print("⚠️ Model not found. Downloading...")
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# --- 2. DATA MODELS ---
class RedactionRequest(BaseModel):
    text: str
    entities: list = ["PERSON", "ORG", "GPE", "EMAIL", "PHONE"] 
    style: str = "Tags" 

class RedactionResponse(BaseModel):
    original_text: str
    redacted_text: str
    detections: list
    stats: dict
    processing_time: float

# --- 3. CORE LOGIC (REFINED) ---
def detect_and_redact(text, target_entities, style):
    start_time = datetime.now()
    doc = nlp(text) 
    
    found_items = []
    
    # 🔧 FIX 1: LABEL NORMALIZATION MAP
    # Internal SpaCy Label -> Enterprise Friendly Label
    spacy_map = {
        "GPE": "LOCATION",
        "ORG": "ORGANIZATION",
        "PERSON": "PERSON",
        "DATE": "DATE_TIME",
        "FAC": "FACILITY"
    }

    # A. NLP DETECTION (Smart Context)
    for ent in doc.ents:
        # Check against target_entities (using original SpaCy label for filtering)
        if ent.label_ in target_entities:
            # Save using the friendly enterprise label
            friendly_label = spacy_map.get(ent.label_, ent.label_)
            
            found_items.append({
                "value": ent.text,
                "type": friendly_label, 
                "source": "spaCy (NLP)",
                "confidence": 0.85  # 🔧 FIX 3: Realistic Confidence
            })

    # B. REGEX DETECTION (Pattern Precision)
    regex_patterns = {
        "EMAIL": r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
        "PHONE": r"\b(?:\+8801|01)[3-9]\d{8}\b",
        "IP": r"\b\d{1,3}(?:\.\d{1,3}){3}\b",
        "URL": r"https?://\S+|www\.\S+"
    }

    for label, pattern in regex_patterns.items():
        if label in target_entities:
            for m in re.finditer(pattern, text):
                # Avoid duplicates if NLP already caught it
                if not any(d['value'] == m.group() for d in found_items):
                    found_items.append({
                        "value": m.group(),
                        "type": label,
                        "source": "Regex Pattern",
                        "confidence": 0.99 # Regex is exact, so high confidence is honest
                    })

    # C. REDACTION
    redacted_text = text
    # Sort by length (descending) to prevent partial replacement errors
    found_items.sort(key=lambda x: len(x['value']), reverse=True)

    for item in found_items:
        replacement = f"[{item['type']}]" if style == "Tags" else "██████"
        redacted_text = redacted_text.replace(item['value'], replacement)

    # 🔧 FIX 2: SMARTER WEIGHTED RISK SCORE
    risk_score = 0
    high_risk_types = ["PERSON", "EMAIL", "PHONE", "CREDIT_CARD"]
    
    for item in found_items:
        if item['type'] in high_risk_types:
            risk_score += 20  # Sensitive data = High penalty
        else:
            risk_score += 10  # Metadata/Location = Lower penalty
            
    # Cap at 100
    final_risk_score = min(risk_score, 100)

    # Processing Stats
    processing_time = (datetime.now() - start_time).total_seconds()
    
    return {
        "original_text": text,
        "redacted_text": redacted_text,
        "detections": found_items,
        "stats": {
            "total_detected": len(found_items),
            "risk_score": final_risk_score
        },
        "processing_time": processing_time
    }

# --- 4. API ENDPOINT ---
@app.post("/api/v1/analyze", response_model=RedactionResponse)
def analyze_text(req: RedactionRequest):
    return detect_and_redact(req.text, req.entities, req.style)
    
