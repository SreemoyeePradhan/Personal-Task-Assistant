# reminder.py
import time
from datetime import datetime
import schedule
from assistant import load_tasks, save_tasks, speak, notify, next_due

def _now_minute():
    # Compare at minute granularity
    return datetime.now().strftime("%Y-%m-%d %H:%M")

# reminder.py


def check_tasks():
    tasks = load_tasks()
    now_str = _now_minute()
    updated = False

    for task in tasks:
        due = task.get("due")
        done = task.get("done", False)
        desc = task.get("description", "Untitled task")
        recurrence = task.get("recurrence")
        minutes_interval = task.get("minutes_interval", None)

        if (not done) and (due == now_str):
            msg = f"Reminder: {desc}"
            print(f"🔔 {msg}")
            notify("Task Reminder", msg)
            speak(msg)

            if recurrence:
                try:
                    new_due = next_due(due, recurrence, minutes_interval)
                    task["due"] = new_due
                    task["done"] = False
                    print(f"↪ Rescheduled recurring task to {new_due}")
                except Exception as e:
                    task["done"] = True
                    print(f"[reminder] Failed to reschedule task: {e}")
            else:
                task["done"] = True

            updated = True

    if updated:
        save_tasks(tasks)


def start_reminders():
    print("⏰ Reminder scheduler started (checks every minute).")
    speak("Reminder scheduler started.")
    schedule.every(1).minutes.do(check_tasks)

    # Also check immediately at startup
    check_tasks()

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    start_reminders()
