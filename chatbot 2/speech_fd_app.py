import os
import re
import tempfile
from typing import Optional

import speech_recognition as sr
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


LANG_TO_TTS = {
    "hindi": "hi",
    "bhojpuri": "hi",
    "maithili": "hi",
    "punjabi": "hi",
    "english": "en",
}

LANG_TO_STT = {
    "hindi": "hi-IN",
    "bhojpuri": "hi-IN",
    "maithili": "hi-IN",
    "punjabi": "pa-IN",
    "english": "en-IN",
}

# langdetect code → our language key mapping
DETECT_CODE_TO_LANG = {
    "hi": "Hindi",
    "pa": "Punjabi",
    "en": "English",
    "bn": "Bhojpuri",   # Bengali detection sometimes fires for Bhojpuri
    "mr": "Hindi",      # Marathi fallback → Hindi
}


def speak_text(text: str, lang: str = "hi", slow: bool = False) -> None:
    if not text.strip():
        return
    tld = "co.in" if lang in {"hi", "en"} else "com"
    tts = gTTS(text=text, lang=lang, slow=slow, tld=tld)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        temp_path = fp.name
    tts.save(temp_path)
    os.system(f"afplay '{temp_path}'")
    os.remove(temp_path)


def listen_once(stt_lang: str = "hi-IN", timeout: int = 8) -> str:
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.9
    with sr.Microphone() as source:
        print("🎙️ Boliye... (listening)")
        recognizer.adjust_for_ambient_noise(source, duration=1.2)
        audio = recognizer.listen(source, timeout=timeout)
    return recognizer.recognize_google(audio, language=stt_lang)


def listen_any_language(timeout: int = 8) -> str:
    language_guesses = ["hi-IN", "en-IN", "bn-IN", "pa-IN", "mr-IN"]
    last_error = None
    for stt_lang in language_guesses:
        try:
            text = listen_once(stt_lang=stt_lang, timeout=timeout)
            if text:
                return text
        except Exception as exc:  # pragma: no cover - runtime speech failures
            last_error = exc
    if last_error:
        raise last_error
    return ""


def ask_by_voice(question: str, tts_lang: str, retries: int = 2, retry_text: str = "Voice was unclear, please repeat.") -> str:
    speak_text(question, lang=tts_lang)
    print(question)
    for _ in range(retries + 1):
        try:
            heard = listen_any_language()
            print(f"📝 Aapne bola: {heard}")
            return heard
        except Exception:
            print(retry_text)
            speak_text(retry_text, lang=tts_lang)
    return ""


def detect_language_from_text(text: str) -> str:
    """Auto-detect user's language from spoken text using langdetect.

    Returns a language name like 'Hindi', 'English', 'Punjabi'.
    Falls back to 'Hindi' if detection fails.
    """
    if not text or not text.strip():
        return "Hindi"
    try:
        detected_code = detect(text)
        lang = DETECT_CODE_TO_LANG.get(detected_code, "Hindi")
        print(f"🔍 Language auto-detected: {detected_code} → {lang}")
        return lang
    except LangDetectException:
        print("🔍 Language detection failed, defaulting to Hindi")
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
    if any(k in t for k in ("hindi", "हिंदी", "हिन्दी")):
        return "Hindi"
    return "Hindi"


