import streamlit as st
import cv2
import numpy as np
import time
from ultralytics import YOLO
import pygame
import pandas as pd
from datetime import datetime
from threading import Thread
import os
import csv
import asyncio

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())


import sys
import types

# Prevent Streamlit from accessing torch.classes as a module
import torch
if not isinstance(torch.classes, types.ModuleType):
    sys.modules['torch.classes'] = types.ModuleType('torch.classes')


pygame.mixer.init()  # use pygame to play sound files

# runs the alarm using pygame in a separate thread, to allow parallel processing
alarm_playing = False
alarm_thread = None
stop_alarm_thread = False

# if the state changes into drowsy and confidence threshold is 0.75-0.90 for >= 2 mins, alarm will go on
# then will log to report column, if awake log again to the report column
detection_log = []
current_state = "awake"
drowsy_start_time = None
drowsy_duration = None
log = False
weekly = False
THRESHOLD_DURATION = 5

# detect every 3 seconds, otherwise the model will detect blinking as drowsy
last_detection_time = 0
DETECTION_INTERVAL = 3

if 'hour' not in st.session_state or 'weekly' not in st.session_state:
    st.session_state.hour = [] 
    st.session_state.weekly = []

def start_alarm(alarm_path):  # to play alarm
    global alarm_playing, stop_alarm_thread
    alarm_playing = True

    try:
        pygame.mixer.music.load(alarm_path)
        pygame.mixer.music.play(-1)  # -1 meaning indefinitely

        while pygame.mixer.music.get_busy() and not stop_alarm_thread:
            pygame.time.Clock().tick(10)
    except Exception as e:
        st.error(f"Error playing alarm: {e}")
    finally:
        alarm_playing = False


def stop_alarm():  # to stop alarm
    global stop_alarm_thread
    stop_alarm_thread = True
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()


def log_change_state(new_state, confidence):  # to input the state changes to the report column
    global current_state, drowsy_start_time, drowsy_duration, log
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if new_state == "drowsy" and current_state == "awake" and 0.75 <= confidence <= 1.00: # from awake to drowsy
        drowsy_start_time = datetime.now()
        drowsy_duration = 0
        log = True
    
    elif new_state == "drowsy" and current_state == "drowsy" and drowsy_start_time is not None and log == True: # if already drowsy, check whether the threshold is reached
        drowsy_duration = (datetime.now() - drowsy_start_time).total_seconds()
        
        if drowsy_duration >= THRESHOLD_DURATION:
            detection_log.append({
                "Timestamp": timestamp,
                "Event": "You slept!",
                "Alarm Status": "ON"
            })
            st.session_state.hour.append([confidence, drowsy_start_time.minute])
            st.session_state.weekly.append([confidence, drowsy_start_time.strftime("%A"), drowsy_start_time.hour, drowsy_start_time.strftime("%W")]) 
            log = False

    elif new_state == "awake" and current_state == "drowsy" and drowsy_duration >= THRESHOLD_DURATION: # from drowsy to awake
        detection_log.append({
            "Timestamp": timestamp,
            "Event": "You woke up!",
            "Alarm Status": "OFF"
        })

        drowsy_start_time = None
        drowsy_duration = None
    
    if new_state != current_state:
        current_state = new_state


def handle_alarm(state, confidence, alarm_path):  # state and alarm logic, play alarm in a separate thread
    global alarm_playing, alarm_thread, stop_alarm_thread, drowsy_start_time, drowsy_duration, detection_log, current_state

    if state == "drowsy":

        if drowsy_start_time is None:
            drowsy_start_time = datetime.now()
            drowsy_duration = 0
        else:
            drowsy_duration = (datetime.now() - drowsy_start_time).total_seconds()

        if drowsy_duration >= THRESHOLD_DURATION and 0.75 <= confidence <= 1.00: 
            st.session_state.hour.append([confidence, drowsy_duration/60]) # pass to homepage
            
            if not alarm_playing:
                if alarm_thread and alarm_thread.is_alive():
                    stop_alarm()
                    alarm_thread.join(timeout=1)
                stop_alarm_thread = False

                alarm_thread = Thread(target=start_alarm, args=(alarm_path,))
                alarm_thread.daemon = True
                alarm_thread.start()
    else:
        if alarm_playing:
            stop_alarm()
        
        if current_state == "drowsy":
            drowsy_start_time = None
            drowsy_duration = None


