import cv2
import torch 
from tracker import *
import numpy as np

import mysql.connector
from datetime import datetime

import sys  # นำเข้า sys เพื่อใช้ exit()
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
# ฟังก์ชันสำหรับการเชื่อมต่อฐานข้อมูล
def connect_to_db():
    return mysql.connector.connect(
        host="localhost",  # แก้ไขให้ตรงกับเซิร์ฟเวอร์ของคุณ
        user="root",       # ชื่อผู้ใช้ MySQL
        password="",  # รหัสผ่าน MySQL
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


# ฟังก์ชันดึงข้อมูล total_count และ current_count ล่าสุดจากฐานข้อมูล
def get_total_and_current_count():
    try:
        db = connect_to_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT total_count, current_count FROM ru_queue ORDER BY queue_date DESC LIMIT 1")
        result = cursor.fetchone()
        cursor.close()
        db.close()
        if result:
            return result['total_count'], result['current_count']
        else:
            return 0, 0  # หากไม่มีข้อมูลในฐานข้อมูล
    except Exception as e:
        print(f"Error fetching data: {e}")
        return 0, 0

# ฟังก์ชันอัปเดต current_count
def update_current_count(new_current_count):
    try:
        db = connect_to_db()
        cursor = db.cursor()
        cursor.execute(
            "UPDATE ru_queue SET current_count = %s WHERE id = 1",
            (new_current_count,)
        )
        db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Error updating current count: {e}")

# โหลดโมเดล YOLOv5
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# ตรวจสอบการใช้ GPU
# device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
# model.to(device)

# อ่านวิดีโอ
# cap = cv2.VideoCapture('6-1-v2.mp4')
cap = cv2.VideoCapture('http://202.41.160.68:1935/live/ru999/playlist.m3u8')
# cap = cv2.VideoCapture(0)

# ฟังก์ชันสำหรับติดตามจุดจากเมาส์
def POINTS(event, x, y, flags, param):
    if event == cv2.EVENT_MOUSEMOVE:  
        print(f"Mouse Position: ({x}, {y})")

cv2.namedWindow('FRAME')
cv2.setMouseCallback('FRAME', POINTS)

# อินสแตนซ์ตัวติดตาม
tracker = Tracker()

# พื้นที่โพลิกอน (Polygon zone)

# area_1 = [(727, 468), (793, 226), (818, 243), (785, 472)]
# area_1 = [(372, 473), (375, 198), (421, 206), (419, 476)] #จุดที่ 0
# area_1 = [(345, 472), (345, 192), (467, 186), (453, 477)] #จุดที่ 1
# area_1 = [(444, 474), (466, 194), (508, 189), (498, 472)] #จุดที่ 1.1
area_1 = [(748, 476), (769, 251), (787, 252), (763, 472)]  #จุดที่ 3 ระยะนี้ *
counted_ids = set()

# ดึงข้อมูล total_count และ current_count จากฐานข้อมูล
total_count, current_count = get_total_and_current_count()

if total_count == 0:  # หากไม่มีข้อมูลในฐานข้อมูล ให้กำหนดค่าเริ่มต้น
    # total_count = 100  # ตั้งค่า total_count เริ่มต้น (ปรับตามความต้องการ)
    current_count = total_count
    update_database(total_count, current_count, [])


# ตรวจสอบ current_count เมื่อมันเป็น 0 ให้หยุดโปรแกรม
if current_count == 0:
    print("Current count is 0. Exiting the program.")
    sys.exit()  # ออกจากโปรแกรมทันที

# ตัวแปรควบคุมการนับ
is_counting = False

while True:
    total_count, current_count = get_total_and_current_count()
    
    if current_count == 0:
        print("Current count is 0. Exiting the program.")
        sys.exit()  # ออกจากโปรแกรมทันที
    
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
        cx, cy = (x + w) // 2, (y + h) // 2
        
        # วาด bounding box และ ID บนเฟรม
        cv2.rectangle(frame, (x, y), (w, h), (255, 0, 255), 2)
        cv2.putText(frame, str(obj_id), (x, y - 10), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
        
        # วาดจุดที่ตำแหน่งใหม่
        # วาดจุดกึ่งกลาง
        # กำหนดระยะที่ต้องการให้จุดเลื่อนลงจากกึ่งกลาง
        offset = 50  # ระยะห่างที่ต้องการเลื่อนลง (ปรับได้ตามต้องการ)
        cy_adjusted = cy + offset  # ปรับตำแหน่งลง
        cv2.circle(frame, (cx, cy_adjusted), 5, (0, 255, 255), -1)
        
        
        if is_counting:
            result = cv2.pointPolygonTest(np.array(area_1, np.int32), (cx, cy), False)
            if result > 0 and obj_id not in counted_ids:
                counted_ids.add(obj_id)
                current_count -= 1  # ลด current_count เมื่อมีการนับวัตถุ
                # print(current_count)
                update_current_count(current_count)  # อัปเดต current_count ในฐานข้อมูล

    cv2.putText(frame, f"Total: {total_count}, Remaining: {current_count}", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow('FRAME', frame)

    # if cv2.waitKey(1) & 0xFF == 27:
    #     break
    
    
    # ดักจับปุ่ม ESC (27) และปุ่ม S (115)
    # key = cv2.waitKey(1) & 0xFF
    # if key == 27:  # ESC เพื่อออกจากโปรแกรม
    #     break
    # elif key == ord('s'):  # ปุ่ม S เพื่อหยุดการนับ
    #     print("Counting paused. Press R to resume.")
    #     while True:
    #         key = cv2.waitKey(1) & 0xFF
    #         if key == ord('r'):  # ปุ่ม R เพื่อกลับมานับต่อ
    #             print("Counting resumed.")
    #             break
    #         elif key == 27:  # ESC เพื่อออกจากโปรแกรมขณะหยุด
    #             sys.exit()

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
