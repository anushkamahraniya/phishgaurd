import streamlit as st

from phishguard_ui import engine, go

FEATURES = [
    ("check", ":red[:material/gpp_bad:]", "Is it a scam?", "Paste a link or message, or upload a QR code. Get a clear answer.",
     "app_pages/check.py"),
    ("quiz", ":orange[:material/phishing:]", "Spot the phish", "A short quiz with real-looking fakes. Learn the signs fast.",
     "app_pages/quiz.py"),
    ("overview", ":green[:material/dashboard:]", "Overview", "See who on your team is safe and who needs help.",
     "app_pages/overview.py"),
    ("why", ":gray[:material/help:]", "Why at risk?", "Find out what trips each person up, and what fixes it.",
     "app_pages/why.py"),
]
STEPS = [
    ("01", "Paste it", "A link, email, text or QR code."),
    ("02", "See the answer", "Scam, be careful, or safe, with the reasons why."),
    ("03", "Learn the signs", "Practise with the quiz so you spot the next one."),
]

# ------------------------------------------------------------------ hero
with st.container(key="hero"):
    text, card = st.columns([3, 2], gap="large", vertical_alignment="center")
    with text:
        st.badge("Stay one step ahead of scammers", icon=":material/shield:", color="orange")
        st.title("Spot the scam before it costs you.")
        st.markdown("Check any link, message or QR code in seconds. Then teach your team the signs.")
        with st.container(horizontal=True):
            if st.button("Check something now", key="hero_go", icon=":material/search_check:"):
                go("app_pages/check.py")
            if st.button("Take the quiz", key="hero_quiz", icon=":material/play_arrow:"):
                go("app_pages/quiz.py")
    with card.container(key="hero_card"):
        st.caption(":material/sms: New message")
        st.markdown("URGENT: Your parcel is on hold. Pay the Rs 25 fee within 12 hours: "
                    ":blue[indiapost-redelivery.top/pay]")
        st.error("**This is a scam**  \nFake website · Rushes you · Asks for money", icon=":material/gpp_bad:")

stats = st.container(key="stats", horizontal=True)  # filled last: it needs the employee data

# ---------------------------------------------------------------- features
st.space("medium")
st.header("Everything in one place", text_alignment="center")
st.caption("Pick where to start.", text_alignment="center")
with st.container(horizontal=True, gap="medium"):
    for key, icon, title, blurb, page in FEATURES:
        with st.container(key=f"feat_{key}", height="stretch"):
            st.markdown(f"## {icon}")
            st.subheader(title)
            st.markdown(f":gray[{blurb}]")
            if st.button("Open", key=f"open_{key}", icon=":material/arrow_forward:", icon_position="right",
                         type="tertiary"):
                go(page)

# ------------------------------------------------------------ how it works
st.space("medium")
st.header("How it works", text_alignment="center")
with st.container(horizontal=True, gap="medium"):
    for num, title, blurb in STEPS:
        with st.container(key=f"step_{num}", height="stretch"):
            st.markdown(f"### :orange[{num}]")
            st.markdown(f"**{title}**  \n:gray[{blurb}]")

# --------------------------------------------------------------- final CTA
st.space("medium")
with st.container(key="cta", horizontal_alignment="center"):
    st.header("Got a strange message?", text_alignment="center")
    st.markdown("Don't click it. Check it first.", text_alignment="center")
    if st.button("Check it now", key="cta_go", icon=":material/search_check:"):
        go("app_pages/check.py")

st.caption("PhishGuard · All tests use safe, fake messages.", text_alignment="center")

# ------------------------------------------------------- live numbers (slow)
k = engine().summary_numbers()
with stats:
    st.metric("People tested", f"{k['staff']:,}", border=True)
    st.metric("Need help now", k["high_risk"], border=True)
    st.metric("Scam types checked", "4", help="Emails, links, QR codes and phone calls", border=True)
