import io

import qrcode
import streamlit as st

from phishguard_ui import LEVEL, course, engine, level_of, pct, person_picker, risk_badge

RIGHT, WRONG = 10, -5

st.title("Spot the phish")
emp_id = person_picker("Taking the quiz as")

quiz = st.session_state.get("quiz")
if not quiz or quiz["emp"] != emp_id:  # new person: fresh quiz
    t = engine().training(emp_id)
    quiz = st.session_state.quiz = {"emp": emp_id, "data": t, "phase": "tips", "qi": 0, "answers": {},
                                    "feedback": {}, "points": 0, "start_risk": t["employee"]["risk"], "result": None}
data = quiz["data"]
first = data["employee"]["name"].split()[0]


def restart():
    st.session_state.pop("quiz", None)


def answer(qid: str, value: str):
    f = engine().check_answer(qid, value, emp_id)
    quiz["answers"][qid] = value
    quiz["feedback"][qid] = f
    quiz["points"] += RIGHT if f["correct"] else WRONG


def show_example(a: dict):
    with st.container(border=True):
        if a["type"] == "email":
            st.markdown(f"**{a['subject']}**  \n:gray[From: {a['sender']}]")
            st.markdown(a["body"].replace("\n", "  \n"))
            if a.get("cta"):
                st.badge(a["cta"], color="blue")
        elif a["type"] == "url":
            st.code(a["url"], language=None, wrap_lines=True)
        elif a["type"] == "call":
            st.markdown(f":material/call: Voicemail from **{a['caller']}**")
            st.markdown(f"> *“{a['transcript']}”*")
        elif a["type"] == "image" and a["image"] == "quota":
            st.markdown("**Mailbox storage**  \n99.8 GB of 100 GB used")
            st.progress(0.998)
            st.badge("Expand quota", color="blue")
            st.caption(a.get("caption", ""))
        else:
            buf = io.BytesIO()
            qrcode.make("https://example.com/this-was-a-phishing-test").save(buf, format="PNG")
            st.markdown("**Invoice #88294 · €4,812.00**  \n:red[OVERDUE, pay within 24 h]")
            st.image(buf.getvalue(), width=140)
            st.caption(a.get("caption", ""))


with st.container(border=True, horizontal=True, vertical_alignment="center"):
    st.markdown(f"**{data['employee']['name']}**", width="stretch")
    risk_badge(data["employee"]["risk"], data["employee"]["level"])
    pts = quiz["points"]
    st.markdown(f"Points :{'red' if pts < 0 else 'green'}[**{pts}**]", width="content")

if quiz["phase"] == "tips":
    with st.container(border=True):
        st.subheader(course(data["module"]["name"]))
        cols = st.columns(3)
        for col, tip in zip(cols, data["module"]["tips"]):
            with col.container(border=True, height="stretch"):
                st.markdown(f":green[:material/verified_user:] **{tip['title']}**")
                st.caption(tip["body"])
        if st.button("Start the quiz", type="primary", icon=":material/play_arrow:"):
            quiz["phase"] = "quiz"
            st.rerun()

elif quiz["phase"] == "quiz":
    qs = data["questions"]
    q = qs[quiz["qi"]]
    fb = quiz["feedback"].get(q["id"])
    with st.container(border=True):
        st.subheader(f"Question {quiz['qi'] + 1} of {len(qs)}")
        st.progress(len(quiz["feedback"]) / len(qs))
        left, right = st.columns(2)
        with left:
            show_example(q["artifact"])
        with right:
            st.markdown(f"**{q['prompt']}**")
            options = [("phish", "Phishing — it’s a scam"), ("legit", "Safe — it’s real")] if q["kind"] == "verdict" \
                else [(o["id"], o["text"]) for o in q["options"]]
            for value, label in options:
                if fb:
                    mark = ":green[:material/check_circle:]" if value == fb["answer"] else \
                        ":red[:material/cancel:]" if value == quiz["answers"][q["id"]] else ":gray[:material/radio_button_unchecked:]"
                    st.markdown(f"{mark} {label}")
                else:
                    st.button(label, key=f"{q['id']}_{value}", on_click=answer, args=(q["id"], value), width="stretch")
            if fb:
                if fb["correct"]:
                    st.success(f"**Correct! +{RIGHT} points**  \n{fb['explain']}", icon=":material/check_circle:")
                else:
                    st.error(f"**You fell for it. {WRONG} points**  \n{fb['explain']}  \n\n"
                             f"**{first} was added to the Needs attention list.**", icon=":material/cancel:")
                last = quiz["qi"] == len(qs) - 1
                if st.button("See my result" if last else "Next", type="primary", icon=":material/arrow_forward:"):
                    if last:
                        quiz["result"] = engine().submit_quiz(emp_id, quiz["answers"])
                        quiz["phase"] = "done"
                    else:
                        quiz["qi"] += 1
                    st.rerun()

else:
    r = quiz["result"]
    with st.container(border=True, horizontal_alignment="center"):
        if r["passed"]:
            st.success(f"### Passed! {r['score']} of {r['total']}  \n{first} is off the Needs attention list.", icon=":material/check_circle:")
        else:
            st.error(f"### {r['score']} of {r['total']}, not passed yet  \nGet {r['needed']} right to pass.", icon=":material/cancel:")
        before, after = quiz["start_risk"], r["risk_after"]
        cb, ca = LEVEL[level_of(before)][1], LEVEL[level_of(after)][1]
        st.markdown(f"## Risk :{cb}[{pct(before)}%] → :{ca}[{pct(after)}%]", text_alignment="center")
        st.caption(f"{quiz['points']} points", text_alignment="center")
        st.button("Try again", icon=":material/refresh:", on_click=restart)
