import cv2
import torch
from tracker import *
import numpy as np
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# cap=cv2.VideoCapture('cctv.mp4')
cap=cv2.VideoCapture('6-1-v2.mp4')
# อ่านจากสตรีม URL
# cap = cv2.VideoCapture('http://202.41.160.68:1935/live/klb201/playlist.m3u8')

def POINTS(event, x, y, flags, param):
    if event == cv2.EVENT_MOUSEMOVE :  
        colorsBGR = [x, y]
        print(colorsBGR)
        

cv2.namedWindow('FRAME')
cv2.setMouseCallback('FRAME', POINTS)

tracker = Tracker()


# area_1=[(366,315),(429,373),(535,339),(500,296)]#ต้นฉบับ
# area_1=[(414,295),(583,244),(601,274),(441,313)]#จะทำเป็นเส้น
# area_1 = [(366, 415), (429, 473), (535, 439), (500, 396)]
# area_1 = [(309, 423), (365, 487), (470, 451), (437, 404)]
#area_1 = [(362, 477), (370, 444), (413, 444), (403, 491)]
# area_1 = [(361, 488), (371, 451), (447, 452), (446, 484)]
#area_1 = [(432, 487), (467, 421), (531, 413), (545, 483)]#จุดที่สอง
area_1 = [(403, 482), (427, 433), (461, 437), (449, 480)]#จุดที่สอง
# area_1 = [(308, 288), (305, 220), (448, 230), (456, 382)]
area1=set()
while True:
    ret,frame=cap.read()
    frame=cv2.resize(frame,(1020,500))
    cv2.polylines(frame,[np.array(area_1,np.int32)],True,(0,255,0),3)
    results=model(frame)
    #frame=np.squeeze(results.render())
    list=[]
    for index,row in results.pandas().xyxy[0].iterrows():
        x1=int(row['xmin'])
        y1=int(row['ymin'])
        x2=int(row['xmax'])
        y2=int(row['ymax'])
        b=(row['name'])
        if 'person' in b:
            list.append([x1,y1,x2,y2])
    boxes_ids=tracker.update(list)
    for box_id in boxes_ids:
        x,y,w,h,id=box_id
        cv2.rectangle(frame,(x,y),(w,h),(255,0,255),2)
        cv2.putText(frame,str(id),(x,y),cv2.FONT_HERSHEY_PLAIN,3,(0,0,255),2)
        # print(w,h)
        result=cv2.pointPolygonTest(np.array(area_1,np.int32),(int(w),int(h)),False)
        # print(result)
        if result > 0 :
            area1.add(id)
            print("จุดอยู่ภายในโพลิกอน")
        # elif result < 0:
        #     print("จุดอยู่ภายนอกโพลิกอน")
        # else:
        #     print("จุดอยู่บนขอบของโพลิกอน")
            
    p=len(area1)
    cv2.putText(frame,str(p),(20,30),cv2.FONT_HERSHEY_PLAIN,3,(0,0,255),2)
    cv2.imshow('FRAME',frame)
    if cv2.waitKey(1)&0xFF==27:
        break
cap.release()
cv2.destroyAllWindows()
    
    
