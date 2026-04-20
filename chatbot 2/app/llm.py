from app.gemini_client import call_ollama


def rewrite_in_dialect(prompt: str, fallback_text: str) -> str:
    """Rewrite FD advice in a regional dialect using Ollama (Mistral).

    Falls back to fallback_text if Ollama is unavailable.
    """
    result = call_ollama(prompt=prompt, temperature=0.7)
    return result if result else fallback_text