def clean_name_from_sentence(name_sentence: str) -> str:
    text = (name_sentence or "").strip()
    if not text:
        return "Friend"

    # Remove common intro phrases from Hindi/English speech.
    text = re.sub(
        r"(?i)\b(my name is|name is|i am|i'm|mera naam|main|mai|mein|hu|hai|hoon)\b",
        " ",
        text,
    )
    text = re.sub(r"[^\w\s\u0900-\u097F]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "Friend"

    # Keep max first 2 tokens so greeting sounds natural.
    tokens = text.split()
    candidate = " ".join(tokens[:2])
    return candidate.title()


def localize_text(english_text: str, preferred_language: str) -> str:
    if preferred_language == "English":
        return english_text
    translated = translate_to_preferred_language(english_text, preferred_language=preferred_language)
    return translated or english_text


def run() -> None:
    print("Namaste! FD ke baare me samajhna hai ya invest bhi karna hai? 😊")
    speak_text("Namaste! FD ke baare me samajhna hai ya invest bhi karna hai?", lang="hi")

    # ── Step 1: Get user's name ──────────────────────────────────
    username_raw = ask_by_voice(
        "Aapka naam bataiye.",
        tts_lang="hi",
    ) or "Guest"
    extracted_name = extract_name_from_sentence(username_raw)
    username = clean_name_from_sentence(extracted_name or username_raw)

    # ── Step 2: Auto-detect language from speech ─────────────────
    auto_lang = detect_language_from_text(username_raw)
    print(f"🌐 Auto-detected language: {auto_lang}")

    # Confirm or let user override
    confirm_msg = f"Aap {auto_lang} bol rahe hain. Kya yeh theek hai? Ya doosri language boliye: Hindi, Bhojpuri, Maithili, Punjabi, English."
    lang_confirm = ask_by_voice(confirm_msg, tts_lang="hi") or ""
    lang_confirm_lower = lang_confirm.strip().lower()

    # If user says yes/haan, keep auto-detected. Otherwise parse their choice.
    if lang_confirm_lower in {"yes", "y", "haan", "ha", "h", "theek", "theek hai", "ok", "okay", ""}:
        lang = auto_lang
    else:
        lang = parse_language_choice(lang_confirm)

    lang_key = lang.strip().lower()
    if lang_key not in SUPPORTED_LANGUAGES:
        print("Language not matched, Hindi use kar rahe hain.")
        lang_key = "hindi"
        lang = "Hindi"

    tts_lang = LANG_TO_TTS.get(lang_key, "hi")
    print(f"✅ Selected language: {lang}")

    personalized_greet = localize_text(
        f"Nice to meet you {username}. I will continue in your selected language.",
        lang,
    )
    print(personalized_greet)
    speak_text(personalized_greet, lang=tts_lang)

    # ── Step 3: Get FD reason ────────────────────────────────────
    retry_text = localize_text("Voice was unclear, please repeat.", lang)
    reason_spoken = ask_by_voice(
        localize_text("What is the reason for this FD? Speak freely in your own words.", lang),
        tts_lang=tts_lang,
        retry_text=retry_text,
    ) or "future planning"
    reason_data = normalize_utterance_to_english(reason_spoken)
    extracted_reason = str(reason_data.get("reason") or "").strip()
    summary_reason = summarize_reason_to_plain_english(extracted_reason or reason_spoken)
    reason = summary_reason or extracted_reason or reason_spoken
    reason_ack = localize_text(
        f"I understood you are saving for: {reason}. Now please tell FD duration in months.",
        lang,
    )
    print(reason_ack)
    speak_text(reason_ack, lang=tts_lang)

    # ── Step 4: Get tenor ────────────────────────────────────────
    tenor_text = ask_by_voice(
        localize_text("How many months do you want for FD? Say a number, like 12.", lang),
        tts_lang=tts_lang,
        retry_text=retry_text,
    )
    tenor_data = normalize_utterance_to_english(tenor_text)
    tenor_value = tenor_data.get("tenor_months")
    if tenor_value is None:
        tenor_value = parse_amount(tenor_text)
    if tenor_value:
        tenor_ack = localize_text(
            f"I understood tenure is {int(float(tenor_value))} months. Now please tell investment amount.",
            lang,
        )
    else:
        tenor_ack = localize_text(
            "I could not fully understand tenure. Please now tell investment amount.",
            lang,
        )
    print(tenor_ack)
    speak_text(tenor_ack, lang=tts_lang)

    # ── Step 5: Get amount ───────────────────────────────────────
    amount_text = ask_by_voice(
        localize_text("How much money do you want to invest? Say amount like 2 lakh.", lang),
        tts_lang=tts_lang,
        retry_text=retry_text,
    )
    amount_data = normalize_utterance_to_english(amount_text)
    amount = amount_data.get("amount_inr")
    if amount is None:
        amount = parse_amount(amount_text)
    if amount is None:
        typed_amount = input(localize_text("Could not understand amount. Please type it, for example 10000.", lang) + " ").strip()
        amount = float(typed_amount)
        amount_ack = localize_text(
            f"Got it. Amount noted as INR {int(amount)}. Now I will prepare your FD guidance.",
            lang,
        )
        print(amount_ack)
        speak_text(amount_ack, lang=tts_lang)
    else:
        confirm_text = localize_text(f"You said amount INR {int(amount)}, correct?", lang)
        print(confirm_text)
        speak_text(confirm_text, lang=tts_lang)
        next_text = localize_text("Great, now I will prepare your FD guidance.", lang)
        print(next_text)
        speak_text(next_text, lang=tts_lang)

    # ── Step 6: Generate advice ──────────────────────────────────
    advice = generate_advice(
        username=username,
        user_reason=reason,
        lang_input=lang,
        investment_amount=float(amount),
        preferred_tenor_months=int(tenor_value) if tenor_value else None,
    )

    english_message = (
        f"For your goal ({reason}), a suitable FD is {advice.bank_name}. "
        f"Rate is {advice.rate}% per year for {advice.tenor_months} months. "
        f"If you invest INR {float(amount):,.0f}, expected interest is INR {advice.estimated_interest:,.0f}, "
        f"and maturity amount is around INR {advice.maturity_amount:,.0f}. "
        "I guide you with steps, but booking is done by you."
    )
    if lang == "English":
        message = english_message
    else:
        translated = translate_to_preferred_language(english_message, preferred_language=lang)
        message = translated or english_message
    print("\n--- FD Advice ---")
    print(message)
    speak_text(message, lang=tts_lang)

    # ── Step 7: Booking steps ────────────────────────────────────
    confirm = ask_by_voice(
        localize_text("Do you want to hear FD booking steps? Say yes or no.", lang),
        tts_lang=tts_lang,
        retry_text=retry_text,
    ).strip().lower()
    confirm_data = normalize_utterance_to_english(confirm)
    confirmation = str(confirm_data.get("confirmation") or "").lower()
    intent = str(confirm_data.get("intent") or "").lower()
    
    wants_steps = False
    if confirmation == "yes" or confirm in {"yes", "y", "haan", "ha"}:
        wants_steps = True
    elif "booking" in confirm or "process" in confirm or "kaise" in confirm or "bata" in confirm:
        wants_steps = True
    elif intent == "ask_question" and ("step" in confirm or "booking" in confirm):
        wants_steps = True

    if wants_steps:
        steps_english = (
            "Simple FD booking guidance: "
            "Step 1, choose bank app or branch. "
            "Step 2, select amount and tenor. "
            "Step 3, add nominee. "
            "Step 4, choose interest payout option. "
            "Step 5, verify details and confirm. "
            "I only guide you, you book the FD yourself. Final decision is yours."
        )
        steps_text = steps_english if lang == "English" else translate_to_preferred_language(steps_english, lang)
        print(steps_text)
        speak_text(steps_text, lang=tts_lang)
    else:
        okay_text = localize_text("Okay, no problem.", lang)
        print(okay_text)
        speak_text(okay_text, lang=tts_lang)

    # ── Step 8: Open-ended doubts loop ───────────────────────────
    while True:
        more_prompt = localize_text("Kya aapko koi aur doubt hai ya aap kuch aur janna chahte hain?", lang)
        user_doubt = ask_by_voice(more_prompt, tts_lang=tts_lang, retry_text=retry_text)

        if not user_doubt.strip():
            continue

        should_exit = check_exit_intent(user_doubt)
        if should_exit:
            closing = localize_text("Theek hai, dhanyawad! Aap kabhi bhi aakar sawal pooch sakte hain. Alvida!", lang)
            print(closing)
            speak_text(closing, lang=tts_lang)
            break

        # Treat as question
        ans_eng = answer_fd_doubt_in_english(user_doubt)
        ans_loc = localize_text(ans_eng, lang)
        print(ans_loc)
        speak_text(ans_loc, lang=tts_lang)

if __name__ == "__main__":
    run()
