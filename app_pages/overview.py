import time

import altair as alt
import pandas as pd
import streamlit as st

from phishguard_ui import MOD, ONE, engine, go, risk_badge

data = engine().dashboard()
k = data["kpis"]

st.title("Overview")
st.caption(f"{k['staff']:,} people tested with safe, fake phishing messages")

with st.container(horizontal=True):
    st.metric(":red[High risk]", k["high_risk"], help="Likely to fall for a real attack", border=True)
    st.metric(":orange[Watch]", k["medium_risk"], help="Could go either way", border=True)
    st.metric(":green[Safe]", k["low_risk"], help="Spot most phishing", border=True)

left, right = st.columns([3, 2])

with left.container(border=True):
    st.subheader("Needs attention")
    for e in data["attention"]:
        with st.container(horizontal=True, vertical_alignment="center"):
            note = " · :red[**Failed the quiz**]" if e["flagged"] else ""
            st.markdown(f"**{e['name']}**  \n:gray[{e['dept']}]{note}", width="stretch")
            risk_badge(e["risk"], e["level"])
            if st.button("Why?", key=f"why_{e['id']}"):
                go("app_pages/why.py", e["id"])
            if st.button("Train", key=f"train_{e['id']}"):
                go("app_pages/quiz.py", e["id"])

with right.container(border=True):
    st.subheader("What fools people most")
    df = pd.DataFrame([{"Type": MOD[m["modality"]], "Clicked": m["fail_rate"]} for m in data["modality"]])
    chart = alt.Chart(df).mark_bar(color="#2D3142", cornerRadiusEnd=4).encode(
        x=alt.X("Clicked:Q", title="Share of fake messages clicked (%)"),
        y=alt.Y("Type:N", sort="-x", title=None),
        tooltip=["Type", alt.Tooltip("Clicked:Q", format=".0f", title="Clicked %")],
    )
    st.altair_chart(chart, height=240)

VERB = {"Clicked": ":red[fell for]", "Reported": ":green[reported]", "Ignored": ":gray[ignored]",
        "Passed training": ":green[passed training]", "Failed quiz": ":red[failed the quiz]"}


def ago(ts: float) -> str:
    s = max(0, time.time() - ts)
    return "just now" if s < 60 else f"{int(s // 60)} min ago" if s < 3600 else f"{int(s // 3600)} h ago" if s < 86400 else f"{int(s // 86400)} d ago"


with st.container(border=True):
    st.subheader("Recent activity")
    for e in data["activity"][:6]:
        what = f" a fake {ONE[e['modality']]}" if e["modality"] in ONE else ""
        st.markdown(f"**{e['emp']}** {VERB.get(e['status'], e['status'].lower())}{what} :gray[· {ago(e['at'])}]")
