import cv2
import torch 
from tracker import *
import numpy as np

import mysql.connector
from datetime import datetime
import sys  
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# ฟังก์ชันเชื่อมต่อฐานข้อมูล
def connect_to_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="graduate49"
    )

# ฟังก์ชันดึงข้อมูล total_count และ current_count
def get_total_and_current_count():
    try:
        db = connect_to_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT total_count, current_count FROM ru_queue ORDER BY queue_date DESC LIMIT 1")
        result = cursor.fetchone()
        cursor.close()
        db.close()
        return (result['total_count'], result['current_count']) if result else (0, 0)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return 0, 0

# ฟังก์ชันอัปเดต current_count
def update_current_count(new_current_count):
    try:
        db = connect_to_db()
        cursor = db.cursor()
        cursor.execute("UPDATE ru_queue SET current_count = %s WHERE id = 1", (new_current_count,))
        db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Error updating current count: {e}")

# โหลดโมเดล YOLOv5
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# อ่านวิดีโอ
cap = cv2.VideoCapture('http://202.41.160.68:1935/live/ru999/playlist.m3u8')

cv2.namedWindow('FRAME')

# อินสแตนซ์ตัวติดตาม
tracker = Tracker()

# พื้นที่โพลิกอนที่ต้องการตรวจจับ
area_1 = [(748, 476), (769, 251), (787, 252), (763, 472)]  

# เก็บข้อมูลการติดตามวัตถุ
counted_ids = set()
tracked_objects = {}  # ใช้เก็บตำแหน่งก่อนหน้าของแต่ละ ID

# ดึงข้อมูลจากฐานข้อมูล
total_count, current_count = get_total_and_current_count()

if total_count == 0:
    current_count = total_count

if current_count == 0:
    print("Current count is 0. Exiting the program.")
    sys.exit()

# ตัวแปรควบคุมการนับ
is_counting = False

# เริ่มตรวจจับ
while True:
    total_count, current_count = get_total_and_current_count()
    
    if current_count == 0:
        print("Current count is 0. Exiting the program.")
        sys.exit()
    
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (1020, 500))
    cv2.polylines(frame, [np.array(area_1, np.int32)], True, (0, 255, 0), 3)

    results = model(frame)
    detections = []
    for _, row in results.pandas().xyxy[0].iterrows():
        x1, y1, x2, y2 = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
        label = row['name']
        if label == 'person':
            detections.append([x1, y1, x2, y2])

    boxes_ids = tracker.update(detections)
    for box_id in boxes_ids:
        x, y, w, h, obj_id = box_id
        cx, cy = (x + w) // 2, (y + h) // 2  # หาจุดกึ่งกลางของวัตถุ

        # วาดกรอบ
        cv2.rectangle(frame, (x, y), (w, h), (255, 0, 255), 2)
        cv2.putText(frame, str(obj_id), (x, y - 10), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)

        # กำหนดระยะที่ต้องการให้จุดเลื่อนลงจากกึ่งกลาง
        offset = 50  # ระยะห่างที่ต้องการเลื่อนลง (ปรับได้ตามต้องการ)
        cy_adjusted = cy + offset  # ปรับตำแหน่งลง
        cv2.circle(frame, (cx, cy_adjusted), 5, (0, 255, 255), -1)
        # ติดตามทิศทางการเคลื่อนที่
        if obj_id in tracked_objects:
            prev_cx, _ = tracked_objects[obj_id]
            direction = cx - prev_cx  # หาค่าการเปลี่ยนแปลงตำแหน่งแนวนอน

            # ตรวจสอบว่าคนเดินจากซ้ายไปขวาและยังไม่ถูกนับ
            if direction > 0 and obj_id not in counted_ids:
                result = cv2.pointPolygonTest(np.array(area_1, np.int32), (cx, cy), False)
                if result > 0:
                    counted_ids.add(obj_id)
                    current_count -= 1
                    update_current_count(current_count)

        # อัปเดตตำแหน่งล่าสุดของวัตถุ
        tracked_objects[obj_id] = (cx, cy)

    cv2.putText(frame, f"Total: {total_count}, Remaining: {current_count}", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow('FRAME', frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('s'):
        is_counting = False
        print("Counting paused.")
    elif key == ord('r'):
        is_counting = True
        print("Counting resumed.")
    elif key == 27:  # ESC key
        break
             
cap.release()
cv2.destroyAllWindows()
