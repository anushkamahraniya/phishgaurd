import pandas as pd
import streamlit as st

from phishguard_ui import LEVEL, MOD, engine, go, pct

FILTERS = {"Everyone": "All", "Needs attention": "Attention", "High risk": "High", "Watch": "Medium", "Safe": "Low"}

st.title("People")

with st.container(horizontal=True, vertical_alignment="bottom"):
    q = st.text_input("Search", placeholder="Search by name…", label_visibility="collapsed", width=260)
    shown = st.segmented_control("Show", list(FILTERS), default="Everyone", required=True, label_visibility="collapsed")
    if st.button("Assign training to at-risk people", icon=":material/auto_fix_high:", type="primary"):
        n = len(engine().auto_assign())
        st.toast(f"Training assigned to {n} people." if n else "Everyone at risk already has training.")

rows = engine().employees(search=q, lvl=FILTERS[shown], size=5000)["rows"]
st.caption(f"{len(rows):,} shown · select a row to see why or start training")

df = pd.DataFrame([{
    "id": r["id"],
    "Name": r["name"] + ("  ⚠ failed quiz" if r["flagged"] else ""),
    "Department": r["dept"],
    "Risk": pct(r["risk"]),
    "Level": LEVEL[r["level"]][0],
    "Weakest spot": MOD[r["weakness"]],
    "Training": "None" if not r["assigned_module"] else "Done" if r["completed"] else "To do",
} for r in rows])

pick = st.dataframe(
    df, hide_index=True, on_select="rerun", selection_mode="single-row", height=520,
    column_order=["Name", "Department", "Risk", "Level", "Weakest spot", "Training"],
    column_config={"Risk": st.column_config.ProgressColumn("Risk", min_value=0, max_value=100, format="%d%%")},
)

sel = pick.selection.rows
if sel:
    person = df.iloc[sel[0]]
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown(f"**{person['Name']}**")
        if st.button("Why at risk?", icon=":material/help:"):
            go("app_pages/why.py", person["id"])
        if st.button("Start training", icon=":material/school:"):
            go("app_pages/quiz.py", person["id"])
