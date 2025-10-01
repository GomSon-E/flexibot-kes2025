from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pypylon import pylon
from pymodbus.client import ModbusTcpClient
import cv2
import numpy as np
from ultralytics import YOLO
import threading
import os
from pydantic import BaseModel

# 요청 모델
class ROIRequest(BaseModel):
    x: int
    y: int

class LightRequest(BaseModel):
    on: bool
    brightness: int

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if camera.connect_camera():
        camera.start_capture()
    else:
        print("⚠️ 카메라 없이 시작")
    
    # 피더 연결
    if feeder.connect():
        print("✓ 피더 연결 완료")
    else:
        print("⚠️ 피더 없이 시작")
    
    yield
    
    # Shutdown
    camera.stop()
    feeder.disconnect()

app = FastAPI(lifespan=lifespan)

class FeederController:
    def __init__(self, ip='192.168.1.100', port=502):
        self.ip = ip
        self.port = port
        self.client = None
        
    def connect(self):
        """피더 연결"""
        try:
            self.client = ModbusTcpClient(self.ip, port=self.port)
            return self.client.connect()
        except Exception as e:
            print(f"피더 연결 실패: {e}")
            return False
    
    def set_light(self, on: bool, brightness: int = 0):
        """
        조명 제어
        on: True/False
        brightness: 0-100 (실제로는 0-1000으로 변환)
        """
        if not self.client:
            return False
        
        try:
            # P0.10: 조명 스위치
            self.client.write_register(10, 1 if on else 0)
            
            if on:
                # P0.11: 밝기 (0-100% -> 0-1000)
                brightness_value = int(brightness * 10)
                self.client.write_register(11, brightness_value)
            
            return True
        except Exception as e:
            print(f"조명 제어 실패: {e}")
            return False
    
    def disconnect(self):
        """연결 종료"""
        if self.client:
            self.client.close()

class CameraInference:
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
        
    def set_roi(self, x: int, y: int):
        """ROI 위치 변경"""
        with self.lock:
            self.roi[0] = x
            self.roi[1] = y
        print(f"✓ ROI 변경: ({x}, {y})")
        
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
        """현재 프레임 반환"""
        with self.lock:
            if self.current_frame is not None:
                ret, buffer = cv2.imencode('.jpg', self.current_frame)
                return buffer.tobytes()
        return None
    
    def stop(self):
        """정지"""
        self.running = False
        if self.camera:
            self.camera.StopGrabbing()
            self.camera.Close()

# 전역 인스턴스
camera = CameraInference()
feeder = FeederController()

def generate_frames():
    """프레임 생성기"""
    while True:
        frame = camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.get("/video_feed")
async def video_feed():
    """비디오 스트림"""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/")
async def root():
    """메인 페이지"""
    html_path = os.path.join(os.path.dirname(__file__), "..", "UI", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/camera")
async def camera_page():
    """카메라 페이지"""
    html_path = os.path.join(os.path.dirname(__file__), "..", "UI", "camera.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/control")
async def control_page():
    """제어 페이지"""
    html_path = os.path.join(os.path.dirname(__file__), "..", "UI", "control.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.post("/api/set_roi")
async def set_roi(req: ROIRequest):
    """ROI 위치 변경"""
    camera.set_roi(req.x, req.y)
    return {"status": "ok", "x": req.x, "y": req.y}

@app.post("/api/light_control")
async def light_control(req: LightRequest):
    """조명 제어"""
    success = feeder.set_light(req.on, req.brightness)
    return {
        "status": "ok" if success else "error",
        "on": req.on,
        "brightness": req.brightness
    }

# 정적 파일
img_dir = os.path.join(os.path.dirname(__file__), "..", "UI", "img")
if os.path.exists(img_dir):
    app.mount("/img", StaticFiles(directory=img_dir), name="img")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)