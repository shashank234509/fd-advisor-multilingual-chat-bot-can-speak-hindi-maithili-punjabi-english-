from app.advisor import generate_advice


def ask_float(prompt: str) -> float:
    while True:
        raw = input(prompt).strip()
        try:
            value = float(raw)
            if value <= 0:
                raise ValueError
            return value
        except ValueError:
            print("Please valid amount daliye, jaise 10000")


def ask_yes_no(prompt: str) -> bool:
    raw = input(prompt).strip().lower()
    return raw in {"yes", "y", "haan", "ha", "h"}


def run() -> None:
    print("\n=== Vernacular FD Advisor (Terminal Edition) ===")
    print("Namaste! FD option ko simple bhasha me samjhayenge.\n")

    username = input("Aapka naam: ").strip() or "Guest"
    lang = input("Language choose kariye (Hindi/Bhojpuri/Maithili/Punjabi): ").strip() or "Hindi"
    reason = input("Paisa kis kaam ke liye rakhna hai? (free text): ").strip() or "future planning"
    amount = ask_float("Kitna paisa FD me lagana chahte hain? ")
    tenor_raw = input("Kitne mahine ke liye FD chahiye? (optional, enter dabao skip): ").strip()
    tenor = int(tenor_raw) if tenor_raw.isdigit() else None

    result = generate_advice(
        username=username,
        user_reason=reason,
        lang_input=lang,
        investment_amount=amount,
        preferred_tenor_months=tenor,
    )

    print("\n--- Decision Card ---")
    print(f"Bank: {result.bank_name}")
    print(f"Rate: {result.rate}% p.a.")
    print(f"Tenor: {result.tenor_months} months")
    print(f"Estimated Interest: INR {result.estimated_interest}")
    print(f"Maturity Amount: INR {result.maturity_amount}\n")
    print(result.explanation)

    confirm = ask_yes_no("\nKya is FD suggestion ko book mark/save karna hai? (yes/no): ")
    if confirm:
        print("FD suggestion successfully saved in history. Final decision aapka hai.")
    else:
        print("Theek hai. Jab chahein dubara check kar sakte hain.")


if __name__ == "__main__":
    run()
