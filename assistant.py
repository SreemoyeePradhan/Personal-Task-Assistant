# assistant.py
import json
import os
from datetime import datetime

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
        engine.setProperty('voice', voices[1].id)  # 0 = male, 1 = female (usually)
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
        # duration=5 shows toast for ~5s; threaded prevents blocking.
        toaster.show_toast(title, message, duration=5, threaded=True)
        return
    except Exception:
        pass

    # Fallback (cross-platform)
    try:
        from plyer import notification
        notification.notify(title=title, message=message, timeout=5)
    except Exception as e:
        print(f"[notify] {title}: {message} (Notification fallback, {e})")

# ---------- Task helpers ----------
def validate_due_str(due_str: str) -> bool:
    try:
        datetime.strptime(due_str, "%Y-%m-%d %H:%M")
        return True
    except ValueError:
        return False

def add_task(description: str, due_str: str):
    if not description.strip():
        raise ValueError("Task description cannot be empty.")
    if not validate_due_str(due_str):
        raise ValueError("Invalid date/time format. Use YYYY-MM-DD HH:MM")

    tasks = load_tasks()
    tasks.append({
        "description": description.strip(),
        "due": due_str,
        "done": False
    })
    save_tasks(tasks)
    speak(f"Task added: {description} at {due_str}")

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
        tasks[index]["done"] = done
        save_tasks(tasks)
        status = "completed" if done else "reopened"
        speak(f"Task {status}: {tasks[index].get('description','')}")
    else:
        raise IndexError("Task index out of range.")
