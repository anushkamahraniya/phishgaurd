import streamlit as st

st.set_page_config(page_title="PhishGuard", page_icon=":material/shield:", layout="wide")

if "emp_id" not in st.session_state:
    st.session_state.emp_id = "EMP-101"

page = st.navigation(
    [
        st.Page("app_pages/check.py", title="Is it a scam?", icon=":material/search_check:", default=True),
        st.Page("app_pages/overview.py", title="Overview", icon=":material/dashboard:"),
        st.Page("app_pages/people.py", title="People", icon=":material/group:"),
        st.Page("app_pages/why.py", title="Why at risk?", icon=":material/help:"),
        st.Page("app_pages/quiz.py", title="Spot the phish", icon=":material/phishing:"),
    ],
    position="top",
)
page.run()
