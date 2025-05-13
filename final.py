import cv2
import numpy as np
import threading
import time
import math
import dlib
import os
import winsound
from inference_sdk import InferenceHTTPClient
from collections import deque
from datetime import datetime

class AttentionMonitor:
    def __init__(self):
        self.running = True
        self.window_size = 30
        self.phone_detections = deque([0] * self.window_size, maxlen=self.window_size)
        self.earbud_detections = deque([0] * self.window_size, maxlen=self.window_size)
        self.pose_counts = {
            'Looking Left': 0,
            'Looking Right': 0,
            'Looking Down': 0
        }
        
        self.debug = True
        self.pose_threshold = 10
        self.phone_threshold = 5
        self.earbud_threshold = 5
        
        self.alert_cooldown = 5
        self.last_alert_time = {
            'pose': 0,
            'phone': 0,
            'earbud': 0
        }
        
        self.frame_counter = 0
        self.setup_models()
        

    def setup_models(self):
        print("Setting up models...")
        
        self.detector = dlib.get_frontal_face_detector()
        predictor_path = "shape_predictor_68_face_landmarks.dat"
        if not os.path.exists(predictor_path):
            print("Shape predictor file not found!")
            raise FileNotFoundError("shape_predictor_68_face_landmarks.dat not found")
        self.predictor = dlib.shape_predictor(predictor_path)
        print("Face detector initialized")
        
        if not os.path.exists("yolov4.weights") or not os.path.exists("yolov4.cfg"):
            print("YOLO files missing! Please download yolov4.weights and yolov4.cfg")
            raise FileNotFoundError("YOLO files not found")
            
        self.net = cv2.dnn.readNet("yolov4.weights", "yolov4.cfg")
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            print("Using CUDA for YOLO")
        else:
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            print("Using CPU for YOLO")
            
        self.layer_names = self.net.getLayerNames()
        self.output_layers = [self.layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
        print("YOLO initialized")
        
        try:
            self.client_earphone = InferenceHTTPClient(
                api_url="https://detect.roboflow.com",
                api_key="7jvLHlOsHPI5LaYlUB8q"
            )
            print("Roboflow client initialized")
        except Exception as e:
            print(f"Error initializing Roboflow client: {e}")
            raise

    def play_alert(self, alert_type):
        current_time = time.time()
        if current_time - self.last_alert_time[alert_type] >= self.alert_cooldown:
            winsound.Beep(1000, 500)
            self.last_alert_time[alert_type] = current_time
            print(f"Alert: {alert_type} detection threshold exceeded!")

    def head_pose_estimation(self, shape, frame):
        image_points = np.array([
            (shape.part(30).x, shape.part(30).y),    # Nose tip
            (shape.part(8).x, shape.part(8).y),      # Chin
            (shape.part(36).x, shape.part(36).y),    # Left eye left corner
            (shape.part(45).x, shape.part(45).y),    # Right eye right corner
            (shape.part(48).x, shape.part(48).y),    # Left mouth corner
            (shape.part(54).x, shape.part(54).y)     # Right mouth corner
        ], dtype="double")

        model_points = np.array([
            (0.0, 0.0, 0.0),             # Nose tip
            (0.0, -330.0, -65.0),        # Chin
            (-225.0, 170.0, -135.0),     # Left eye left corner
            (225.0, 170.0, -135.0),      # Right eye right corner
            (-150.0, -150.0, -125.0),    # Left mouth corner
            (150.0, -150.0, -125.0)      # Right mouth corner
        ])

        size = frame.shape
        focal_length = size[1]
        center = (size[1]/2, size[0]/2)
        camera_matrix = np.array(
            [[focal_length, 0, center[0]],
             [0, focal_length, center[1]],
             [0, 0, 1]], dtype="double"
        )

        dist_coeffs = np.zeros((4,1))
        
        success, rotation_vector, translation_vector = cv2.solvePnP(
            model_points, image_points, camera_matrix, dist_coeffs
        )

        if success:
            rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
            pitch, yaw, _ = self.rotation_matrix_to_euler_angles(rotation_matrix)
            return pitch, yaw
        return None, None

    def rotation_matrix_to_euler_angles(self, rotation_matrix):
        sy = math.sqrt(rotation_matrix[0, 0] * rotation_matrix[0, 0] + rotation_matrix[1, 0] * rotation_matrix[1, 0])
        singular = sy < 1e-6

        if not singular:
            x = math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
            y = math.atan2(-rotation_matrix[2, 0], sy)
            z = math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
        else:
            x = math.atan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
            y = math.atan2(-rotation_matrix[2, 0], sy)
            z = 0

        return np.degrees(x), np.degrees(y), np.degrees(z)

    def detect_phone(self, frame):
        height, width = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
        self.net.setInput(blob)
        
        try:
            outs = self.net.forward(self.output_layers)
            
            class_ids = []
            confidences = []
            boxes = []
            
            for out in outs:
                for detection in out:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    
                    if confidence > 0.5:
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)
                        
                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)
                        
                        boxes.append([x, y, w, h])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)
            
            indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
            phone_detected = False
            
            if len(indexes) > 0:
                for i in indexes.flatten():
                    if class_ids[i] == 67:  # Phone class ID
                        phone_detected = True
                        box = boxes[i]
                        cv2.rectangle(frame, (box[0], box[1]), 
                                    (box[0] + box[2], box[1] + box[3]), (0, 255, 0), 2)
                        cv2.putText(frame, f"Phone ({confidences[i]:.2f})", 
                                  (box[0], box[1] - 10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            if self.debug:
                cv2.putText(frame, f"Phone Detected: {phone_detected}", 
                           (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            return phone_detected
            
        except Exception as e:
            print(f"Error in phone detection: {e}")
            return False

    def detect_earbuds(self, frame):
        try:
            temp_path = f"temp_frame_{int(time.time())}.jpg"
            cv2.imwrite(temp_path, frame)
            
            result = self.client_earphone.infer(temp_path, model_id="earphone-detection-75qzd/1")
            predictions = result.get("predictions", [])
            
            for pred in predictions:
                x = int(pred["x"])
                y = int(pred["y"])
                w = int(pred["width"])
                h = int(pred["height"])
                cv2.rectangle(frame, (x - w//2, y - h//2), 
                            (x + w//2, y + h//2), (0, 0, 255), 2)
                cv2.putText(frame, f"Earbud ({pred['confidence']:.2f})", 
                           (x - w//2, y - h//2 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            earbud_detected = len(predictions) > 0
            
            if self.debug:
                cv2.putText(frame, f"Earbuds Detected: {earbud_detected}", 
                           (10, 110),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            return earbud_detected
            
        except Exception as e:
            print(f"Error in earbud detection: {e}")
            return False

    def process_frame(self, frame):
        frame = cv2.resize(frame, (640, 480))
        self.frame_counter += 1
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector(gray)
        
        for face in faces:
            shape = self.predictor(gray, face)
            pitch, yaw = self.head_pose_estimation(shape, frame)
            
            if pitch is not None and yaw is not None:
                if yaw < -20:
                    self.pose_counts['Looking Left'] += 1
                elif yaw > 20:
                    self.pose_counts['Looking Right'] += 1
                elif pitch < -20:
                    self.pose_counts['Looking Down'] += 1
                else:
                    self.pose_counts = {k: max(0, v - 1) for k, v in self.pose_counts.items()}
        
        phone_detected = self.detect_phone(frame)
        self.phone_detections.append(1 if phone_detected else 0)
        
        if self.frame_counter % 5 == 0:
            earbud_detected = self.detect_earbuds(frame)
            self.earbud_detections.append(1 if earbud_detected else 0)
        
        if sum(self.phone_detections) >= self.phone_threshold:
            self.play_alert('phone')
            self.phone_detections.clear()
            self.phone_detections.extend([0] * self.window_size)
        
        if sum(self.earbud_detections) >= self.earbud_threshold:
            self.play_alert('earbud')
            self.earbud_detections.clear()
            self.earbud_detections.extend([0] * self.window_size)
        
        for pose, count in self.pose_counts.items():
            if count >= self.pose_threshold:
                self.play_alert('pose')
                self.pose_counts[pose] = 0
        
        cv2.putText(frame, 
                    f"Head Pose - Left: {self.pose_counts['Looking Left']} Right: {self.pose_counts['Looking Right']} Down: {self.pose_counts['Looking Down']}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        cv2.putText(frame, 
                    f"Phone Detections: {sum(self.phone_detections)}/{self.phone_threshold}", 
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.putText(frame, 
                    f"Earbud Detections: {sum(self.earbud_detections)}/{self.earbud_threshold}", 
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return frame
    
    def stop(self):
        self.running = False

    def run(self):
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    break
                
                processed_frame = self.process_frame(frame)
                cv2.imshow('Attention Monitor', processed_frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                time.sleep(0.01)
        
        finally:
            cap.release()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        monitor = AttentionMonitor()
        monitor.run()
    except Exception as e:
        print(f"Error: {e}")