import cv2
import torch 
from tracker import *
import numpy as np

import mysql.connector
from datetime import datetime

import sys  # นำเข้า sys เพื่อใช้ exit()
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import time  # นำเข้าไลบรารี time
import math
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
# def update_current_count(new_current_count):
#     # time.sleep(0.2)
#     try:
#         db = connect_to_db()
#         cursor = db.cursor()
#         cursor.execute(
#             "UPDATE ru_queue SET current_count = %s WHERE id = 1",
#             (new_current_count,)
#         )
#         db.commit()
#         cursor.close()
#         db.close()
#     except Exception as e:
#         print(f"Error updating current count: {e}")

# ฟังก์ชันอัปเดต current_count โดยตรวจสอบ last_updated
def update_current_count(new_current_count):
    try:
        db = connect_to_db()
        cursor = db.cursor(dictionary=True)  # ✅ ใช้ dictionary=True

        # ดึงเวลาล่าสุดจากฐานข้อมูล
        cursor.execute("SELECT last_updated FROM ru_queue WHERE id = 1")
        result = cursor.fetchone()

        if result and result["last_updated"]:
            last_updated_time = result["last_updated"].timestamp()
            current_time = time.time()

            # ถ้าเวลาห่างกันน้อยกว่า 2 วินาที ให้ข้ามการอัปเดต
            if (current_time - last_updated_time) < 1.5:
                print("Skipping update: Last update was too recent.")
                return

        # อัปเดตค่าใหม่
        cursor.execute("""
            UPDATE ru_queue 
            SET current_count = %s, last_updated = NOW()
            WHERE id = 1
        """, (new_current_count,))

        db.commit()
        cursor.close()
        db.close()

        print("Current count updated successfully.")

    except Exception as e:
        print(f"Error updating current count: {e}")

# โหลดโมเดล YOLOv5
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
model.conf = 0.40  # Confidence threshold (ค่ามากขึ้น = ตรวจจับเฉพาะวัตถุที่มั่นใจมากขึ้น)0.39
# model.iou = 0.10   # IOU threshold (ค่ามากขึ้น = ลดการตรวจจับวัตถุซ้ำ)

# อ่านวิดีโอ
# cap = cv2.VideoCapture('6-1-v2.mp4')
cap = cv2.VideoCapture('http://202.41.160.68:1935/live/ru999/playlist.m3u8')
# cap = cv2.VideoCapture('07-02-68.mp4')
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

area_1 = [(790, 476), (807, 293), (825, 304), (810, 478)]  #จุดที่ 4 ปรับตั้งจุด พื้นที่ใหม่ โดยให้มีขนาดสั้นลง เพื่อป้องกัน คนด้านบนเดินทับเส้น *
counted_ids = set()


