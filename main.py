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
            if (current_time - last_updated_time) < 2:
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
# ตรวจสอบการใช้ GPU
# device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
# model.to(device)

# อ่านวิดีโอ
# cap = cv2.VideoCapture('6-1-v2.mp4')
# cap = cv2.VideoCapture('http://202.41.160.68:1935/live/ru999/playlist.m3u8')
cap = cv2.VideoCapture('07-02-68.mp4')
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
# area_1 = [(384, 173), (383, 472),(410,178),(409,475)] # xx
# area_1 = [(383, 474), (385, 173),(410,180),(408,470)]#จุดที่0.0
# area_1 = [(372, 473), (375, 198), (421, 206), (419, 476)] #จุดที่ 0
# area_1 = [(345, 472), (345, 192), (467, 186), (453, 477)] #จุดที่ 1
# area_1 = [(444, 474), (466, 194), (508, 189), (498, 472)] #จุดที่ 1.1
# area_1 = [(748, 476), (769, 251), (787, 252), (763, 472)]  #จุดที่ 3 ระยะนี้ *
area_1 = [(748, 476), (769, 251), (777, 252), (757, 472)]  #จุดที่ 3 ระยะนี้ *
area_1 = [(790, 476), (811, 263), (826, 262), (810, 478)]  #จุดที่ 3 ระยะนี้ *
area_1 = [(790, 476), (807, 293), (825, 304), (810, 478)]  #จุดที่ 3 ระยะนี้ *
# 
# p=50 #เพิ่มระยะห่างที่เท่าๆกัน 
# area_1 = [(790+p, 476), (811+p, 263), (826+p, 262), (810+p, 478)] #จุดที่ 4 ระยะนี้ *

p_x = 20  # เพิ่มในแนวแกน X
p_y = 10  # เพิ่มในแนวแกน Y

p_x = 50  # เพิ่มในแนวแกน X
p_y = 10  # เพิ่มในแนวแกน Y

p_x = -10  # เพิ่มในแนวแกน X
p_y = 10  # เพิ่มในแนวแกน Y


# area_1 = [(x + p_x, y + p_y) for x, y in area_1]
# area_1 = [(727, 468), (883, 282), (913, 296), (785, 472)]
counted_ids = set()

# updatecode5_2_68
last_positions = {}  # เก็บตำแหน่งล่าสุดของแต่ละ ID
distance_threshold =20   # ระยะทางขั้นต่ำก่อนนับซ้ำ
# updatecode5_2_68

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
is_counting = True
# กำหนดเวลา cooldown 5 วินาที เพื่อป้องกันการนับซ้ำ
COOLDOWN_TIME = 8
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
    detections = []
    confidences = {}  # ใช้ dictionary เพื่อเก็บค่า conf ตามลำดับของ obj_id
    for i, row in results.pandas().xyxy[0].iterrows():
        x1, y1, x2, y2 = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
        label = row['name']
        conf = row['confidence']
        
        if label == 'person':
            detections.append(([x1, y1, x2, y2]))
            confidences[i] = conf  # เก็บ conf แยกไว้ใน dictionary ตามลำดับ index

    boxes_ids = tracker.update(detections)
    for idx, box_id in enumerate(boxes_ids):
        x, y, w, h, obj_id = box_id
        cx, cy = (x + w) // 2, (y + h) // 2
        # ดึงค่า confidence จาก dictionary (หากหาไม่เจอให้เป็น 0.0)
        conf = confidences.get(idx, 0.0)
        if conf < 0.39 :
            exit
        # วาด bounding box และ ID บนเฟรม
        cv2.rectangle(frame, (x, y), (w, h), (255, 0, 255), 2)
        cv2.putText(frame,  f"ID: {obj_id} ({conf:.2f})", (x, y - 10), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
        
        # วาดจุดที่ตำแหน่งใหม่
        # วาดจุดกึ่งกลาง
        # กำหนดระยะที่ต้องการให้จุดเลื่อนลงจากกึ่งกลาง
        offset = 50  # ระยะห่างที่ต้องการเลื่อนลง (ปรับได้ตามต้องการ)
        cy_adjusted = cy + offset  # ปรับตำแหน่งลง
        cv2.circle(frame, (cx, cy_adjusted), 5, (0, 255, 255), -1)
        
        if is_counting:
            result = cv2.pointPolygonTest(np.array(area_1, np.int32), (cx, cy), False)
            if result > 0 and obj_id not in counted_ids:
                print(f"Object {obj_id} entered counting zone")  # Debug
                
                # ตรวจสอบว่ามีการนับไปแล้วหรือไม่
                current_time = time.time()
                if obj_id in last_counted_time:
                    elapsed_time = current_time - last_counted_time[obj_id]
                    if elapsed_time < COOLDOWN_TIME:
                        print(f"ID {obj_id} skipped due to cooldown ({elapsed_time:.2f}s)")
                        continue  # ข้ามการนับซ้ำ
                    
                # กรณีเดินจากซ้ายไปขวา หรือ ขวาไปซ้าย
                if obj_id in last_positions:
                    last_cx, last_cy = last_positions[obj_id]
                    distance = math.sqrt((cx - last_cx) ** 2 + (cy - last_cy) ** 2)
                    print(f"ID {obj_id} Distance moved: {distance}")  # Debug

                    # ถ้าระยะเคลื่อนที่น้อยเกินไป แสดงว่าอาจเป็นคนยืนอยู่กับที่
                    if distance < distance_threshold:
                        print(f"ID {obj_id} skipped due to low movement")
                        continue

                # ตรวจสอบทิศทางการเดิน
                if obj_id in last_positions:
                    last_cx, last_cy = last_positions[obj_id]
                    
                    # ตรวจสอบการเดินจากซ้ายไปขวา
                    if cx > last_cx:
                        print(f"ID {obj_id} moved LEFT ➝ RIGHT")
                        counted_ids.add(obj_id)  # เพิ่ม ID ในชุดที่นับแล้ว
                    # ตรวจสอบการเดินจากขวาไปซ้าย
                    elif cx < last_cx:
                        print(f"ID {obj_id} moved RIGHT ➝ LEFT")
                        # ไม่ทำการนับ ID เมื่อเดินจากขวาไปซ้าย
                        continue  # ข้ามการนับเมื่อเดินย้อนกลับ

                # บันทึกตำแหน่งและเวลานับล่าสุด
                last_positions[obj_id] = (cx, cy)
                last_counted_time[obj_id] = current_time

                current_count -= 1
                print(f"Updated current_count: {current_count}")  # Debug
                # time.sleep(0.1)
                update_current_count(current_count)

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


    # รอให้กด Spacebar (32) เพื่อไปเฟรมถัดไป
    # is_counting = True
    # key = cv2.waitKey(0) & 0xFF  
    # if key == ord('q'):  # กด 'q' เพื่อออก
    #     break
    # time.sleep(0.05)
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