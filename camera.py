import cv2
import time
import numpy as np

IDS_BOUNDARY = [0, 1, 2, 3] 
IDS_BEES     = [4, 5, 6] 
ID_HIVE    = [7]      
IDS_FLOWERS   = [8, 9, 10]  

EXPIRATION_TIME = 7 
marker_memory = {}


def get_marker_center(corners):
    return corners.reshape(-1, 2).mean(axis=0).astype(int)

def get_categorized_objects(memory):
    categorized = {
        "boundary": [],
        "bees": [],
        "hives": [],
        "flowers": []
    }
    
    for m_id, data in memory.items():
        center = get_marker_center(data['corners'])
        obj_info = {'id': m_id, 'center': tuple(center)}
        
        if m_id in IDS_BOUNDARY:
            categorized["boundary"].append(obj_info)
        elif m_id in IDS_BEES:
            categorized["bees"].append(obj_info)
        elif m_id in ID_HIVE:
            categorized["hives"].append(obj_info)
        elif m_id in IDS_FLOWERS:
            categorized["flowers"].append(obj_info)
            
    return categorized

def main():
    dict_ = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(dict_, params)

    cap = cv2.VideoCapture(0)
    
    while True:
        ok, frame = cap.read()
        if not ok: break

        current_time = time.time()
        corners, ids, _ = detector.detectMarkers(frame)

        if ids is not None:
            for i, m_id in enumerate(ids.flatten()):
                marker_memory[m_id] = {'corners': corners[i], 'last_seen': current_time}

        expired_ids = [m_id for m_id, d in marker_memory.items() if current_time - d['last_seen'] > EXPIRATION_TIME]
        for m_id in expired_ids: del marker_memory[m_id]

        objs = get_categorized_objects(marker_memory)

        
        for bee in objs["bees"]:
            cv2.circle(frame, bee['center'], 8, (255, 0, 0), -1)
            cv2.putText(frame, f"Bee {bee['id']}", bee['center'], cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1)

        for hive in objs["hives"]:
            c = hive['center']
            cv2.rectangle(frame, (c[0]-10, c[1]-10), (c[0]+10, c[1]+10), (255, 72, 0), 2)
            cv2.putText(frame, "HIVE", (c[0]-15, c[1]-15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 72, 0), 1)

        for flower in objs["flowers"]:
            cv2.drawMarker(frame, flower['center'], (0, 255, 0), cv2.MARKER_TILTED_CROSS, 15, 2)
            cv2.putText(frame, f"Flower {flower['id']}", (flower['center'][0] + 10, flower['center'][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 56, 189), 1)

        if len(objs["boundary"]) >= 3:
            hull_points = np.array([marker_memory[b['id']]['corners'] for b in objs["boundary"]]).reshape(-1, 2).astype(int)
            hull = cv2.convexHull(hull_points)
            cv2.drawContours(frame, [hull], -1, (0, 255, 0), 2)

        cv2.imshow("Detection System", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()