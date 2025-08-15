# assistant.py
import json
import os
from datetime import datetime, timedelta
from calendar import monthrange

TASKS_FILE = "tasks.json"

# ---------- Storage ----------
def _ensure_store():
    if not os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "w") as f:
            f.write("[]")

def load_tasks():
    _ensure_store()
    try:
        with open(TASKS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_tasks(tasks):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=4)

# ---------- Utilities ----------
def speak(text: str):
    """Offline TTS (pyttsx3). Creates its own engine per call for reliability."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        # choose second voice if available (usually female)
        if len(voices) > 1:
            engine.setProperty('voice', voices[1].id)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"[speak] Warning: {e}")

def notify(title: str, message: str):
    """
    Desktop notification. Prefers Windows 10 toast if available,
    else falls back to plyer notification.
    """
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(title, message, duration=5, threaded=True)
        return
    except Exception:
        pass

    try:
        from plyer import notification
        notification.notify(title=title, message=message, timeout=5)
    except Exception as e:
        print(f"[notify] {title}: {message} (Notification fallback, {e})")

# ---------- Date helpers ----------
def validate_due_str(due_str: str) -> bool:
    try:
        datetime.strptime(due_str, "%Y-%m-%d %H:%M")
        return True
    except ValueError:
        return False

def _add_months(dt: datetime, months: int) -> datetime:
    # month arithmetic that keeps end-of-month semantics
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, monthrange(year, month)[1])
    return datetime(year, month, day, dt.hour, dt.minute)

def _add_years(dt: datetime, years: int) -> datetime:
    year = dt.year + years
    # handle Feb 29
    day = dt.day
    if dt.month == 2 and dt.day == 29:
        # if target year not leap, use 28
        try:
            return datetime(year, 2, 29, dt.hour, dt.minute)
        except ValueError:
            return datetime(year, 2, 28, dt.hour, dt.minute)
    return datetime(year, dt.month, day, dt.hour, dt.minute)

# assistant.py

def next_due(due_str: str, recurrence: str, minutes_interval: int = None) -> str:
    """
    Given a due_str 'YYYY-MM-DD HH:MM' and recurrence type, 
    returns the next due_str.
    """
    dt = datetime.strptime(due_str, "%Y-%m-%d %H:%M")
    if recurrence == "daily":
        dt = dt + timedelta(days=1)
    elif recurrence == "weekly":
        dt = dt + timedelta(weeks=1)
    elif recurrence == "monthly":
        dt = _add_months(dt, 1)
    elif recurrence == "yearly":
        dt = _add_years(dt, 1)
    elif recurrence == "every_x_minutes":
        if not minutes_interval:
            raise ValueError("minutes_interval must be provided for every_x_minutes recurrence")
        dt = dt + timedelta(minutes=minutes_interval)
    else:
        raise ValueError("Invalid recurrence for next_due")
    return dt.strftime("%Y-%m-%d %H:%M")


def add_task(description: str, due_str: str, recurrence: str = None, minutes_interval: int = None):
    """
    Adds task. recurrence should be None or one of: 
    'daily','weekly','monthly','yearly','every_x_minutes'
    """
    if not description.strip():
        raise ValueError("Task description cannot be empty.")
    if not validate_due_str(due_str):
        raise ValueError("Invalid date/time format. Use YYYY-MM-DD HH:MM")

    valid_recurrences = {None, "daily", "weekly", "monthly", "yearly", "every_x_minutes"}
    if recurrence not in valid_recurrences:
        raise ValueError(f"Recurrence must be one of {valid_recurrences}")

    tasks = load_tasks()
    task_data = {
        "description": description.strip(),
        "due": due_str,
        "done": False,
        "recurrence": recurrence
    }
    if recurrence == "every_x_minutes":
        if not minutes_interval or minutes_interval <= 0:
            raise ValueError("Minutes interval must be a positive integer for every_x_minutes")
        task_data["minutes_interval"] = minutes_interval

    tasks.append(task_data)
    save_tasks(tasks)
    speak(f"Task added: {description} at {due_str}{' repeating ' + recurrence if recurrence else ''}")


def delete_task(index: int):
    tasks = load_tasks()
    if 0 <= index < len(tasks):
        removed = tasks.pop(index)
        save_tasks(tasks)
        speak(f"Deleted task {removed.get('description','')}")
    else:
        raise IndexError("Task index out of range.")

def mark_done(index: int, done: bool = True):
    """
    Mark a task done or not done. If marking done and task has recurrence,
    reschedule to next occurrence (and keep done=False). If no recurrence,
    set done flag.
    """
    tasks = load_tasks()
    if 0 <= index < len(tasks):
        task = tasks[index]
        recurrence = task.get("recurrence")
        if done and recurrence:
            # compute next due and leave task as pending
            old_due = task.get("due")
            try:
                task["due"] = next_due(old_due, recurrence)
                task["done"] = False
                speak(f"Task rescheduled for {task['due']}")
            except Exception as e:
                # fallback: mark done if next due fails
                task["done"] = True
                speak(f"Error rescheduling task; marked done. ({e})")
        else:
            task["done"] = done
            status = "completed" if done else "reopened"
            speak(f"Task {status}: {task.get('description','')}")
        save_tasks(tasks)
    else:
        raise IndexError("Task index out of range.")
