from __future__ import annotations

"""Ollama (Mistral) powered NLU client + deep_translator for translation.

Uses local Ollama server for extraction/summarization tasks,
and deep_translator for language translation (free, no API key needed).
"""

import json
import re
from typing import Any

import requests
from deep_translator import GoogleTranslator

from app.config import settings

# ── Language code mapping for deep_translator ────────────────────
LANG_TO_TRANSLATE = {
    "Hindi": "hi",
    "Bhojpuri": "hi",      # Bhojpuri → Hindi (closest supported)
    "Maithili": "hi",      # Maithili → Hindi (closest supported)
    "Punjabi": "pa",
    "English": "en",
}


# ── Helpers ──────────────────────────────────────────────────────
def _extract_json_object(raw: str) -> dict[str, Any]:
    """Extract the first JSON object from potentially noisy LLM output."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return {}


def _sanitize_llm_text(text: str) -> str:
    """Strip common reasoning / markdown wrappers from LLM output."""
    cleaned = text.strip()
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"```.*?```", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"(?im)^(thinking|reasoning|analysis)\s*:\s*.*$", "", cleaned)
    return cleaned.strip()


def call_ollama(prompt: str, temperature: float = 0.2) -> str:
    """Send a prompt to Ollama (Mistral) and return the text response."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.ollama_api_key:
        headers["Authorization"] = f"Bearer {settings.ollama_api_key}"

    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    try:
        resp = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            headers=headers,
            json=payload,
            timeout=45,
        )
        resp.raise_for_status()
        data = resp.json()
        return _sanitize_llm_text(str(data.get("response", "")))
    except requests.RequestException as exc:
        print(f"⚠️ Ollama API error: {exc}")
        return ""


# ── Public functions ─────────────────────────────────────────────
def normalize_utterance_to_english(utterance: str) -> dict[str, Any]:
    """Extract structured data from a user's FD-related sentence."""
    prompt = (
        "You are an information extraction system.\n"
        "Extract details from this FD user sentence and return STRICT JSON only.\n"
        "Keys: language, amount_inr, tenor_months, reason, intent, confirmation\n"
        "Rules:\n"
        "- language: detected user language in English (Hindi/Bhojpuri/Punjabi/Bengali/English/Other)\n"
        "- amount_inr: numeric INR value if present else null\n"
        "- tenor_months: integer months if present else null\n"
        "- reason: short English phrase\n"
        "- intent: one of [provide_info, ask_question, confirm_yes, confirm_no, unclear]\n"
        "- confirmation: one of [yes, no, unknown]\n"
        f"User sentence: {utterance}"
    )
    raw = call_ollama(prompt=prompt, temperature=0.0)
    if not raw:
        return {}
    return _extract_json_object(raw)


def extract_name_from_sentence(utterance: str) -> str:
    """Extract a person's first name from a spoken sentence."""
    prompt = (
        "Extract only the person's first name from this sentence.\n"
        'Return STRICT JSON with key: name\n'
        'If no name is clear, return {"name":""}.\n'
        f"Sentence: {utterance}"
    )
    raw = call_ollama(prompt=prompt, temperature=0.0)
    if not raw:
        return ""
    data = _extract_json_object(raw)
    name = str(data.get("name", "")).strip()
    # Keep it short and natural for greeting.
    return name.split()[0] if name else ""


def summarize_reason_to_plain_english(reason_text: str) -> str:
    """Rewrite an FD reason in plain simple English, max 8 words."""
    prompt = (
        "Rewrite this FD reason in plain simple English, max 8 words.\n"
        "Do not copy raw sentence. Return only rewritten phrase.\n"
        "Do not include any thinking or explanation.\n"
        f"Reason: {reason_text}"
    )
    out = call_ollama(prompt=prompt, temperature=0.1)
    return out.strip()


def translate_to_preferred_language(text: str, preferred_language: str) -> str:
    """Translate text to the user's preferred language using Google Translate.

    Uses deep_translator (free, no API key) instead of LLM-based translation.
    Falls back to Ollama if deep_translator fails.
    """
    if preferred_language == "English":
        return text

    target_code = LANG_TO_TRANSLATE.get(preferred_language, "hi")

    try:
        translated = GoogleTranslator(source="en", target=target_code).translate(text)
        if translated:
            return translated
    except Exception as exc:
        print(f"⚠️ deep_translator failed: {exc}, falling back to Ollama")

    # Fallback: use Ollama for translation
    prompt = (
        "Translate this to user's preferred language with very simple tone.\n"
        "Keep FD terms easy and conversational.\n"
        "Return only final translated text. No thinking. No explanation.\n"
        f"Target language: {preferred_language}\n"
        f"Text: {text}"
    )
    return call_ollama(prompt=prompt, temperature=0.2)


def check_exit_intent(utterance: str) -> bool:
    """Check if the user wants to stop/exit or has more doubts."""
    prompt = (
        "Analyze the user's sentence to determine if they want to exit or have more questions.\n"
        "The system just asked them if they have any other questions or doubts.\n"
        "Return STRICT JSON with key: 'should_exit' (boolean)\n"
        "If the user says 'no', 'nothing', 'stop', 'exit', 'nope', or indicates they are done, set should_exit to true.\n"
        "If the user asks a question, mentions a topic, or says 'yes', 'tell me', set should_exit to false.\n"
        f"User sentence: {utterance}"
    )
    raw = call_ollama(prompt=prompt, temperature=0.1)
    if not raw:
        return True # Default to exit if LLM fails
    data = _extract_json_object(raw)
    return bool(data.get("should_exit", False))


def answer_fd_doubt_in_english(question: str) -> str:
    """Answer an open-ended FD question briefly in English."""
    prompt = (
        "You are a helpful, expert banking assistant in India specializing in Fixed Deposits (FD).\n"
        "Answer the user's FD related question accurately and very briefly in plain, simple English.\n"
        "Keep the answer to 2-3 short sentences maximum.\n"
        "Do not use markdown formatting. Return only the final text.\n"
        f"User Question: {question}"
    )
    return call_ollama(prompt=prompt, temperature=0.3)
