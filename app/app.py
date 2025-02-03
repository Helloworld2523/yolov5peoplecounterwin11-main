from flask import Flask, render_template, request, redirect, url_for, jsonify
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# ฟังก์ชันดึงข้อมูลจากฐานข้อมูล
def fetch_queue_data():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="graduate49"
        )
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM ru_queue ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        return result
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

# เส้นทางหน้าเว็บหลัก
@app.route('/')
def index():
    return render_template('index.html')

# เส้นทาง API สำหรับดึงข้อมูล
@app.route('/api/queue', methods=['GET'])
def get_queue():
    data = fetch_queue_data()
    if data:
        # หากไม่มีข้อมูลในตาราง ru_queue
        if data['current_count'] == 0:
            data['message'] = "นับครบแล้ว"
        else:
            data['message'] = ""
        return jsonify(data)
    else:
        # กรณีไม่สามารถดึงข้อมูลได้
        return jsonify({"error": "ไม่สามารถดึงข้อมูลได้"}), 500

# เส้นทางหน้า Edit
@app.route('/edit_queue', methods=['GET'])
def edit_queue():
    data = fetch_queue_data()
    if data:
        return render_template('edit_queue.html', current_count=data['current_count'], remaining_count=data['remaining_count'], total_count=data['total_count'])
    else:
        return "Data not found", 404

# เส้นทางสำหรับการบันทึกข้อมูลที่แก้ไข
@app.route('/update_queue', methods=['POST'])
def update_queue():
    current_count = request.form.get('current_count')
    total_count = request.form.get('total_count')
    remaining_count = request.form.get('remaining_count')
    # เชื่อมต่อกับฐานข้อมูลเพื่ออัปเดตค่า
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="graduate49"
    )
    cursor = db.cursor()
    cursor.execute("""
        UPDATE ru_queue
        SET current_count = %s,remaining_count=%s, total_count = %s
        WHERE id = 1
    """, (current_count,remaining_count, total_count))
    db.commit()
    cursor.close()
    db.close()

    return redirect(url_for('edit_queue'))


# เส้นทางหน้าเว็บหลัก
@app.route('/monitor')
def monitor():
    return render_template('monitor.html')

@app.route('/api/update_queue_button', methods=['POST'])
def update_queue_button():
    print('update_queue_button')
    try:
        # รับข้อมูล JSON จากคำขอ
        data = request.json
        action = data.get('action')

        # เชื่อมต่อฐานข้อมูล
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="graduate49"
        )
        cursor = db.cursor()

        # ดึงข้อมูลปัจจุบันจากตาราง ru_queue
        cursor.execute("SELECT current_count, remaining_count,total_count FROM ru_queue WHERE id = 1")
        row = cursor.fetchone()

        if not row:
            return jsonify({"success": False, "message": "Queue data not found."})

        current_count, remaining_count,total_count = row
        remaining_count = remaining_count

        # อัปเดตค่าตาม action
        if action == 'increment':
            current_count += 1
        elif action == 'decrement' and current_count > 0:
            current_count -= 1
        else:
            return jsonify({"success": False, "message": "Invalid action or count is already zero."})

        # คำนวณ remaining_count ใหม่
        # remaining_count = total_count - current_count

        # อัปเดตค่าลงฐานข้อมูล
        cursor.execute("""
            UPDATE ru_queue
            SET current_count = %s, remaining_count = %s, total_count = %s
            WHERE id = 1
        """, (current_count, remaining_count, total_count))
        db.commit()

        # ปิดการเชื่อมต่อ
        cursor.close()
        db.close()

        # ส่งผลลัพธ์กลับไปยัง frontend
        return jsonify({
            "success": True,
            "current_count": current_count,
            "remaining_count": remaining_count,
            "total_count": total_count
        })

    except Exception as e:
        # จัดการข้อผิดพลาด
        return jsonify({"success": False, "message": str(e)})



if __name__ == '__main__':
    app.run(debug=True)
