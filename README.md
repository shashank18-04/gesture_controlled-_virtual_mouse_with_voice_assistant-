# Gesture Controlled virtual mouse with voice assistance 

This project allows you to control your Windows computer using both hand gestures and voice commands simultaneously. It uses your webcam to track hand movements for precise mouse control and your microphone for a smart, context-aware voice assistant.

![Project Demo GIF](demo.gif)

*(**Note**: You should record a short GIF or video of the project in action, name it `demo.gif`, and place it in your repository!)*

## ✨ Features

### Gesture Control (via Webcam)
* **Mouse Movement**: Move your hand in a "V" (victory) gesture to move the cursor.
* **Left Click**: Raise your middle finger.
* **Right Click**: Raise your index finger.
* **Double Click**: Raise your index and middle fingers, then close them.
* **Click and Drag**: Make a fist to grab and drag.
* **Scroll**: Use a pinch gesture (thumb and index) and move up/down or left/right.
* **Volume & Brightness Control**: Use a pinch gesture with your *other* hand to control system volume and brightness.

### Voice Assistant (via Microphone)
* **Mouse Commands**: "click", "right click", "double click", "scroll up", "scroll down".
* **Window Management**: "close this" (Alt+F4), "minimize all" (Win+M).
* **Application Launching**: "launch chrome", "launch this pc", "launch whatsapp" (searches desktop for shortcuts).
* **File & Folder Navigation**:
    * "open folder [folder name]": Searches your Desktop/Documents for a folder and opens it.
    * "open file [file name]": Searches *within the last opened folder* for a file.
    * "go to documents": Resets the file search path back to your Documents folder.

## 💻 Tech Stack
* **Python 3**
* **OpenCV**: For capturing webcam feed.
* **MediaPipe**: For real-time hand and gesture detection.
* **PyAutoGUI**: For controlling the mouse and keyboard.
* **SpeechRecognition**: For processing voice commands (uses Google Web Speech API).
* **Pycaw**: For (gesture-based) system audio control.
* **screen-brightness-control**: For (gesture-based) screen brightness control.

## 🚀 Setup and Installation

### 1. Prerequisites
* Python 3.8 or newer.
* A webcam.
* A microphone.

### 2. Clone the Repository
```git clone [https://github.com/your-username/your-project-name.git](https://github.com/your-username/your-project-name.git)
cd your-project-name.
```
### 3. Create a Virtual Environment (Recommended)
# On Windows
```
python -m venv venv
venv\Scripts\activate
```

### 4. Install Dependencies
Create a file named requirements.txt in the project folder and paste the following lines into it:

opencv-python
mediapipe
pyautogui
SpeechRecognition
pycaw
screen-brightness-control
pyaudio
comtypes
protobuf
Now, run the following command in your terminal to install all of them:
```bash
pip install -r requirements.txt
```
## 🏃 How to Run

With your virtual environment active and dependencies installed, simply run:

```bash
python main.py
```
### 🧠 What Happens

- The **gesture engine** and **voice engine** start simultaneously.  
- A **camera window** opens showing live **hand tracking**.  
- The **terminal** displays voice command logs.  

To **stop the program**:
- Press **Esc** while the camera window is active, or  
- Press **Ctrl + C** in the terminal.

---

## 🎮 Available Commands

### ✋ Gesture Commands

| Gesture | Action |
|----------|--------|
| ✌️ "V" (Index & Middle) | Move Mouse Cursor |
| 🖕 Middle Finger Up (from Fist) | Left Click |
| ☝️ Index Finger Up (from Fist) | Right Click |
| ✌️ then Close | Double Click |
| ✊ Fist | Click and Drag |
| 🤏 Pinch (Thumb + Index) | Scroll Vertically / Horizontally |
| 🤲 Pinch with Other Hand | Control System Volume / Brightness |

---

### 🎤 Voice Commands

| Command Phrase | Action |
|----------------|--------|
| “click” / “left click” | Performs a left click |
| “right click” | Performs a right click |
| “double click” | Performs a double click |
| “scroll up” / “scroll down” | Scrolls the page |
| “close this” / “close window” | Closes the active window (Alt+F4) |
| “minimize all” / “show desktop” | Minimizes all windows (Win+M) |
| “launch [app name]” | Searches Desktop for and opens an app (e.g., “launch chrome”) |
| “launch this pc” | Opens *This PC* window |
| “open folder [folder name]” | Opens a folder from Desktop/Documents |
| “open file [file name]” | Opens a file inside the current folder |
| “go to documents” | Resets the search path to Documents |
| “stop program” | Shuts down the application |

---

