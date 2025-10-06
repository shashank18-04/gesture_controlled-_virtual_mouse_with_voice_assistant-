# gesture_mouse.py (continuous voice listening, no timeout)
import cv2
import mediapipe as mp
import pyautogui
import math
import threading
import queue
import speech_recognition as sr  # Voice recognition
from enum import IntEnum
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from google.protobuf.json_format import MessageToDict
import screen_brightness_control as sbcontrol
import signal
import sys
import time

pyautogui.FAILSAFE = False
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

# ========================= ENUMS ========================= #
class Gest(IntEnum):
    FIST = 0
    PINKY = 1
    RING = 2
    MID = 4
    LAST3 = 7
    INDEX = 8
    FIRST2 = 12
    LAST4 = 15
    THUMB = 16
    PALM = 31
    V_GEST = 33
    TWO_FINGER_CLOSED = 34
    PINCH_MAJOR = 35
    PINCH_MINOR = 36
    VOLUME_BRIGHTNESS = 37

class HLabel(IntEnum):
    MINOR = 0
    MAJOR = 1

# ========================= HAND RECOGNITION ========================= #
class HandRecog:
    def __init__(self, hand_label):
        self.finger = 0
        self.ori_gesture = Gest.PALM
        self.prev_gesture = Gest.PALM
        self.frame_count = 0
        self.hand_result = None
        self.hand_label = hand_label

    def update_hand_result(self, hand_result):
        self.hand_result = hand_result

    def get_signed_dist(self, point):
        sign = -1
        if self.hand_result.landmark[point[0]].y < self.hand_result.landmark[point[1]].y:
            sign = 1
        dist = (self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x) ** 2
        dist += (self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y) ** 2
        dist = math.sqrt(dist)
        return dist * sign

    def get_dist(self, point):
        dist = (self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x) ** 2
        dist += (self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y) ** 2
        dist = math.sqrt(dist)
        return dist

    def get_dz(self, point):
        return abs(self.hand_result.landmark[point[0]].z - self.hand_result.landmark[point[1]].z)

    def set_finger_state(self):
        if self.hand_result is None:
            return
        points = [[8, 5, 0], [12, 9, 0], [16, 13, 0], [20, 17, 0]]
        self.finger = 0
        self.finger = self.finger | 0
        for idx, point in enumerate(points):
            dist = self.get_signed_dist(point[:2])
            dist2 = self.get_signed_dist(point[1:])
            try:
                ratio = round(dist / dist2, 1)
            except Exception:
                ratio = round(dist / 0.01, 1)
            self.finger = self.finger << 1
            if ratio > 0.5:
                self.finger = self.finger | 1

    def get_gesture(self):
        if self.hand_result is None:
            return Gest.PALM
        current_gesture = Gest.PALM
        if self.finger in [Gest.LAST3, Gest.LAST4] and self.get_dist([8, 4]) < 0.05:
            if self.hand_label == HLabel.MINOR:
                current_gesture = Gest.PINCH_MINOR
            else:
                current_gesture = Gest.PINCH_MAJOR
        elif Gest.FIRST2 == self.finger:
            point = [[8, 12], [5, 9]]
            dist1 = self.get_dist(point[0])
            dist2 = self.get_dist(point[1])
            ratio = dist1 / dist2 if dist2 != 0 else 10
            if ratio > 1.7:
                current_gesture = Gest.V_GEST
            else:
                if self.get_dz([8, 12]) < 0.1:
                    current_gesture = Gest.TWO_FINGER_CLOSED
                else:
                    current_gesture = Gest.MID
        elif (self.finger & 0b1110) == 0b1110 and not (self.finger & 0b0001) and self.get_dist([4, 17]) < 0.05:
            current_gesture = Gest.VOLUME_BRIGHTNESS
        else:
            current_gesture = self.finger

        if current_gesture == self.prev_gesture:
            self.frame_count += 1
        else:
            self.frame_count = 0
        self.prev_gesture = current_gesture
        if self.frame_count > 2:
            self.ori_gesture = current_gesture
        return self.ori_gesture

