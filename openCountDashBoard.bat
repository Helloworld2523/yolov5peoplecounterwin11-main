@echo off
cd /d C:\Users\RU\Documents\yolov5peoplecounterwin11-main\app 
call .\venv\Scripts\activate
start python .\app.py

:: รอ 5 วินาที (หรือปรับค่าเป็นเวลาที่ต้องการ)
timeout /t 5 /nobreak


:: เปิด Chrome ผ่านพาธที่แน่นอน
start ""  http://127.0.0.1:5000/
start ""  http://127.0.0.1:5000/monitor
start ""  http://127.0.0.1:5000/edit_queue