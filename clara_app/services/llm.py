import google.generativeai as genai
import json
import re
from typing import Dict, Any, Optional

from clara_app.constants import API_KEY, SYSTEM_INSTRUCTIONS, SUMMARY_SYSTEM_INSTRUCTIONS, CLASSIFIER_SYSTEM_INSTRUCTIONS

# Initialize immediately if key is present
if API_KEY:
    genai.configure(api_key=API_KEY)

# Safety Settings
SAFETY_SETTINGS = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_ONLY_HIGH",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
]

_model = None
_summary_model = None
_classifier_model = None
_meta_model = None

def get_model():
    global _model
    if _model is None:
        _model = genai.GenerativeModel(
            model_name="gemini-2.5-pro",
            system_instruction=SYSTEM_INSTRUCTIONS,
            safety_settings=SAFETY_SETTINGS
        )
    return _model

def get_summary_model():
    global _summary_model
    if _summary_model is None:
        _summary_model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            system_instruction=SUMMARY_SYSTEM_INSTRUCTIONS,
            safety_settings=SAFETY_SETTINGS
        )
    return _summary_model

def get_classifier_model():
    global _classifier_model
    if _classifier_model is None:
        _classifier_model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=CLASSIFIER_SYSTEM_INSTRUCTIONS,
            safety_settings=SAFETY_SETTINGS
        )
    return _classifier_model

def get_meta_model():
    global _meta_model
    if _meta_model is None:
        _meta_model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            safety_settings=SAFETY_SETTINGS
        )
    return _meta_model

def classify_topic(user_text: str) -> str:
    """
    Anonymous topic classifier for analytics.
    Uses a dedicated Gemini model with a strict instruction and temperature=0.
    Returns one of: Career, Productivity, Relationships, Health, Anxiety, Philosophy, Learning, Other.
    """
    allowed = {
        "career",
        "productivity",
        "relationships",
        "health",
        "anxiety",
        "philosophy",
        "learning",
        "other",
    }
    if not isinstance(user_text, str) or not user_text.strip():
        return "Other"
    try:
        model = get_classifier_model()
        resp = model.generate_content(
            user_text,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                max_output_tokens=8,
            ),
        )
        label = (resp.text or "").strip().strip("'\"")
        label_lower = label.lower()
        if label_lower in allowed:
            # Return with canonical capitalisation
            return label_lower.capitalize()
    except Exception:
        pass
    return "Other"

def extract_emotional_metadata(text: str) -> Dict[str, Any]:
    """
    Analyzes the text to extract emotional tone and weight.
    Returns:
        {
            "tone": str,    # e.g., "Anxious", "Joyful", "Neutral"
            "weight": int   # 1-10
        }
    """
    if not text or not text.strip():
        return {"tone": "Neutral", "weight": 1}

    try:
        model = get_meta_model()
        
        prompt = f"""
        Analyze the following text for its emotional tone and emotional weight (intensity).
        
        Text: "{text}"
        
        Return ONLY a JSON object with this format. Do not use markdown code blocks.
        {{
            "tone": "OneWordAdjective",
            "weight": IntegerBetween1And10
        }}
        """
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json"
            )
        )
        
        result_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(result_text)
        
        return {
            "tone": data.get("tone", "Neutral"),
            "weight": int(data.get("weight", 1))
        }
        
    except Exception as e:
        print(f"Emotion extraction error: {e}")
        return {"tone": "Neutral", "weight": 1}