# ========================= CONTROLLER ========================= #
class Controller:
    tx_old, ty_old = 0, 0
    flag, grabflag, pinchmajorflag, pinchminorflag, volbrightflag = False, False, False, False, False
    pinchstartxcoord, pinchstartycoord, pinchdirectionflag = None, None, None
    prevpinchlv, pinchlv, framecount = 0, 0, 0
    prev_hand = None
    pinch_threshold = 0.3
    startbrightness, startvolume = 0, 0.0
    current_action = ""

    def getpinchylv(hand_result):
        return round((Controller.pinchstartycoord - hand_result.landmark[8].y) * 10, 1)

    def getpinchxlv(hand_result):
        return round((hand_result.landmark[8].x - Controller.pinchstartxcoord) * 10, 1)

    def changesystembrightness():
        change = Controller.pinchlv * 10
        new = Controller.startbrightness + change
        new = max(0, min(100, new))
        try:
            sbcontrol.set_brightness(int(new))
        except Exception as e:
            print(f"[brightness] error: {e}")

    def changesystemvolume():
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            change = Controller.pinchlv / 10.0
            new = Controller.startvolume + change
            new = max(0.0, min(1.0, new))
            volume.SetMasterVolumeLevelScalar(new, None)
        except Exception as e:
            print(f"[volume] error: {e}")

    SCROLL_SPEED = 120

    def scrollVertical():
        pyautogui.scroll(Controller.SCROLL_SPEED if Controller.pinchlv > 0.0 else -Controller.SCROLL_SPEED)

    def scrollHorizontal():
        pyautogui.keyDown('shift')
        pyautogui.keyDown('ctrl')
        pyautogui.scroll(-Controller.SCROLL_SPEED if Controller.pinchlv > 0.0 else Controller.SCROLL_SPEED)
        pyautogui.keyUp('ctrl')
        pyautogui.keyUp('shift')

    def get_position(hand_result):
        point = 9
        pos = [hand_result.landmark[point].x, hand_result.landmark[point].y]
        sx, sy = pyautogui.size()
        x_old, y_old = pyautogui.position()
        x, y = int(pos[0] * sx), int(pos[1] * sy)
        if Controller.prev_hand is None:
            Controller.prev_hand = x, y
        delta_x, delta_y = x - Controller.prev_hand[0], y - Controller.prev_hand[1]
        distsq = delta_x ** 2 + delta_y ** 2
        ratio = 1
        Controller.prev_hand = [x, y]
        if distsq <= 25:
            ratio = 0
        elif distsq <= 900:
            ratio = 0.1 * (distsq ** 0.5)
        else:
            ratio = 2.8
        return (x_old + delta_x * ratio, y_old + delta_y * ratio)

    def pinch_control_init(hand_result):
        Controller.pinchstartxcoord = hand_result.landmark[8].x
        Controller.pinchstartycoord = hand_result.landmark[8].y
        Controller.pinchlv, Controller.prevpinchlv, Controller.framecount = 0, 0, 0
        try:
            Controller.startbrightness = sbcontrol.get_brightness(display=0)[0]
        except Exception:
            Controller.startbrightness = 50
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            Controller.startvolume = volume.GetMasterVolumeLevelScalar()
        except Exception:
            Controller.startvolume = 0.5

    def pinch_control(hand_result, controlHorizontal, controlVertical):
        if Controller.framecount == 3:
            Controller.framecount = 0
            Controller.pinchlv = Controller.prevpinchlv
            if Controller.pinchdirectionflag is True:
                controlHorizontal()
            elif Controller.pinchdirectionflag is False:
                controlVertical()
        lvx, lvy = Controller.getpinchxlv(hand_result), Controller.getpinchylv(hand_result)
        if abs(lvy) > abs(lvx) and abs(lvy) > Controller.pinch_threshold:
            Controller.pinchdirectionflag = False
            if abs(Controller.prevpinchlv - lvy) < Controller.pinch_threshold:
                Controller.framecount += 1
            else:
                Controller.prevpinchlv, Controller.framecount = lvy, 0
        elif abs(lvx) > Controller.pinch_threshold:
            Controller.pinchdirectionflag = True
            if abs(Controller.prevpinchlv - lvx) < Controller.pinch_threshold:
                Controller.framecount += 1
            else:
                Controller.prevpinchlv, Controller.framecount = lvx, 0

    def handle_controls(gesture, hand_result):
        x, y = (None, None)
        if gesture != Gest.PALM:
            x, y = Controller.get_position(hand_result)
        if gesture != Gest.FIST and Controller.grabflag:
            Controller.grabflag, _ = False, pyautogui.mouseUp(button="left")
        if gesture != Gest.PINCH_MAJOR and Controller.pinchmajorflag:
            Controller.pinchmajorflag = False
        if gesture != Gest.PINCH_MINOR and Controller.pinchminorflag:
            Controller.pinchminorflag = False
        if gesture != Gest.VOLUME_BRIGHTNESS and Controller.volbrightflag:
            Controller.volbrightflag = False

        Controller.current_action = ""
        if gesture == Gest.V_GEST:
            Controller.flag, _ = True, pyautogui.moveTo(x, y, duration=0)
            Controller.current_action = "Mouse Control"
        elif gesture == Gest.FIST:
            if not Controller.grabflag:
                Controller.grabflag, _ = True, pyautogui.mouseDown(button="left")
            pyautogui.moveTo(x, y, duration=0)
            Controller.current_action = "Dragging"
        elif gesture == Gest.MID and Controller.flag:
            Controller.flag, _, Controller.current_action = False, pyautogui.click(), "Left Click"
        elif gesture == Gest.INDEX and Controller.flag:
            Controller.flag, _, Controller.current_action = False, pyautogui.click(button='right'), "Right Click"
        elif gesture == Gest.TWO_FINGER_CLOSED and Controller.flag:
            Controller.flag, _, Controller.current_action = False, pyautogui.doubleClick(), "Double Click"
        elif gesture == Gest.PINCH_MINOR:
            if not Controller.pinchminorflag:
                Controller.pinch_control_init(hand_result)
                Controller.pinchminorflag = True
            Controller.pinch_control(hand_result, Controller.scrollHorizontal, Controller.scrollVertical)
            if Controller.pinchdirectionflag is not None:
                Controller.current_action = f"{'Horizontal' if Controller.pinchdirectionflag else 'Vertical'} Scroll"
        elif gesture in [Gest.PINCH_MAJOR, Gest.VOLUME_BRIGHTNESS]:
            flag_attr = 'volbrightflag' if gesture == Gest.VOLUME_BRIGHTNESS else 'pinchmajorflag'
            if not getattr(Controller, flag_attr):
                Controller.pinch_control_init(hand_result)
                setattr(Controller, flag_attr, True)
            Controller.pinch_control(hand_result, Controller.changesystembrightness, Controller.changesystemvolume)
            if Controller.pinchdirectionflag is not None:
                action = "Brightness" if Controller.pinchdirectionflag else "Volume"
                direction = "Increase" if Controller.pinchlv > 0 else "Decrease"
                Controller.current_action = f"{action} {direction}"