def main():  # display the streamlit frontend and detection logic
    st.set_page_config(page_title="Study Mode", layout="wide")

    st.title("Study Mode")

    alarm_path = os.path.join(os.path.dirname(__file__), 'alarm.wav')
    model_path = os.path.join(os.path.dirname(__file__), 'best.pt')

    with st.sidebar: 
        st.header("Study Mode")

        start_detection = st.checkbox("Start Detection", value=False)

        # st.markdown("Detection Threshold: 0.75-1.00 for 2 minutes")
        # st.markdown("Detection Rate: Every 3 seconds")

        if st.button("Clear report logs"):
            global detection_log, drowsy_start_time, current_state
            detection_log.clear()
            st.session_state.hour.clear()
            st.session_state.weekly.clear()
            drowsy_start_time = None
            current_state = "awake"  

    col1, col2 = st.columns([3, 2])  

    with col1:
        st.header("Camera Display")
        video_placeholder = st.empty()
        status_indicator = st.empty()
        state_indicator = st.empty()

    with col2:
        st.header("Detection Report")
        report_placeholder = st.empty()

    if start_detection:
        global last_detection_time, drowsy_duration, weekly
        weekly = True
        try:
            model = YOLO(model_path)

            cap = cv2.VideoCapture(0)

            if not cap.isOpened():
                st.error("Error: could not open webcam")
                return
            
            status_text = "Status: Initializing..."
            status_color = (255, 255, 255)
            detected_class = None
            
            while start_detection:
                success, frame = cap.read()

                if not success:
                    st.error("Error: Failed to capture video from webcam")
                    break
            
                current_time = time.time()

                max_confidence = 0.0

                perform_detection = False
                if current_time - last_detection_time >= DETECTION_INTERVAL:
                    perform_detection = True
                    last_detection_time = current_time
                
                if perform_detection:
                    results = model(frame)

                    if results and len(results) > 0:
                        for r in results:
                            boxes = r.boxes
                            if len(boxes) > 0:
                                for box in boxes:
                                    conf = float(box.conf[0])
                                    cls = int(box.cls[0])
                                    cls_name = model.names[cls]

                                    if conf > max_confidence:
                                        max_confidence = conf
                                        detected_class = cls_name

                                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                                    if cls_name == "awake":
                                        color = (0, 255, 0)  # green for awake
                                    elif cls_name == "drowsy":
                                        color = (0, 0, 255)  # red for drowsy
                                    else:
                                        color = (0, 165, 255)  # orange for yawn
                                    
                                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                                    label = f"{cls_name} {conf:.2f}"
                                    cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

                    if detected_class:
                        log_change_state(detected_class, max_confidence)
                        handle_alarm(detected_class, max_confidence, alarm_path)

                        if detected_class == "awake":
                            status_color = (0, 255, 0)
                            status_text = "Status: Awake"
                            state_indicator.info("Current state: Awake")
                            status_indicator.empty()  
                        elif detected_class == "drowsy":
                            status_color = (0, 0, 255)
                            status_text = "Status: Drowsy"
                            state_indicator.warning("Current state: Drowsy")
                            # Show progress toward threshold
                            if drowsy_duration is not None:
                                # remaining = max(0, THRESHOLD_DURATION - drowsy_duration)
                                progress_pct = min(1.0, drowsy_duration / THRESHOLD_DURATION)
                                status_indicator.progress(progress_pct, 
                                                        f"Drowsy for: {int(drowsy_duration)}s / Threshold: {THRESHOLD_DURATION}s") # progress bar
                        
                                if drowsy_duration >= THRESHOLD_DURATION:
                                    state_indicator.error("ALERT: Drowsy threshold reached!")
                        elif detected_class == "yawn":
                            status_color = (0, 165, 255)
                            status_text = "Status: Yawning"
                            state_indicator.info("Current state: Yawning")

                cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # convert frame from BGR (what opencv uses) to RGB to display in streamlit
                video_placeholder.image(rgb_frame, channels="RGB", use_container_width=True)

                if detection_log:
                    df = pd.DataFrame(detection_log)
                    report_placeholder.dataframe(df, use_container_width=True)
                else:
                    report_placeholder.info("No drowsiness detected yet")
            
            cap.release()
            stop_alarm()
        
        except Exception as e:
            st.error(f"An error has occurred: {e}")
            import traceback
            st.error(traceback.format_exc())
    
    elif start_detection == False and weekly == False:
        video_placeholder.image(np.zeros((480, 640, 3), dtype=np.uint8), channels="RGB", use_container_width=True)
        status_indicator.empty()
        state_indicator.empty()
        report_placeholder.info("Start detection to see report.")
    
    elif start_detection == False and weekly == True:
        video_placeholder.image(np.zeros((480, 640, 3), dtype=np.uint8), channels="RGB", use_container_width=True)
        status_indicator.empty()
        state_indicator.empty()
        report_placeholder.dataframe(df, use_container_width=True)
        stop_alarm() 

        weekly_path = "C:/Users/ThinkPad/Documents/Coding/Uni Project/drowsiness-detection/weekly_data.csv"
        with open(weekly_path, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Drowsiness", "Day", "Hour", "Week"])  # header
            for entry in st.session_state.weekly:
                writer.writerow(entry)



        weekly = False

if __name__ == "__main__":
    main()