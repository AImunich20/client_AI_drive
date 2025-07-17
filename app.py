from flask import Flask, render_template
from flask_socketio import SocketIO
import cv2
import numpy as np
import base64
import threading
import time
from door import run_terminal
from sleep import AI_sleeep
import mediapipe as mp


app = Flask(__name__)
app.secret_key = "admin"
run_terminal(app)
socketio = SocketIO(app, cors_allowed_origins="*")

clients = {}      # clientId -> frame
last_seen = {}    # clientId -> last timestamp
lock = threading.Lock()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('frame')
def handle_frame(data):
    client_id = data.get('clientId', 'unknown')
    buffer = data.get('buffer', None)
    if not buffer:
        return

    img = cv2.imdecode(np.frombuffer(buffer, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is not None:
        with lock:
            clients[client_id] = img
            last_seen[client_id] = time.time()  # อัปเดตเวลาที่ส่งข้อมูลล่าสุด

import os
from playsound import playsound

# เพิ่มตัวแปรเก็บเวลาที่เริ่มหลับตา
eye_closed_start = {}  # clientId -> timestamp (หรือ None ถ้าไม่หลับตา)

def show_frames():
    mp_face_mesh = mp.solutions.face_mesh
    while True:
        current_time = time.time()
        with lock:
            for client_id in list(clients.keys()):
                # ลบ client ที่ไม่ส่งข้อมูลเกิน 2 วิ
                if current_time - last_seen.get(client_id, 0) > 2:
                    if cv2.getWindowProperty(f"Client: {client_id}", cv2.WND_PROP_VISIBLE) >= 0:
                        cv2.destroyWindow(f"Client: {client_id}")
                    del clients[client_id]
                    del last_seen[client_id]
                    eye_closed_start.pop(client_id, None)
                    continue

                frame = clients[client_id]
                status = AI_sleeep(frame, mp_face_mesh)  # status เช่น {'eye_closed': True, ...}

                # จัดการเวลาเริ่มหลับตา
                if status.get('eye_closed'):
                    if client_id not in eye_closed_start:
                        eye_closed_start[client_id] = current_time  # เริ่มนับเวลา
                    else:
                        elapsed = current_time - eye_closed_start[client_id]
                        # ถ้าเกิน 2 วิ แต่ยังไม่ถึง 3 วิ
                        if 1 <= elapsed < 2:
                            threading.Thread(target=playsound, args=("alert.mp3",), daemon=True).start()
                        # ถ้าเกิน 3 วิ
                        elif elapsed >= 2:
                            # เล่นเสียงเตือนซ้ำ หรือเล่นเสียงที่ดังขึ้น
                            # (ถ้าต้องการเสียงดังขึ้น ให้เตรียมไฟล์เสียงอีกไฟล์ เช่น alert_loud.mp3)
                            threading.Thread(target=playsound, args=("alert_loud.mp3",), daemon=True).start()
                else:
                    # ถ้าไม่หลับตา รีเซ็ตเวลาเริ่มหลับตา
                    eye_closed_start.pop(client_id, None)

                # แสดงข้อความบนภาพตาม status
                y = 50
                for k, v in status.items():
                    if v:
                        text = f"{k.upper()} DETECTED!"
                        cv2.putText(frame, text, (30, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                        y += 40

                socketio.emit('status', {'clientId': client_id, **status})
                cv2.imshow(f"Client: {client_id}", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()


if __name__ == '__main__':
    t = threading.Thread(target=show_frames)
    t.daemon = True
    t.start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
