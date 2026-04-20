import base64
import os
import re
import tempfile
from typing import Optional, Dict, Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from gtts import gTTS
from langdetect import detect, LangDetectException

from app.advisor import SUPPORTED_LANGUAGES, generate_advice
from app.gemini_client import (
    extract_name_from_sentence,
    normalize_utterance_to_english,
    summarize_reason_to_plain_english,
    translate_to_preferred_language,
    check_exit_intent,
    answer_fd_doubt_in_english,
)

app = FastAPI(title="Voice FD Advisor UI")
templates = Jinja2Templates(directory="templates")

# Store in-memory sessions
# session_id -> { "state": ..., "username": ..., "lang": ..., ... }
sessions: Dict[str, Any] = {}

class ChatRequest(BaseModel):
    session_id: str
    message: str

LANG_TO_TTS = {
    "hindi": "hi",
    "bhojpuri": "hi",
    "maithili": "hi",
    "punjabi": "hi",
    "english": "en",
}

DETECT_CODE_TO_LANG = {
    "hi": "Hindi",
    "pa": "Punjabi",
    "en": "English",
    "bn": "Bhojpuri",
    "mr": "Hindi",
}

def detect_language_from_text(text: str) -> str:
    if not text or not text.strip():
        return "Hindi"
    try:
        detected_code = detect(text)
        return DETECT_CODE_TO_LANG.get(detected_code, "Hindi")
    except LangDetectException:
        return "Hindi"

