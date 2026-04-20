from __future__ import annotations

from dataclasses import dataclass

from app.db import fetch_best_offer, fetch_jargon_map, save_user_advice
from app.llm import rewrite_in_dialect


SUPPORTED_LANGUAGES = {
    "hindi": "Hindi",
    "bhojpuri": "Bhojpuri",
    "maithili": "Maithili",
    "punjabi": "Punjabi",
    "english": "English",
}


@dataclass
class AdviceResult:
    bank_name: str
    tenor_months: int
    rate: float
    estimated_interest: float
    maturity_amount: float
    explanation: str


def estimate_simple_interest(principal: float, annual_rate: float, tenor_months: int) -> tuple[float, float]:
    years = tenor_months / 12
    interest = principal * (annual_rate / 100) * years
    maturity = principal + interest
    return round(interest, 2), round(maturity, 2)


def generate_advice(
    username: str,
    user_reason: str,
    lang_input: str,
    investment_amount: float,
    preferred_tenor_months: int | None = None,
) -> AdviceResult:
    language = SUPPORTED_LANGUAGES.get(lang_input.strip().lower(), "Hindi")
    reason = (user_reason or "general savings").strip()
    offer = fetch_best_offer(preferred_tenor_months)
    if not offer:
        raise ValueError("No bank offer found.")

    interest, maturity = estimate_simple_interest(
        principal=investment_amount,
        annual_rate=float(offer["rate"]),
        tenor_months=int(offer["tenor_months"]),
    )

    jargon = fetch_jargon_map(language)
    if language == "English":
        fallback_text = (
            f"{offer['bank_name']} looks suitable for your goal. "
            f"Rate is {offer['rate']}% for {offer['tenor_months']} months. "
            f"On INR {investment_amount:.2f}, expected interest is INR {interest:.2f} "
            f"and maturity is around INR {maturity:.2f}."
        )
    else:
        fallback_text = (
            f"{offer['bank_name']} aapke goal ke liye theek option lagta hai. "
            f"Rate {offer['rate']}% hai aur tenor {offer['tenor_months']} mahine ka hai. "
            f"Agar aap {investment_amount:.2f} lagate hain to lagbhag {interest:.2f} interest milega, "
            f"aur maturity par total {maturity:.2f} ke aas-paas milega."
        )

    prompt = (
        f"Explain FD advice in {language} for rural user.\n"
        f"Bank: {offer['bank_name']}, Rate: {offer['rate']}%, Tenor: {offer['tenor_months']} months, "
        f"Amount: {investment_amount}, Interest: {interest}, Maturity: {maturity}.\n"
        f"User reason: {reason}\n"
        f"Use local, simple style. Include these meanings if possible: {jargon}."
    )
    explanation = rewrite_in_dialect(prompt=prompt, fallback_text=fallback_text)

    save_user_advice(
        username=username,
        language=language,
        user_reason=reason,
        invested_amount=investment_amount,
        suggested_bank=offer["bank_name"],
        suggested_rate=float(offer["rate"]),
    )

    return AdviceResult(
        bank_name=offer["bank_name"],
        tenor_months=int(offer["tenor_months"]),
        rate=float(offer["rate"]),
        estimated_interest=interest,
        maturity_amount=maturity,
        explanation=explanation,
    )
