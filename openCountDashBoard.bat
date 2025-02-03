@echo off
cd /d C:\Users\RU\Documents\yolov5peoplecounterwin11-main\app 
call .\venv\Scripts\activate
python .\app.py


:: เปิด Google Chrome ไปที่ URL ที่ต้องการ
start chrome http://127.0.0.1:5000/
start chrome http://127.0.0.1:5000/monitor
start chrome http://127.0.0.1:5000/edit_queue