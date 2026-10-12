"""Penny - Streamlit chat UI."""
import json
import time
from pathlib import Path

import streamlit as st

import agent as penny

FEEDBACK = Path(__file__).parent / "feedback.jsonl"
BADGE = {"GREEN": ("🟢", "All looks normal"), "YELLOW": ("🟡", "Worth a look"), "RED": ("🔴", "Act today")}
STARTERS = ["Why did my bill go up?", "What's costing me the most?", "Is there anything I should switch off right now?"]

st.set_page_config(page_title="Penny - your AWS bill buddy", page_icon="🪙")


def esc_dollars(t: str) -> str:
    return t.replace("\\$", "$").replace("$", "\\$")


def read_feedback():
    up = down = 0
    if FEEDBACK.exists():
        for line in FEEDBACK.read_text().splitlines():
            try:
                r = json.loads(line)
                up += r["rating"] == "up"
                down += r["rating"] == "down"
            except Exception:
                pass
    return up, down


def save_feedback(idx: int, rating: str):
    msg = st.session_state.messages[idx]
    msg["rated"] = rating
    with FEEDBACK.open("a") as f:
        f.write(json.dumps({"ts": time.time(), "rating": rating, "verdict": msg.get("verdict"),
                            "question": st.session_state.messages[idx - 1]["content"]}) + "\n")


# ---------- sidebar ----------
with st.sidebar:
    st.header("🪙 Penny")
    st.caption("A read-only bill buddy. I can look at your costs, but I can never change anything.")
    live = st.toggle("Use my real AWS account", value=False,
                     help="Reads costs from Cost Explorer (read-only). Each Cost Explorer request costs about $0.01.")
    penny.STATE["mode"] = "live" if live else "demo"
    st.info("Live mode: reading your account via Cost Explorer." if live else "Demo mode: sample billing data (Amazon Bedrock model still requires AWS credentials).")
    language = st.selectbox("Reply language", list(penny.LANGUAGES.keys()))
    up, down = read_feedback()
    st.metric("Answers rated 👍 / 👎", f"{up} / {down}")
    if any(m["role"] == "assistant" and not m.get("error") for m in st.session_state.get("messages", [])):
        st.download_button("⬇️ Save bill check-up (.md)", penny.make_report(st.session_state.messages, penny.STATE["mode"]),
                           file_name="penny-bill-checkup.md", mime="text/markdown")
    if st.button("Start over"):
        st.session_state.messages = []
        st.session_state.pop("agent", None)
        st.rerun()

# ---------- state ----------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    st.session_state.agent = penny.build_agent()

st.title("🪙 Penny")
st.write("Hi, I'm Penny. Seen a surprise on your AWS bill? Tell me what's worrying you and I'll explain it in plain English, no jargon, no panic.")

# ---------- history ----------
for i, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"], avatar="🪙" if m["role"] == "assistant" else None):
        if m.get("verdict"):
            icon, label = BADGE[m["verdict"]]
            st.markdown(f"**{icon} {label}**")
        st.markdown(esc_dollars(m["content"]))
        if m["role"] == "assistant" and not m.get("error"):
            if m.get("rated"):
                st.caption("Thanks for the feedback 💛")
            else:
                c1, c2, _ = st.columns([1, 1, 8])
                c1.button("👍", key=f"up{i}", on_click=save_feedback, args=(i, "up"))
                c2.button("👎", key=f"dn{i}", on_click=save_feedback, args=(i, "down"))

# ---------- starter chips (first run only) ----------
prompt = None
if not st.session_state.messages:
    st.caption("Not sure where to start? Try one:")
    cols = st.columns(3)
    for col, s in zip(cols, STARTERS):
        if col.button(s, use_container_width=True):
            prompt = s
typed = st.chat_input("Ask about your AWS bill…")
prompt = prompt or typed

# ---------- answer ----------
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar="🪙"):
        try:
            with st.spinner("Checking your bill…"):
                answer, verdict = penny.ask(st.session_state.agent, prompt, penny.LANGUAGES[language])
            st.session_state.messages.append({"role": "assistant", "content": answer, "verdict": verdict})
        except Exception as e:  # never show a stack trace to a worried beginner
            st.session_state.messages.append({"role": "assistant", "content": penny.friendly_error(e), "error": True})
            st.session_state.pop("agent", None)
    st.rerun()
