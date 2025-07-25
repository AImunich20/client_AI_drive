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
import os
from playsound import playsound

app = Flask(__name__)
app.secret_key = "admin"
run_terminal(app)
socketio = SocketIO(app, cors_allowed_origins="*")

clients = {}
last_seen = {}
eye_closed_start = {}
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
    print(f"[RECEIVED FRAME] From: {client_id}")

    img = cv2.imdecode(np.frombuffer(buffer, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is not None:
        with lock:
            clients[client_id] = img
            last_seen[client_id] = time.time()


@socketio.on('connect')
def handle_connect():
    print("[CONNECT] Client connected")


@socketio.on('disconnect')
def handle_disconnect():
    print("[DISCONNECT] Client disconnected")


def show_frames():
    print("[DEBUG] show_frames() started")
    mp_face_mesh = mp.solutions.face_mesh
    headless = not os.environ.get("DISPLAY")

    while True:
        current_time = time.time()
        with lock:
            for client_id in list(clients.keys()):
                if current_time - last_seen.get(client_id, 0) > 2:
                    print(f"[TIMEOUT] Removing client {client_id}")
                    # ❌ ห้ามใช้ getWindowProperty ถ้า headless
                    # ✅ ลบออกตรง ๆ
                    del clients[client_id]
                    del last_seen[client_id]
                    eye_closed_start.pop(client_id, None)
                    continue

                frame = clients[client_id]
                status = AI_sleeep(frame, mp_face_mesh)

                if status.get('eye_closed'):
                    if client_id not in eye_closed_start:
                        eye_closed_start[client_id] = current_time
                    else:
                        elapsed = current_time - eye_closed_start[client_id]
                        if 1 <= elapsed < 2:
                            threading.Thread(target=playsound, args=("alert.mp3",), daemon=True).start()
                        elif elapsed >= 2:
                            threading.Thread(target=playsound, args=("alert_loud.mp3",), daemon=True).start()
                else:
                    eye_closed_start.pop(client_id, None)

                # ส่ง status กลับไป client
                socketio.emit('status', {'clientId': client_id, **status})

                # ✅ แสดงภาพเฉพาะถ้าไม่ headless
                if not headless:
                    y = 50
                    for k, v in status.items():
                        if v:
                            text = f"{k.upper()} DETECTED!"
                            cv2.putText(frame, text, (30, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                            y += 40
                    cv2.imshow(f"Client: {client_id}", frame)

        if not headless and cv2.waitKey(1) & 0xFF == ord('q'):
            break

    if not headless:
        cv2.destroyAllWindows()

# if __name__ == '__main__':
# Always start show_frames regardless of __name__
t = threading.Thread(target=show_frames)
t.daemon = True
t.start()

# Run Flask
socketio.run(app, host='0.0.0.0', port=2000, debug=True, allow_unsafe_werkzeug=True)

