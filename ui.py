# ui.py
import threading
from datetime import datetime, date, time as dtime

import streamlit as st
from assistant import (
    add_task, load_tasks, delete_task, mark_done, parse_nlp_task
)
import reminder

st.set_page_config(page_title="Personal Task Assistant", page_icon="📝", layout="centered")
st.title("📝 Personal Task Assistant")

# --- Start / status of reminders (per-session thread) ---
if "reminder_thread_started" not in st.session_state:
    st.session_state.reminder_thread_started = False

def start_scheduler_bg():
    if not st.session_state.reminder_thread_started:
        t = threading.Thread(target=reminder.start_reminders, daemon=True)
        t.start()
        st.session_state.reminder_thread_started = True

with st.sidebar:
    st.header("⚙️ Controls")
    if st.button("▶ Start Reminder Scheduler"):
        start_scheduler_bg()
        st.success("Reminder scheduler started in the background for this session.")

    st.markdown("---")
    st.caption("Keep this page open if you rely on the scheduler here. "
               "Alternatively, run `python main.py` to keep reminders running without the browser.")

# --- Add Task (Option 1: Natural Language Input) ---
st.subheader("➕ Add a New Task (Smart Input)")
nlp_text = st.text_area(
    "Describe your task naturally",
    placeholder="e.g., Call mom tomorrow at 6 pm every week"
)

if st.button("Add via NLP"):
    if not nlp_text.strip():
        st.warning("Please enter a description.")
    else:
        try:
            parsed = parse_nlp_task(nlp_text)

            if not parsed or "description" not in parsed:
                st.error("❌ Could not extract a valid task description. Please try again.")
            else:
                desc = parsed.get("description", "Untitled Task")
                due_str = parsed.get("due", None)
                recurrence = parsed.get("recurrence", None)
                interval = parsed.get("minutes_interval", None)

                add_task(desc, due_str, recurrence, interval)
                st.success(f"✅ Added: {desc} @ {due_str or 'N/A'} ({recurrence or 'None'})")

            # Debug view for dev/testing
            st.json(parsed)

        except Exception as e:
            st.error(f" Parsing failed. Try formats like 'Call mom tomorrow at 6 pm' or 'Submit report 2025-08-17 14:30'. Error: {e}")

# --- Add Task (Option 2: Manual Form) ---
st.subheader("➕ Add a New Task (Manual Entry)")
col1, col2 = st.columns(2)

with col1:
    desc = st.text_input("Task description", placeholder="e.g., Finish report")
    recurrence_choice = st.selectbox(
        "Recurrence",
        options=["None", "Daily", "Weekly", "Monthly", "Yearly", "Every X minutes"],
        index=0
    )
    minutes_interval = None
    if recurrence_choice == "Every X minutes":
        minutes_interval = st.number_input(
            "Interval (minutes)", min_value=1, max_value=1440, value=5
        )

with col2:
    due_date = st.date_input("Due date", value=date.today())
    due_time = st.time_input(
        "Due time (HH:MM)",
        value=dtime(
            hour=datetime.now().hour,
            minute=(datetime.now().minute + 1) % 60
        )
    )

if st.button("Add via Form"):
    if not desc.strip():
        st.warning("Please enter a task description.")
    else:
        recurrence_map = {
            "None": None,
            "Daily": "daily",
            "Weekly": "weekly",
            "Monthly": "monthly",
            "Yearly": "yearly",
            "Every X minutes": "every_x_minutes"
        }
        recurrence = recurrence_map.get(recurrence_choice, None)
        due_str = f"{due_date.strftime('%Y-%m-%d')} {due_time.strftime('%H:%M')}"
        try:
            add_task(desc, due_str, recurrence, minutes_interval)
            st.success(f"✅ Added: {desc} @ {due_str} ({recurrence_choice})")
        except Exception as e:
            st.error(str(e))

# --- Task List ---
st.subheader("📋 Tasks")
tasks = load_tasks()
if not tasks:
    st.info("No tasks yet. Add your first one above!")
else:
    for i, task in enumerate(tasks):
        c1, c2, c3, c4 = st.columns([6, 3, 1.4, 1.4])
        with c1:
            st.write(f"**{i+1}. {task.get('description','')}**")
            rec = task.get("recurrence")
            rec_label = rec.capitalize() if rec else "None"
            st.caption(f"Due: {task.get('due','N/A')} — Recurrence: {rec_label}")
        with c2:
            done_flag = task.get("done", False)
            st.write("✅ Done" if done_flag else "⏳ Pending")
        with c3:
            if st.button("Toggle", key=f"toggle_{i}"):
                mark_done(i, not task.get("done", False))
                st.rerun()
        with c4:
            if st.button("🗑️ Delete", key=f"delete_{i}"):
                delete_task(i)
                st.rerun()

st.markdown("---")
st.caption("Tip: Try adding tasks in natural language (e.g., 'Submit assignment next Monday 9am, repeat weekly').")
