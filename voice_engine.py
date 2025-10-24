# voice_engine.py

import speech_recognition as sr
import threading
import time
import pyautogui
import subprocess
import os

# ========================= MIC SELECTION ========================= #
def list_input_microphones():
    mic_list = sr.Microphone.list_microphone_names()
    return list(enumerate(mic_list))

def get_preferred_microphone_index():
    try:
        mic_list = sr.Microphone.list_microphone_names()
        bluetooth_keywords = ["bluetooth", "headset", "earbuds", "airpods", "hands-free"]
        for i, mic_name in enumerate(mic_list):
            if any(k in mic_name.lower() for k in bluetooth_keywords):
                print(f"[voice] Using preferred mic: {mic_name} (index {i})")
                return i
        if mic_list:
             print(f"[voice] Falling back to default mic: {mic_list[0]} (index 0)")
             return 0
        return None
    except Exception as e:
        print(f"[voice] Error fetching microphone list: {e}")
        return None

# ========================= VOICE ENGINE ========================= #
class VoiceEngine:
    def __init__(self, stop_event):
        self.stop_event = stop_event
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8
        self.recognizer.dynamic_energy_threshold = True
        self.mic_index = get_preferred_microphone_index()
        
        # --- Define file/app paths ---
        self.user_home_dir = os.path.expanduser("~")
        
        # --- (CHANGED) Renamed for clarity ---
        self.documents_path = os.path.join(self.user_home_dir, "Desktop")
        
        # --- (NEW) This is the "memory" for the current search folder ---
        self.current_search_path = self.documents_path
        
        desktop_path = os.path.join(self.user_home_dir, "Desktop")
        public_desktop_path = os.path.join(os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop")
        self.app_search_paths = [desktop_path, public_desktop_path]

    # --- App/Folder Helper Functions ---
    def _find_and_launch_app(self, app_name):
        if not app_name: return
        print(f"[voice] Searching for app: '{app_name}' on Desktops...")
        for path in self.app_search_paths:
            try:
                for file in os.listdir(path):
                    file_lower = file.lower()
                    if app_name in file_lower and (file_lower.endswith(".lnk") or file_lower.endswith(".exe")):
                        full_path = os.path.join(path, file)
                        print(f"[voice] Found and launching: {full_path}")
                        os.startfile(full_path)
                        return
            except Exception as e:
                print(f"[voice] Error searching path {path}: {e}")
        print(f"[voice] Sorry, I couldn't find an app named '{app_name}' on your desktop.")

    # --- (CHANGED) This function now returns the path of the folder it finds ---
    def _find_and_open_folder(self, folder_name):
        """Helper function to search for and open a folder. Returns the path if found."""
        if not folder_name:
            print("[voice] No folder name heard.")
            return None # Return None if no name
            
        print(f"[voice] Searching for folder: '{folder_name}'...")
        # Search Desktop, Public Desktop, and the *current* search path
        search_paths = self.app_search_paths + [self.current_search_path, self.documents_path]
        search_words = folder_name.lower().split()
        
        for path in search_paths:
            try:
                for item in os.listdir(path):
                    item_lower = item.lower()
                    item_full_path = os.path.join(path, item)
                    
                    if os.path.isdir(item_full_path) and all(word in item_lower for word in search_words):
                        print(f"[voice] Found and opening folder: {item_full_path}")
                        os.startfile(item_full_path)
                        return item_full_path # Return the path of the found folder
            except Exception as e:
                print(f"[voice] Error searching path {path}: {e}")
        
        print(f"[voice] Sorry, I couldn't find a folder named '{folder_name}'.")
        return None # Return None if not found

    # --- Main Voice Recognition Loop ---
    def run(self):
        if self.mic_index is None:
            print("[voice] No microphone found. Voice engine cannot start.")
            return

        try:
            mic = sr.Microphone(device_index=self.mic_index)
            with mic as source:
                print(f"[voice] Calibrating microphone... Please wait.")
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
                print(f"[voice] Microphone calibrated. Ready. (Default folder: {self.current_search_path})")
        except Exception as e:
            print(f"[voice] Could not open microphone: {e}")
            return

        # --- Main Callback Function ---
        def callback(recognizer, audio):
            try:
                cmd = recognizer.recognize_google(audio).lower()
                print(f"[voice] Heard: '{cmd}'")
                
                # --- System & Mouse ---
                if "stop gesture" in cmd or "stop program" in cmd:
                    print("[voice] Stop command received. Shutting down.")
                    self.stop_event.set()
                elif "click" in cmd or "left click" in cmd:
                    pyautogui.click()
                elif "right click" in cmd:
                    pyautogui.click(button="right")
                elif "double click" in cmd:
                    pyautogui.doubleClick()
                elif "scroll up" in cmd:
                    pyautogui.scroll(300)
                elif "scroll down" in cmd:
                    pyautogui.scroll(-300)
                elif "close this" in cmd or "close window" in cmd:
                    print("[voice] Closing active window (Alt+F4)...")
                    pyautogui.hotkey('alt', 'f4')
                elif "minimize" in cmd or "show desktop" in cmd:
                    print("[voice] Minimizing all windows...")
                    pyautogui.hotkey('win', 'm')

                # --- File/App/Folder Opening ---
                elif "open chrome" in cmd:
                    print("[voice] Opening Google Chrome...")
                    subprocess.run(['start', 'chrome'], shell=True)
                
                # --- (CHANGED) Open File ---
                elif "open file" in cmd:
                    filename = cmd.replace("open file", "").strip()
                    if not filename: return

                    # --- This now uses self.current_search_path "memory" ---
                    print(f"[voice] Searching for file: '{filename}' in '{self.current_search_path}'")
                    try:
                        found = False
                        search_words = filename.lower().split()
                        
                        for file in os.listdir(self.current_search_path): # Uses the new path
                            file_lower = file.lower()
                            full_path = os.path.join(self.current_search_path, file) # Uses the new path
                            
                            if os.path.isfile(full_path) and all(word in file_lower for word in search_words):
                                print(f"[voice] Found and opening: {full_path}")
                                os.startfile(full_path) 
                                found = True
                                break 
                        if not found:
                             print(f"[voice] Sorry, I couldn't find a file named '{filename}'.")
                    except Exception as e:
                        print(f"[voice] Error opening file: {e}")

                # --- (CHANGED) Open Folder ---
                elif "open folder" in cmd:
                    folder_name = cmd.replace("open folder", "").strip()
                    found_path = self._find_and_open_folder(folder_name)
                    
                    # --- This is the new "memory" part ---
                    if found_path:
                        self.current_search_path = found_path
                        print(f"[voice] New search folder set to: {self.current_search_path}")
                
                # --- (NEW) Command to reset the search path ---
                elif "go to documents" in cmd or "reset folder" in cmd:
                    print(f"[voice] Resetting search folder to Documents.")
                    self.current_search_path = self.documents_path
                    os.startfile(self.documents_path) # Open Documents to confirm

                elif "launch this pc" in cmd:
                    print("[voice] Opening This PC...")
                    subprocess.run(['explorer.exe', 'shell:MyComputerFolder'], shell=True)
                elif "launch" in cmd:
                    app_name = cmd.replace("launch", "").strip()
                    self._find_and_launch_app(app_name)

            except sr.UnknownValueError:
                pass 
            except Exception as e:
                print(f"[voice] Callback error: {e}")

        # Start listening in the background
        stop_listening = self.recognizer.listen_in_background(mic, callback)

        while not self.stop_event.is_set():
            time.sleep(0.1)
        
        stop_listening(wait_for_stop=False)
        print("[voice] Voice engine stopped.")