# ========================= MIC SELECTION ========================= #
def list_input_microphones():
    out = []
    try:
        mic_list = sr.Microphone.list_microphone_names()
        print("Available microphones:")
        for i, nm in enumerate(mic_list):
            print(f"  {i}: {nm}")
        input_keywords = ['microphone', 'input', 'headset', 'hands-free', 'earbuds', 'mic']
        for i, nm in enumerate(mic_list):
            if any(k in nm.lower() for k in input_keywords):
                out.append((i, nm))
        if not out:
            out = [(i, nm) for i, nm in enumerate(mic_list)]
    except Exception as e:
        print(f"Error fetching mic list: {e}")
    return out

def get_preferred_microphone():
    try:
        mic_list = sr.Microphone.list_microphone_names()
        bluetooth_keywords = ["bluetooth", "headset", "earbuds", "airpods", "hands-free"]
        for i, mic_name in enumerate(mic_list):
            mic_name_lower = mic_name.lower()
            if any(k in mic_name_lower for k in bluetooth_keywords) and "output" not in mic_name_lower:
                print(f"Using Bluetooth mic: {mic_name} (index {i})")
                return i
        input_candidates = list_input_microphones()
        if input_candidates:
            print(f"Falling back to: {input_candidates[0][1]} (index {input_candidates[0][0]})")
            return input_candidates[0][0]
        return None
    except Exception as e:
        print(f"Error fetching mic list: {e}")
        return None

