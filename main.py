# main.py

import cv2
import queue
import threading
import signal
import sys
from gesture_engine import GestureEngine
from voice_engine import VoiceEngine

def main():
    # Create shared resources for threads
    stop_event = threading.Event()
    image_queue = queue.Queue(maxsize=1)

    # --- Signal Handler for Ctrl+C ---
    def signal_handler(sig, frame):
        print("\nCtrl+C received, stopping all processes...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)

    # --- Initialize Engines ---
    print("Initializing Gesture Engine...")
    gesture_engine = GestureEngine(stop_event, image_queue)
    
    print("Initializing Voice Engine...")
    voice_engine = VoiceEngine(stop_event)

    # --- Start Threads ---
    gesture_thread = threading.Thread(target=gesture_engine.run, daemon=True)
    voice_thread = threading.Thread(target=voice_engine.run, daemon=True)
    
    print("Starting threads...")
    gesture_thread.start()
    voice_thread.start()

    # --- Main Loop (UI) ---
    print("Application started. Press 'Esc' in the gesture window or Ctrl+C to exit.")
    while not stop_event.is_set():
        try:
            # Get the latest frame from the gesture engine to display
            image = image_queue.get(timeout=0.1)
            cv2.imshow("Smooth Gesture Mouse Controller", image)

            # Check for 'Esc' key to exit
            if cv2.waitKey(5) & 0xFF == 27:
                print("'Esc' key pressed, stopping...")
                stop_event.set()
                break
        except queue.Empty:
            # This is expected if the gesture engine is slower than the UI loop
            continue
    
    # --- Cleanup ---
    print("Cleaning up resources...")
    # Threads will stop automatically because they are daemons
    cv2.destroyAllWindows()
    sys.exit(0)

if __name__ == "__main__":
    main()