def parse_amount(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = text.lower().replace(",", " ").strip()
    num_match = re.search(r"\d+(\.\d+)?", cleaned)
    if not num_match:
        return None
    base = float(num_match.group(0))
    if any(unit in cleaned for unit in ("lakh", "lac", "लाख")):
        return base * 100000
    if any(unit in cleaned for unit in ("crore", "करोड़", "crores")):
        return base * 10000000
    if any(unit in cleaned for unit in ("thousand", "hazar", "hazaar", "हजार")):
        return base * 1000
    return base

def parse_language_choice(text: str) -> str:
    t = text.strip().lower()
    if any(k in t for k in ("english", "inglish", "इंग्लिश", "अंग्रेजी", "एंग्लिश")):
        return "English"
    if any(k in t for k in ("bhojpuri", "भोजपुरी", "bhojpuriya")):
        return "Bhojpuri"
    if any(k in t for k in ("maithili", "मैथिली", "mithila")):
        return "Maithili"
    if any(k in t for k in ("punjabi", "पंजाबी", "panjabi")):
        return "Punjabi"
    return "Hindi"

def clean_name_from_sentence(name_sentence: str) -> str:
    text = (name_sentence or "").strip()
    if not text:
        return "Friend"
    text = re.sub(r"(?i)\b(my name is|name is|i am|i'm|mera naam|main|mai|mein|hu|hai|hoon)\b", " ", text)
    text = re.sub(r"[^\w\s\u0900-\u097F]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "Friend"
    tokens = text.split()
    return " ".join(tokens[:2]).title()

def localize_text(english_text: str, preferred_language: str) -> str:
    if preferred_language == "English":
        return english_text
    translated = translate_to_preferred_language(english_text, preferred_language=preferred_language)
    return translated or english_text

def get_audio_base64(text: str, lang: str = "hi") -> str:
    if not text.strip():
        return ""
    tld = "co.in" if lang in {"hi", "en"} else "com"
    tts = gTTS(text=text, lang=lang, tld=tld)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        temp_path = fp.name
    tts.save(temp_path)
    with open(temp_path, "rb") as f:
        audio_data = f.read()
    os.remove(temp_path)
    return base64.b64encode(audio_data).decode("utf-8")

@app.get("/", response_class=HTMLResponse)
async def get_ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    sess = sessions.get(req.session_id)
    if not sess:
        sess = {"state": "INIT"}
        sessions[req.session_id] = sess
        
    state = sess["state"]
    msg = req.message.strip()
    
    response_text = ""
    next_state = state
    tts_lang = "hi"
    
    # State Machine Implementation
    if state == "INIT":
        response_text = "Namaste! FD ke baare me samajhna hai ya invest bhi karna hai? Aapka naam bataiye."
        next_state = "ASK_LANGUAGE"

    elif state == "ASK_LANGUAGE":
        extracted_name = extract_name_from_sentence(msg)
        sess["username"] = clean_name_from_sentence(extracted_name or msg)
        auto_lang = detect_language_from_text(msg)
        sess["auto_lang"] = auto_lang
        response_text = f"Aap {auto_lang} bol rahe hain. Kya yeh theek hai? Ya doosri language boliye: Hindi, Bhojpuri, Maithili, Punjabi, English."
        next_state = "CONFIRM_LANGUAGE"

    elif state == "CONFIRM_LANGUAGE":
        lang_confirm_lower = msg.lower()
        if lang_confirm_lower in {"yes", "y", "haan", "ha", "h", "theek", "theek hai", "ok", "okay", ""}:
            lang = sess.get("auto_lang", "Hindi")
        else:
            lang = parse_language_choice(msg)
            
        lang_key = lang.strip().lower()
        if lang_key not in SUPPORTED_LANGUAGES:
            lang_key = "hindi"
            lang = "Hindi"
            
        sess["lang"] = lang
        sess["lang_key"] = lang_key
        tts_lang = LANG_TO_TTS.get(lang_key, "hi")
        
        greeting = localize_text(f"Nice to meet you {sess['username']}. I will continue in your selected language.", lang)
        reason_q = localize_text("What is the reason for this FD? Speak freely in your own words.", lang)
        response_text = f"{greeting} {reason_q}"
        next_state = "ASK_REASON"
        
    elif state == "ASK_REASON":
        lang = sess["lang"]
        tts_lang = LANG_TO_TTS.get(sess["lang_key"], "hi")
        
        reason_data = normalize_utterance_to_english(msg)
        extracted_reason = str(reason_data.get("reason") or "").strip()
        summary_reason = summarize_reason_to_plain_english(extracted_reason or msg)
        sess["reason"] = summary_reason or extracted_reason or msg
        
        response_text = localize_text(f"I understood you are saving for: {sess['reason']}. Now please tell FD duration in months.", lang)
        next_state = "ASK_TENOR"
        
    elif state == "ASK_TENOR":
        lang = sess["lang"]
        tts_lang = LANG_TO_TTS.get(sess["lang_key"], "hi")
        
        tenor_data = normalize_utterance_to_english(msg)
        tenor_value = tenor_data.get("tenor_months")
        if tenor_value is None:
            tenor_value = parse_amount(msg)
        sess["tenor"] = tenor_value
        
        if tenor_value:
            response_text = localize_text(f"I understood tenure is {int(float(tenor_value))} months. Now please tell investment amount.", lang)
        else:
            response_text = localize_text("I could not fully understand tenure. Please now tell investment amount.", lang)
        next_state = "ASK_AMOUNT"
        
    elif state == "ASK_AMOUNT":
        lang = sess["lang"]
        tts_lang = LANG_TO_TTS.get(sess["lang_key"], "hi")
        
        amount_data = normalize_utterance_to_english(msg)
        amount = amount_data.get("amount_inr")
        if amount is None:
            amount = parse_amount(msg)
            
        if amount is None:
            response_text = localize_text("Could not understand amount. Please tell amount, for example 10000.", lang)
        else:
            sess["amount"] = float(amount)
            # Generate Database / LLM Advice
            try:
                advice = generate_advice(
                    username=sess["username"],
                    user_reason=sess["reason"],
                    lang_input=sess["lang"],
                    investment_amount=float(amount),
                    preferred_tenor_months=int(sess["tenor"]) if sess.get("tenor") else None,
                )
                english_message = (
                    f"For your goal ({sess['reason']}), a suitable FD is {advice.bank_name}. "
                    f"Rate is {advice.rate}% per year for {advice.tenor_months} months. "
                    f"If you invest INR {float(amount):,.0f}, expected interest is INR {advice.estimated_interest:,.0f}, "
                    f"and maturity amount is around {advice.maturity_amount:,.0f}. "
                )
                adv_text = localize_text(english_message, lang)
                conf_text = localize_text("Do you want to hear FD booking steps? Say yes or no.", lang)
                response_text = f"{adv_text} {conf_text}"
                next_state = "ASK_STEPS"
            except Exception as e:
                response_text = localize_text(f"Sorry, I had an error analyzing offers: {str(e)}", lang)
                
    elif state == "ASK_STEPS":
        lang = sess["lang"]
        tts_lang = LANG_TO_TTS.get(sess["lang_key"], "hi")
        
        confirm_data = normalize_utterance_to_english(msg.lower())
        confirmation = str(confirm_data.get("confirmation") or "").lower()
        intent = str(confirm_data.get("intent") or "").lower()
        
        wants_steps = False
        if confirmation == "yes" or msg.lower() in {"yes", "y", "haan", "ha"}:
            wants_steps = True
        elif "booking" in msg.lower() or "process" in msg.lower() or "kaise" in msg.lower() or "bata" in msg.lower():
            wants_steps = True
        elif intent == "ask_question" and ("step" in msg.lower() or "booking" in msg.lower()):
            wants_steps = True
            
        if wants_steps:
            steps_english = (
                "Simple FD booking guidance: "
                "Step 1, choose bank app or branch. "
                "Step 2, select amount and tenor. "
                "Step 3, add nominee. "
                "Step 4, choose interest payout option. "
                "Step 5, verify details and confirm."
            )
            resp_part1 = localize_text(steps_english, lang)
        else:
            resp_part1 = localize_text("Okay, no problem.", lang)
            
        resp_part2 = localize_text("Kya aapko koi aur doubt hai ya aap kuch aur janna chahte hain?", lang)
        response_text = f"{resp_part1} {resp_part2}"
        next_state = "OPEN_DOUBTS"
        
    elif state == "OPEN_DOUBTS":
        lang = sess["lang"]
        tts_lang = LANG_TO_TTS.get(sess["lang_key"], "hi")
        
        should_exit = check_exit_intent(msg)
        if should_exit:
            response_text = localize_text("Theek hai, dhanyawad! Aap kabhi bhi aakar sawal pooch sakte hain. Alvida!", lang)
            next_state = "INIT"  # Reset loop
        else:
            ans_eng = answer_fd_doubt_in_english(msg)
            response_text = localize_text(ans_eng, lang)

    sess["state"] = next_state
    
    # Refresh tts_lang in case it got populated
    if "lang_key" in sess:
        tts_lang = LANG_TO_TTS.get(sess["lang_key"], "hi")
        
    try:
        audio_base64 = get_audio_base64(response_text, lang=tts_lang)
    except Exception as e:
        print(f"TTS Error: {e}")
        audio_base64 = ""
        
    return {
        "text": response_text,
        "audio_base64": audio_base64,
        "next_state": next_state
    }

if __name__ == "__main__":
    import uvicorn
    # Make sure to run from within the same directory as templates/
    uvicorn.run("ui:app", host="0.0.0.0", port=8000, reload=True)
