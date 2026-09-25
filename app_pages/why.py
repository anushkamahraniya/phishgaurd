import streamlit as st

from phishguard_ui import MOD, course, engine, go, level_of, pct, person_picker, plan_step, reason, risk_badge

st.title("Why at risk?")
emp_id = person_picker("Pick a person")

e = engine().explain_employee(emp_id)
emp = e["employee"]
first = emp["name"].split()[0]
color = {"High": "red", "Medium": "orange", "Low": "green"}[e["level"]]

with st.container(border=True, horizontal=True, vertical_alignment="center"):
    st.markdown(f"# :{color}[{pct(e['risk'])}%]", width="content")
    st.markdown(f"**{emp['name']}**  \n:gray[{emp['dept']}]", width="stretch")
    risk_badge(e["risk"], e["level"])

a, b, c = st.columns(3)

with a.container(border=True, height="stretch"):
    st.subheader("What is happening?")
    st.markdown(f"{first} would likely fall for **{pct(e['risk'])} in 100** phishing messages.")
    st.caption("Weakest spot")
    st.markdown(f"**{MOD[emp['weakness']]}**")
    if emp["flagged"]:
        st.error("Fell for a phish in the quiz", icon=":material/warning:")

with b.container(border=True, height="stretch"):
    st.subheader("Why?")
    reasons = [reason(x) + (abs(x["shap"]),) for x in e["contributions"]]
    bad = [r for r in reasons if r[2] and r[3] >= 0.5][:3]
    good = [r for r in reasons if not r[2] and r[3] >= 0.5][:2]
    for text, detail, up, _ in bad + good:
        icon = ":red[**▲**]" if up else ":green[**▼**]"
        st.markdown(f"{icon} **{text}**" + (f"  \n:gray[{detail}]" if detail else ""))
    if not bad and not good:
        st.caption("Nothing stands out.")

with c.container(border=True, height="stretch"):
    st.subheader("What next?")
    st.caption("Best course")
    st.markdown(f"**{course(e['recommendation']['module'])}**")
    for s in [s for s in e["counterfactuals"] if s["delta"] < -0.5][:3]:
        col = {"High": "red", "Medium": "orange", "Low": "green"}[level_of(s["risk"])]
        st.markdown(f"{plan_step(s['change'])} → :{col}[**{pct(s['risk'])}%**]")
    if st.button("Start training", icon=":material/school:", type="primary", width="stretch"):
        go("app_pages/quiz.py", emp_id)
