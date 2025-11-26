# how to use mediapipe model on videos

import mediapipe as mp
import cv2  #handling images and videos

cap = cv2.VideoCapture(0)  # this one for capturing videos from camera

while True:
    ret, image = cap.read()
    if ret is not True:
        break
    height, width, _ = image.shape
    mp_face_mesh =  mp.solutions.face_mesh  #face mesh object
    face_mesh = mp_face_mesh.FaceMesh()

    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) # convert images from BGR to RGB

    result = face_mesh.process(rgb_image)
    for facial_landmarks in result.multi_face_landmarks: #landmarks such as lips eyes etc
        for i in range(0, 468): #for each point in this landmark
            pt1 = facial_landmarks.landmark[i] #get the point
            x = int(pt1.x * width)  
            y = int(pt1.y * height)
            cv2.circle(image, (x, y), 1, (100, 100, 0), -1) #put a circle on it
        cv2.imshow("image", image) 
        cv2.waitKey(1)
        