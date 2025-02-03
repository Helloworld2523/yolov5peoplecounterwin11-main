import torch

# โหลดโมเดล YOLOv8 หรือ YOLOv7
model = torch.hub.load('ultralytics/yolov8', 'yolov8', pretrained=True)

# ตรวจสอบการใช้ GPU
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# ตั้งค่าโมเดลให้ใช้ GPU
model.to(device)
