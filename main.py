# main.py
import threading
import time
from assistant import speak
from reminder import start_reminders

def main():
    print("Personal Task Assistant — background mode.")
    print("• This will run reminders (voice + desktop notifications).")
    print("• You can open the UI anytime with:  streamlit run ui.py")
    speak("Personal Task Assistant started. Reminders are active.")

    # Start the scheduler in a background daemon thread
    t = threading.Thread(target=start_reminders, daemon=True)
    t.start()

    try:
        # Keep main process alive; CTRL+C to exit.
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nShutting down. Bye!")
        speak("Shutting down. Goodbye.")

if __name__ == "__main__":
    main()
