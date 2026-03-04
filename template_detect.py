import cv2
import time
import numpy as np

def my_filled_circle(img, center, r): #функция для отрисовки точки
    thickness = -1
    line_type = 8
 
    return cv2.circle(img,
               center,
               r,
               (0, 0, 255),
               thickness,
               line_type)

def main():
    # ArUco detector
    dict_ = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50) #<-Словарик меток подгружаем
    params = cv2.aruco.DetectorParameters()#<-параметры детектора подгружаем
    detector = cv2.aruco.ArucoDetector(dict_, params)# создаем детектор

    cap = cv2.VideoCapture(0)  # подключаемся к камере
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera index={0}")
    
    while True:
        ok, frame = cap.read() # получаем кадр с камеры
        if not ok:
            print("Frame grab failed")
            break

        corners, ids, rejected = detector.detectMarkers(frame) # детектируем маркер
        print(corners, type(corners))


        if ids is not None and len(ids) > 0:
            #тут добавим отрисовку точки середины
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)
            min_c = corners[0].min(1)
            max_c = corners[0].max(1)

            sizec = ((max_c + min_c)/2).astype(int).reshape(-1)
            print(sizec)

            frame = my_filled_circle(frame, (sizec[0], sizec[1]), 5)

        cv2.imshow("aruco_detect", frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord('q')):   # ESC or q
            break

    

if __name__ == "__main__":
    main()