last_positions = {}  # เก็บตำแหน่งล่าสุดของแต่ละ ID

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
# กำหนดเวลา cooldown 5 วินาที เพื่อป้องกันการนับซ้ำ
COOLDOWN_TIME = 3 # หน่วยเป็นวินาที (แนะนำ 1-3 วินาที)
DISTANCE_THRESHOLD = 20  # ถ้าระยะเคลื่อนที่น้อยกว่า 20 px จะไม่นับซ้ำ
last_counted_time = {}

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

    boxes_ids = []  # ลิสต์สำหรับเก็บข้อมูล bounding box ที่ตรวจพบ
    confidences = {}  # Dictionary สำหรับเก็บค่า confidence ของแต่ละ obj_id

    for i, row in results.pandas().xyxy[0].iterrows():
        x1, y1, x2, y2 = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
        label = row['name']
        conf = row['confidence']

        if label == 'person' and conf >= 0.39:
            obj_id = len(boxes_ids)  # ใช้ index เป็น ID ชั่วคราว
            boxes_ids.append([x1, y1, x2, y2])
            # confidences[obj_id] = conf

    # อัปเดตข้อมูลการติดตามวัตถุ
    tracked_objects = tracker.update(boxes_ids)

    for x, y, w, h, obj_id in tracked_objects:
        cx, cy = (x + w) // 2, (y + h) // 2
        # conf = confidences.get(obj_id, 0.0)  # ดึงค่า confidence จาก dictionary

        # วาด bounding box และ ID บนเฟรม
        cv2.rectangle(frame, (x, y), (w, h), (255, 0, 255), 2)
        # cv2.putText(frame, f"ID: {obj_id} ({conf:.2f})", (x, y - 10), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
        cv2.putText(frame, f"ID: {obj_id}", (x, y - 10), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)

        # วาดจุดกึ่งกลาง
        offset = 50
        cy_adjusted = cy + offset
        cv2.circle(frame, (cx, cy_adjusted), 5, (0, 255, 255), -1)

        if is_counting:
            result = cv2.pointPolygonTest(np.array(area_1, np.int32), (cx, cy), False)

            if result > 0:
                # ตรวจสอบวัตถุนี้เคยนับแล้วหรือยัง
                if obj_id in counted_ids:
                    print(f"ID {obj_id} already counted, skipping")
                    continue

                # ตรวจสอบระยะทางการเคลื่อนที่ของวัตถุ
                if obj_id in last_positions:
                    last_cx, last_cy = last_positions[obj_id]
                    distance = math.sqrt((cx - last_cx) ** 2 + (cy - last_cy) ** 2)
                    print("ตรวจสอบระยะทางการเคลื่อนที่ของวัตถุ")
                    print(f"ID {obj_id} Distance moved: {distance}")

                    if distance < DISTANCE_THRESHOLD:
                        print(f"ID {obj_id} skipped due to low movement")
                        continue
                    
                    # ตรวจสอบทิศทางการเดิน
                    if cx > last_cx:
                        print(f"ID {obj_id} moved LEFT ➝ RIGHT")
                        counted_ids.add(obj_id)
                    elif cx < last_cx:
                        print(f"ID {obj_id} moved RIGHT ➝ LEFT")
                        continue
                    
                # ตรวจสอบระยะเวลาระหว่างการนับ
                current_time = time.time()
                if obj_id in last_counted_time:
                    elapsed_time = current_time - last_counted_time[obj_id]
                    if elapsed_time < COOLDOWN_TIME:
                        print(f"ID {obj_id} skipped due to cooldown ({elapsed_time:.2f}s)")
                        last_counted_time[obj_id] = current_time  # บันทึกเวลานับล่าสุด
                        continue
                last_counted_time[obj_id] = current_time  # บันทึกเวลานับล่าสุด
                

                    
                # # ตรวจสอบระยะทางเคลื่อนที่ของวัตถุ
                # if obj_id in last_positions:
                #     last_cx, last_cy = last_positions[obj_id]
                #     distance = math.sqrt((cx - last_cx) ** 2 + (cy - last_cy) ** 2)
                #     print(f"ID {obj_id} Distance moved: {distance}")

                #     if distance < DISTANCE_THRESHOLD:
                #         print(f"ID {obj_id} skipped due to low movement")
                #         continue

                # ตรวจสอบทิศทางการเดิน
                # if obj_id in last_positions:
                #     last_cx, last_cy = last_positions[obj_id]
                #     if cx > last_cx:
                #         print(f"ID {obj_id} moved LEFT ➝ RIGHT")
                #         counted_ids.add(obj_id)
                #     elif cx < last_cx:
                #         print(f"ID {obj_id} moved RIGHT ➝ LEFT")
                #         continue

                # บันทึกตำแหน่งและเวลานับล่าสุด
                last_positions[obj_id] = (cx, cy)
                last_counted_time[obj_id] = current_time

                # อัปเดตตัวนับ
                current_count -= 1
                update_current_count(current_count)
                print(f"Updated current_count: {current_count}")

        cv2.putText(frame, f"Total: {total_count}, Remaining: {current_count}", (20, 50),
        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('FRAME', frame)


    # รอให้กด Spacebar (32) เพื่อไปเฟรมถัดไป
    # is_counting = True
    # key = cv2.waitKey(0) & 0xFF  
    # if key == ord('q'):  # กด 'q' เพื่อออก
    #     break
    # time.sleep(0.05)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('s') or current_count==20: # เมื่อกดดปุ่ม s หรือ จำนวนเหลือ 20 จะให้หยุดการทำงานเพื่อทำการนับเอง
        is_counting = False
        print("Counting paused.")
    elif key == ord('r'):
        is_counting = True
        print("Counting resumed.")
    elif key == 27:  # ESC key
        break
             
cap.release()
cv2.destroyAllWindows()