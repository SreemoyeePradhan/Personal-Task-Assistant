# ui.py
import threading
from datetime import datetime, date, time as dtime

import streamlit as st
from assistant import (
    add_task, load_tasks, delete_task, mark_done, validate_due_str
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

# --- Add Task ---
st.subheader("➕ Add a New Task")
col1, col2 = st.columns(2)
with col1:
    desc = st.text_input("Task description", placeholder="e.g., Call mom")
with col2:
    # Combine a date and time input into the required string format
    due_date = st.date_input("Due date", value=date.today())
    due_time = st.time_input("Due time (HH:MM)", value=dtime(hour=datetime.now().hour, minute=(datetime.now().minute + 1) % 60))

if st.button("Add Task"):
    due_str = f"{due_date.strftime('%Y-%m-%d')} {due_time.strftime('%H:%M')}"
    try:
        add_task(desc, due_str)
        st.success(f"Added: {desc} @ {due_str}")
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
            st.caption(f"Due: {task.get('due','N/A')}")
        with c2:
            done_flag = task.get("done", False)
            st.write("✅ Done" if done_flag else "⏳ Pending")
        with c3:
            if st.button("Toggle", key=f"toggle_{i}"):
                mark_done(i, not task.get("done", False))
                st.experimental_rerun()
        with c4:
            if st.button("🗑️ Delete", key=f"delete_{i}"):
                delete_task(i)
                st.experimental_rerun()

st.markdown("---")
st.caption("Tip: The reminder checks at minute granularity (YYYY-MM-DD HH:MM).")
