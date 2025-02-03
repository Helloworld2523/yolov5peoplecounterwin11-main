import cv2
import torch
from tracker import *
import numpy as np

import mysql.connector
from datetime import datetime


# ฟังก์ชันสำหรับการเชื่อมต่อฐานข้อมูล
def connect_to_db():
    return mysql.connector.connect(
        host="localhost",  # แก้ไขให้ตรงกับเซิร์ฟเวอร์ของคุณ
        user="root",       # ชื่อผู้ใช้ MySQL
        password="password",  # รหัสผ่าน MySQL
        database="graduate49"
    )

# ฟังก์ชันอัปเดตข้อมูลในตาราง ru_queue
def update_database(total_count, remaining_count, counted_ids):
    try:
        db = connect_to_db()
        cursor = db.cursor()
        # แปลง counted_ids เป็น String
        counted_ids_str = ','.join(map(str, counted_ids))
        # เพิ่มข้อมูลในตาราง
        cursor.execute(
            "INSERT INTO ru_queue (total_count, remaining_count, counted_ids) VALUES (%s, %s, %s)",
            (total_count, remaining_count, counted_ids_str)
        )
        db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Error updating database: {e}")


# โหลดโมเดล YOLOv5
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# ตรวจสอบการใช้ GPU
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)

# อ่านวิดีโอ
cap = cv2.VideoCapture('6-1-v2.mp4')
# cap = cv2.VideoCapture('rtmp://202.41.160.68/live/ru999')

# ฟังก์ชันสำหรับติดตามจุดจากเมาส์
def POINTS(event, x, y, flags, param):
    if event == cv2.EVENT_MOUSEMOVE:  
        print(f"Mouse Position: ({x}, {y})")

cv2.namedWindow('FRAME')
cv2.setMouseCallback('FRAME', POINTS)

# อินสแตนซ์ตัวติดตาม
tracker = Tracker()

# พื้นที่โพลิกอน (Polygon zone)
# area_1 = [(748, 476), (736, 237), (759, 236), (772, 468)]  #ใกล้เคียงสุด
# area_1 = [(748, 476), (736, 237), (751, 237), (763, 472)]  #ระยะนี้ดีมากมีผิดพลาดบ้าง
area_1 = [(748, 476), (769, 251), (787, 252), (763, 472)]  #ระยะนี้ดีมากมีผิดพลาดบ้าง
# area_1 = [(727, 468), (793, 226), (818, 243), (785, 472)]
counted_ids = set()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (1020, 500))
    
    # วาดโพลิกอนบนเฟรม
    cv2.polylines(frame, [np.array(area_1, np.int32)], True, (0, 255, 0), 3)
    
    # ใช้ YOLOv5 สำหรับตรวจจับวัตถุ
    results = model(frame)
    detections = []
    for _, row in results.pandas().xyxy[0].iterrows():
        x1, y1, x2, y2 = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
        label = row['name']
        if label == 'person':  # ตรวจจับเฉพาะคน
            detections.append([x1, y1, x2, y2])

    # อัปเดตการติดตาม
    boxes_ids = tracker.update(detections)
    for box_id in boxes_ids:
        x, y, w, h, obj_id = box_id
        cx, cy = (x + w) // 2, (y + h) // 2  # จุดกึ่งกลางของ bounding box
        
        # วาด bounding box และ ID บนเฟรม
        cv2.rectangle(frame, (x, y), (w, h), (255, 0, 255), 2)
        cv2.putText(frame, str(obj_id), (x, y - 10), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
        
        # วาดจุดกึ่งกลาง
        # กำหนดระยะที่ต้องการให้จุดเลื่อนลงจากกึ่งกลาง
        offset = 50  # ระยะห่างที่ต้องการเลื่อนลง (ปรับได้ตามต้องการ)

        # คำนวณตำแหน่งจุดกึ่งกลางและปรับตำแหน่งในแนวตั้ง
        cx, cy = (x + w) // 2, (y + h) // 2
        cy_adjusted = cy + offset  # ปรับตำแหน่งลง

        # วาดจุดที่ตำแหน่งใหม่
        cv2.circle(frame, (cx, cy_adjusted), 5, (0, 255, 255), -1)
        
        # ตรวจสอบว่าจุดกึ่งกลางอยู่ในโซนหรือไม่
        result = cv2.pointPolygonTest(np.array(area_1, np.int32), (cx, cy), False)
        print(f"Object ID {obj_id}: Center = ({cx}, {cy}), Result = {result}")
        if result > 0:  # จุดอยู่ในโซน
            if obj_id not in counted_ids:
                print(f"Object ID {obj_id} is inside the zone")
                counted_ids.add(obj_id)

    # แสดงจำนวนวัตถุที่นับได้ในโซน
    cv2.putText(frame, f"Count: {len(counted_ids)}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow('FRAME', frame)

    # ออกจากลูปเมื่อกด ESC
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
