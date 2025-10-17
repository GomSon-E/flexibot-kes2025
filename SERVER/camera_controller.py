from pypylon import pylon
import cv2
import numpy as np
from ultralytics import YOLO
import threading

class CameraController:
    """카메라 및 비전 처리 통합 컨트롤러"""
    
    def __init__(self, model_path='../MODEL/final_lego_model.pt'):
        self.camera = None
        self.converter = pylon.ImageFormatConverter()
        self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        
        # ROI 설정
        self.roi = [684, 421, 1256, 978]  # [x, y, w, h]
        
        # YOLO 모델 로드
        self.model = YOLO(model_path)
        print(f"✓ 모델 로드: {model_path}")
        
        self.lock = threading.Lock()
        self.current_frame = None
        self.running = False
        
        # 최신 검출 결과 저장
        self.latest_results = None
        
    def connect_camera(self):
        """카메라 연결"""
        try:
            tl_factory = pylon.TlFactory.GetInstance()
            devices = tl_factory.EnumerateDevices()
            
            if len(devices) == 0:
                print("✗ 연결된 카메라가 없습니다")
                return False
            
            self.camera = pylon.InstantCamera(tl_factory.CreateFirstDevice())
            self.camera.Open()
            
            print(f"✓ 카메라 연결: {self.camera.GetDeviceInfo().GetModelName()}")
            return True
            
        except Exception as e:
            print(f"✗ 카메라 연결 실패: {e}")
            return False
    
    def set_roi(self, x: int, y: int):
        """ROI 위치 변경"""
        with self.lock:
            self.roi[0] = x
            self.roi[1] = y
        print(f"✓ ROI 변경: ({x}, {y})")
    
    def get_front_centroids(self):
        """연두색(front) 객체의 중심점 추출"""
        with self.lock:
            if self.latest_results is None:
                return []
            results = self.latest_results
        
        centroids = []
        
        if results[0].boxes is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            classes = results[0].boxes.cls.cpu().numpy()
            confs = results[0].boxes.conf.cpu().numpy()
            
            for box, cls, conf in zip(boxes, classes, confs):
                if conf < 0.8:
                    continue
                
                # front 클래스만 처리
                if int(cls) == 1:
                    x1, y1, x2, y2 = map(int, box)
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    centroids.append((center_x, center_y))
        
        return centroids
    
    def start_capture(self):
        """캡처 시작"""
        if not self.camera:
            return False
        
        self.running = True
        self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        threading.Thread(target=self._capture_loop, daemon=True).start()
        return True
    
    def _capture_loop(self):
        """실시간 캡처 및 추론"""
        while self.running and self.camera.IsGrabbing():
            try:
                grab_result = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                
                if grab_result.GrabSucceeded():
                    image = self.converter.Convert(grab_result)
                    img = image.GetArray()
                    
                    # ROI 크롭
                    with self.lock:
                        x, y, w, h = self.roi
                    
                    roi_img = img[y:y+h, x:x+w].copy()
                    
                    # YOLO 추론
                    results = self.model(roi_img, verbose=False)
                    
                    # 최신 결과 저장
                    with self.lock:
                        self.latest_results = results
                    
                    # 커스텀 시각화
                    annotated_frame = roi_img.copy()
                    
                    if results[0].boxes is not None:
                        boxes = results[0].boxes.xyxy.cpu().numpy()
                        classes = results[0].boxes.cls.cpu().numpy()
                        confs = results[0].boxes.conf.cpu().numpy()
                        
                        for box, cls, conf in zip(boxes, classes, confs):
                            if conf < 0.8:
                                continue
                            
                            x1, y1, x2, y2 = map(int, box)
                            
                            # 색상 설정
                            if int(cls) == 0:  # back
                                color = (0, 0, 255)  # 붉은색
                            else:  # front
                                color = (0, 255, 0)  # 연두색
                            
                            # 투명 박스
                            overlay = annotated_frame.copy()
                            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
                            annotated_frame = cv2.addWeighted(annotated_frame, 0.7, overlay, 0.3, 0)
                            
                            # 테두리
                            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    
                    with self.lock:
                        self.current_frame = annotated_frame
                
                grab_result.Release()
                
            except Exception as e:
                print(f"캡처 오류: {e}")
                break
        
    def get_frame(self):
        """현재 프레임 반환 (JPEG 인코딩)"""
        with self.lock:
            if self.current_frame is not None:
                ret, buffer = cv2.imencode('.jpg', self.current_frame)
                return buffer.tobytes()
        return None
    
    def stop(self):
        """카메라 정지"""
        self.running = False
        if self.camera:
            self.camera.StopGrabbing()
            self.camera.Close()