# ========================= GESTURE + VOICE CONTROLLER ========================= #
class GestureController:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.dom_hand = True
        self.image_queue = queue.Queue(maxsize=1)
        self.stop_event = threading.Event()
        self.voice_recognizer = sr.Recognizer()
        self.voice_recognizer.pause_threshold = 0.5
        self.voice_recognizer.dynamic_energy_threshold = True
        self.mic_index = get_preferred_microphone()

    def _classify_hands(self, results):
        left, right = None, None
        try:
            handedness = MessageToDict(results.multi_handedness[0])
            if handedness['classification'][0]['label'] == 'Right':
                right = results.multi_hand_landmarks[0]
            else:
                left = results.multi_hand_landmarks[0]
        except Exception:
            pass
        try:
            handedness = MessageToDict(results.multi_handedness[1])
            if handedness['classification'][0]['label'] == 'Right':
                right = results.multi_hand_landmarks[1]
            else:
                left = results.multi_hand_landmarks[1]
        except Exception:
            pass
        return (right, left) if self.dom_hand else (left, right)

    def _run_gesture_processing(self):
        handmajor = HandRecog(HLabel.MAJOR)
        handminor = HandRecog(HLabel.MINOR)
        with mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
            while not self.stop_event.is_set():
                success, image = self.cap.read()
                if not success:
                    continue
                image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = hands.process(image)
                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                if results.multi_hand_landmarks:
                    hr_major, hr_minor = self._classify_hands(results)
                    handmajor.update_hand_result(hr_major)
                    handminor.update_hand_result(hr_minor)
                    handmajor.set_finger_state()
                    handminor.set_finger_state()
                    gest_name = handminor.get_gesture()
                    if gest_name in [Gest.PINCH_MINOR, Gest.VOLUME_BRIGHTNESS] and handminor.hand_result:
                        Controller.handle_controls(gest_name, handminor.hand_result)
                    elif handmajor.hand_result:
                        gest_name = handmajor.get_gesture()
                        Controller.handle_controls(gest_name, handmajor.hand_result)
                    for hand_landmarks in results.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                else:
                    Controller.prev_hand, Controller.current_action = None, ""
                cv2.putText(image, Controller.current_action, (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, cv2.LINE_AA)
                if not self.image_queue.full():
                    self.image_queue.put(image)

    def _run_voice_recognition(self):
        mic = None
        try:
            mic = sr.Microphone(device_index=self.mic_index) if self.mic_index is not None else sr.Microphone()
            with mic as source:
                print(f"[voice] Calibrating on mic index {self.mic_index}")
                self.voice_recognizer.adjust_for_ambient_noise(source, duration=1.0)
        except Exception as e:
            print(f"[voice] Could not open mic: {e}")
            return

        def callback(recognizer, audio):
            try:
                cmd = recognizer.recognize_google(audio).lower()
                print(f"[voice] heard: {cmd}")
                if "stop gesture" in cmd:
                    print("Stopping gesture system (via voice)...")
                    self.stop()
                elif "click" in cmd:
                    pyautogui.click()
                elif "right click" in cmd:
                    pyautogui.click(button="right")
                elif "double click" in cmd:
                    pyautogui.doubleClick()
                elif "scroll up" in cmd:
                    pyautogui.scroll(300)
                elif "scroll down" in cmd:
                    pyautogui.scroll(-300)
            except sr.UnknownValueError:
                pass
            except Exception as e:
                print(f"[voice callback error]: {e}")

        try:
            mic = sr.Microphone(device_index=self.mic_index)
            self.voice_recognizer.listen_in_background(mic, callback)
            while not self.stop_event.is_set():
                time.sleep(0.1)
        except Exception as e:
            print(f"[voice recognition error]: {e}")

    def run(self):
        threading.Thread(target=self._run_gesture_processing, daemon=True).start()
        threading.Thread(target=self._run_voice_recognition, daemon=True).start()
        while not self.stop_event.is_set():
            try:
                image = self.image_queue.get(timeout=0.1)
                cv2.imshow("Gesture Control", image)
                if cv2.waitKey(5) & 0xFF == 27:
                    self.stop()
                    break
            except queue.Empty:
                pass
        self.cap.release()
        cv2.destroyAllWindows()

    def stop(self):
        self.stop_event.set()

# ========================= MAIN ========================= #
def main():
    gc = GestureController()
    def signal_handler(sig, frame):
        print("Ctrl+C received, stopping...")
        gc.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    gc.run()

if __name__ == "__main__":
    main()
