import streamlit as st

from app.advisor import SUPPORTED_LANGUAGES, generate_advice


st.set_page_config(page_title="FD Mitra UI", page_icon="💰", layout="centered")

st.title("💰 Vernacular FD Advisor")
st.caption("Simple FD guidance for local users (localhost UI)")

with st.container():
    st.subheader("Step 1: Basic Details")
    username = st.text_input("Aapka naam", value="Guest")
    language = st.selectbox("Language", [v for v in SUPPORTED_LANGUAGES.values()], index=0)
    reason = st.text_input("Paisa kis kaam ke liye rakhna hai? (aap apni marzi se likho)", value="future planning")
    amount = st.number_input("Kitna paisa invest karna chahte ho? (INR)", min_value=100.0, value=10000.0, step=500.0)
    tenor = st.number_input("Kitne mahine ke liye FD chahiye? (optional)", min_value=0, value=12, step=1)

if "advice" not in st.session_state:
    st.session_state["advice"] = None

if st.button("Step 2: FD Estimate Dekho 📈", use_container_width=True):
    try:
        st.session_state["advice"] = generate_advice(
            username=username.strip() or "Guest",
            user_reason=reason,
            lang_input=language,
            investment_amount=float(amount),
            preferred_tenor_months=int(tenor) if tenor > 0 else None,
        )
    except Exception as exc:
        st.error(f"Kuch issue aaya: {exc}")

advice = st.session_state.get("advice")
if advice:
    st.subheader("Step 3: Estimated Return")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Interest (Approx)", f"INR {advice.estimated_interest:,.2f}")
        st.metric("Rate", f"{advice.rate}% p.a.")
    with col2:
        st.metric("Maturity Amount", f"INR {advice.maturity_amount:,.2f}")
        st.metric("Tenor", f"{advice.tenor_months} months")

    st.info(f"Suggested Bank: {advice.bank_name}")
    st.write(advice.explanation)
    st.caption("Yeh assistant guidance deta hai, direct FD booking nahi karta.")

    st.subheader("Step 4: Confirmation")
    confirm = st.radio("Kya aap FD booking ke steps dekhna chahte ho?", ["No", "Yes"], horizontal=True)

    if confirm == "Yes":
        st.success("Step 5: FD khud book karne ke steps")
        st.markdown(
            "1. Bank app/branch choose karo\n"
            "2. Amount aur tenor select karo\n"
            "3. Nominee add karo\n"
            "4. Interest payout option choose karo\n"
            "5. Details verify karke confirm karo"
        )
        st.caption("Final decision aapka hai.")
