import hashlib

import streamlit as st

from phishguard_ui import checker

EXAMPLES = {
    "Scam text": "URGENT: Your parcel is on hold. Pay the Rs 25 fee within 12 hours: http://indiapost-redelivery.top/pay",
    "Scam link": "http://paypa1-account-verify.com/signin",
    "Normal text": "Hey, are we still on for lunch tomorrow at 1? Let me know.",
}
LOOK = {"fraud": ("red", ":material/gpp_bad:"), "careful": ("orange", ":material/warning:"),
        "safe": ("green", ":material/verified_user:"), "unknown": ("gray", ":material/help:")}
SIGNS = [
    (":material/timer:", "Rushes you", "“Act now”, “within 24 hours”, “account locked”."),
    (":material/link_off:", "Odd link", "Misspelt names, strange endings like .top or .xyz."),
    (":material/payments:", "Wants money or passwords", "Real companies never ask for these by message."),
]


def show(result: dict):
    verdict = result["verdict"] if result["verdict"] in LOOK else "unknown"
    color, icon = LOOK[verdict]
    with st.container(key=f"verdict_{verdict}"):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown(f"# :{color}[{icon}]", width="content")
            st.markdown(f"## {result['title']}")
        for r in result["reasons"]:
            st.markdown(f":{color}[:material/chevron_right:] {r}")


def use_example(text: str):
    st.session_state.check_text = text
    st.session_state.check_result = checker().check_text(text)


st.title("Is it a scam?", icon=":material/search_check:")
st.caption("Paste a link or message, or upload a QR code or screenshot.")

with st.container(border=True):
    text = st.text_area("Link or message", key="check_text", height=140,
                        placeholder="Paste a link, email or text message here…", label_visibility="collapsed")
    with st.container(horizontal=True, vertical_alignment="center"):
        if st.button("Check", type="primary", disabled=not text.strip()):
            with st.spinner("Checking…"):
                st.session_state.check_result = checker().check_text(text)
        st.caption("Try:", width="content")
        for label, example in EXAMPLES.items():
            st.button(label, on_click=use_example, args=(example,), icon=":material/science:")

    upload = st.file_uploader("Or upload a QR code or screenshot", type=["png", "jpg", "jpeg", "webp"])
    if upload is not None:
        data = upload.getvalue()
        digest = hashlib.md5(data).hexdigest()
        if st.session_state.get("check_file") != digest:  # check each new picture once
            with st.spinner("Checking the picture…"):
                st.session_state.check_result = checker().check_file(data, upload.name, upload.type)
            st.session_state.check_file = digest
        st.image(data, width=180)

if "check_result" in st.session_state:
    show(st.session_state.check_result)
else:
    st.subheader("Signs of a scam")
    with st.container(horizontal=True, gap="medium"):
        for i, (icon, title, blurb) in enumerate(SIGNS):
            with st.container(key=f"sign_{i}", height="stretch"):
                st.markdown(f"## :red[{icon}]")
                st.markdown(f"**{title}**  \n:gray[{blurb}]")
