import json
import os
import re
from datetime import datetime, timedelta
from calendar import monthrange

import dateparser  # for natural language date parsing

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
        if len(voices) > 1:
            engine.setProperty('voice', voices[1].id)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"[speak] Warning: {e}")

def notify(title: str, message: str):
    """Desktop notification with Windows toast or plyer fallback."""
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
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, monthrange(year, month)[1])
    return datetime(year, month, day, dt.hour, dt.minute)

def _add_years(dt: datetime, years: int) -> datetime:
    year = dt.year + years
    if dt.month == 2 and dt.day == 29:
        try:
            return datetime(year, 2, 29, dt.hour, dt.minute)
        except ValueError:
            return datetime(year, 2, 28, dt.hour, dt.minute)
    return datetime(year, dt.month, dt.day, dt.hour, dt.minute)

# ---------- Recurrence + NLP ----------
def next_due(due_str: str, recurrence: str, minutes_interval: int = None) -> str:
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

def extract_recurrence(text: str):
    """Detect recurrence rules from natural language."""
    text = text.lower()
    if "every day" in text or "daily" in text:
        return "daily", None
    if "every week" in text or "weekly" in text:
        return "weekly", None
    if "every month" in text or "monthly" in text:
        return "monthly", None
    if "every year" in text or "yearly" in text:
        return "yearly", None

    m = re.search(r"every (\d+)\s*minutes?", text)
    if m:
        return "every_x_minutes", int(m.group(1))

    m = re.search(r"every (\d+)\s*hours?", text)
    if m:
        return "every_x_minutes", int(m.group(1)) * 60

    return None, None

def parse_task(raw_text: str):
    """Parse freeform text with recurrence and due date."""
    if not raw_text.strip():
        raise ValueError("Empty task text")

    recurrence, minutes_interval = extract_recurrence(raw_text)

    due_dt = dateparser.parse(raw_text, settings={"PREFER_DATES_FROM": "future"})
    if not due_dt:
        raise ValueError("Could not detect a valid due date/time")

    due_str = due_dt.strftime("%Y-%m-%d %H:%M")

    desc = re.sub(
        r"(remind me to|every.*|daily|weekly|monthly|yearly|tomorrow|today|at \d+(:\d+)?(am|pm)?)",
        "",
        raw_text,
        flags=re.IGNORECASE,
    ).strip()

    if not desc:
        desc = raw_text

    return desc, due_str, recurrence, minutes_interval

# ---------- Task Management ----------
def add_task(description: str, due_str: str, recurrence: str = None, minutes_interval: int = None):
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
    tasks = load_tasks()
    if 0 <= index < len(tasks):
        task = tasks[index]
        recurrence = task.get("recurrence")
        if done and recurrence:
            old_due = task.get("due")
            try:
                task["due"] = next_due(old_due, recurrence, task.get("minutes_interval"))
                task["done"] = False
                speak(f"Task rescheduled for {task['due']}")
            except Exception as e:
                task["done"] = True
                speak(f"Error rescheduling task; marked done. ({e})")
        else:
            task["done"] = done
            status = "completed" if done else "reopened"
            speak(f"Task {status}: {task.get('description','')}")
        save_tasks(tasks)
    else:
        raise IndexError("Task index out of range.")

# ---------- NLP Parsing ----------
import re
import dateparser

def parse_nlp_task(text: str) -> dict:
    """
    Parse natural language task input into structured task fields.
    Supports recurrence and flexible time parsing.
    """
    text = text.strip()
    if not text:
        raise ValueError("Empty input")

    # Extract recurrence keywords
    recurrence = None
    interval = None
    if "every day" in text.lower() or "daily" in text.lower():
        recurrence = "daily"
    elif "every week" in text.lower() or "weekly" in text.lower():
        recurrence = "weekly"
    elif "every month" in text.lower() or "monthly" in text.lower():
        recurrence = "monthly"
    elif "every year" in text.lower() or "yearly" in text.lower():
        recurrence = "yearly"
    else:
        # check pattern: every X minutes
        match = re.search(r"every\s+(\d+)\s+minutes?", text.lower())
        if match:
            recurrence = "every_x_minutes"
            interval = int(match.group(1))

    # Parse datetime using robust settings
    dt = dateparser.parse(
        text,
        settings={
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": datetime.now(),
            "PREFER_DAY_OF_MONTH": "first",
            "RETURN_AS_TIMEZONE_AWARE": False,
        }
    )
    if not dt:
        raise ValueError(
            "Could not parse input. Please provide a valid time like "
            "'tomorrow 5pm' or '2025-08-17 14:30'."
        )

    # Try to remove the date/time part from description
    desc = text
    # If datetime string exists in parsed text, strip it from description
    for token in str(dt).split():
        desc = desc.replace(token, "")

    desc = desc.strip().rstrip(",. ")

    return {
        "description": desc if desc else text,
        "due": dt.strftime("%Y-%m-%d %H:%M"),
        "recurrence": recurrence,
        "minutes_interval": interval,
    }
