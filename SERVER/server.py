# SERVER/server.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import asyncio
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# 컨트롤러 임포트
from camera_controller import CameraController
from feeder_controller import FeederController
from cylinder_controller import CylinderController
from robot_controller import RobotController

# ===== 요청/응답 모델 =====
class ROIRequest(BaseModel):
    x: int
    y: int

class LightRequest(BaseModel):
    on: bool
    brightness: int

class CylinderRequest(BaseModel):
    cylinder_num: int  # 0, 1, 2, 3
    action: str  # "on", "off", "pulse"
    on_time: Optional[float] = 1.0
    off_time: Optional[float] = 1.0

class RobotTaskRequest(BaseModel):
    task_num: int
    x: Optional[int] = 0
    y: Optional[int] = 0
    angle: Optional[int] = 0
    plate_seq: Optional[int] = 0

class SequenceStep(BaseModel):
    type: str  # "cylinder", "robot", "light", "wait", "camera"
    params: Dict[str, Any]

class SequenceRequest(BaseModel):
    name: str
    steps: List[SequenceStep]

# ===== 통합 시스템 클래스 =====
class IntegratedSystem:
    def __init__(self):
        self.camera = CameraController()
        self.feeder = FeederController()
        self.cylinder = CylinderController()
        self.robot = RobotController()
        self.is_initialized = False
        
    async def initialize(self):
        """시스템 초기화"""
        print("=" * 60)
        print("시스템 초기화 시작...")
        print("=" * 60)
        
        # 1. 카메라 연결
        if self.camera.connect_camera():
            self.camera.start_capture()
            print("✓ 카메라 시작")
        else:
            print("⚠️ 카메라 없이 시작")
        
        # 2. 피더 연결 및 조명 켜기
        if self.feeder.connect():
            print("✓ 피더 연결")
            # 조명 자동 켜기 (밝기 10%)
            if self.feeder.set_light(True, 10):
                print("✓ 피더 조명 ON (10%)")
            else:
                print("⚠️ 피더 조명 제어 실패")
        else:
            print("⚠️ 피더 없이 시작")
            
        # 3. 실린더 연결 및 초기화
        if self.cylinder.connect():
            print("✓ 실린더 연결")
            # 모든 실린더 OFF 상태로 초기화
            for i in range(4):
                getattr(self.cylinder, f'cylinder_{i}_off')()
            print("✓ 실린더 초기화 완료 (모두 OFF)")
        else:
            print("⚠️ 실린더 없이 시작")
            
        # 4. 로봇 연결 및 초기화
        if self.robot.connect():
            print("✓ 로봇 연결")
            
            # Task 0: 로봇 초기화
            print("\n[자동 실행] Task 0: 로봇 초기화")
            response0 = self.robot.robot_init()
            if response0:
                print(f"✓ Task 0 완료: {response0}")
                
                print("\n[자동 실행] Task 1: 툴 플레이트 초기화")
                response1 = self.robot.tool_plate_init()
                if response1:
                    print(f"✓ Task 1 완료: {response1}")
                else:
                    print("⚠️ Task 1 응답 없음")
            else:
                print("⚠️ Task 0 응답 없음")
        else:
            print("⚠️ 로봇 없이 시작")
        
        self.is_initialized = True
        print("=" * 60)
        print("시스템 초기화 완료")
        print("=" * 60)
    
    async def shutdown(self):
        """시스템 종료"""
        print("\n시스템 종료 중...")
        
        # 조명 끄기
        if self.feeder.client:
            self.feeder.set_light(False, 0)
            print("✓ 피더 조명 OFF")
        
        # 실린더 모두 OFF
        if self.cylinder.connected:
            for i in range(4):
                getattr(self.cylinder, f'cylinder_{i}_off')()
            print("✓ 실린더 모두 OFF")
        
        self.camera.stop()
        self.feeder.disconnect()
        self.cylinder.disconnect()
        self.robot.disconnect()
        print("✓ 시스템 종료 완료")

# 시스템 인스턴스
system = IntegratedSystem()

# ===== FastAPI 앱 설정 =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    await system.initialize()
    yield
    await system.shutdown()

app = FastAPI(
    title="레고 & 블럭 통합 제어 시스템",
    version="1.0.0",
    lifespan=lifespan
)

# ===== 비디오 스트리밍 =====
def generate_frames():
    """비디오 스트림 생성"""
    while True:
        frame = system.camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            import time
            time.sleep(0.1)

@app.get("/video_feed")
async def video_feed():
    """비디오 스트림"""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

# ===== 카메라 제어 API =====
@app.post("/api/set_roi")
async def set_roi(req: ROIRequest):
    """ROI 위치 변경"""
    system.camera.set_roi(req.x, req.y)
    return {"status": "ok", "x": req.x, "y": req.y}

@app.get("/api/get_centroids")
async def get_centroids():
    """검출된 객체 중심점 반환"""
    centroids = system.camera.get_front_centroids()
    return {
        "status": "ok",
        "count": len(centroids),
        "centroids": centroids
    }

# ===== 조명 제어 API =====
@app.post("/api/light_control")
async def light_control(req: LightRequest):
    """조명 제어"""
    success = system.feeder.set_light(req.on, req.brightness)
    return {
        "status": "ok" if success else "error",
        "on": req.on,
        "brightness": req.brightness
    }

# ===== 실린더 제어 API =====
@app.post("/api/cylinder_control")
async def cylinder_control(req: CylinderRequest):
    """실린더 제어"""
    if not system.cylinder.connected:
        raise HTTPException(status_code=503, detail="실린더 미연결")
    
    try:
        if req.action == "on":
            getattr(system.cylinder, f'cylinder_{req.cylinder_num}_on')()
        elif req.action == "off":
            getattr(system.cylinder, f'cylinder_{req.cylinder_num}_off')()
        elif req.action == "pulse":
            getattr(system.cylinder, f'cylinder_{req.cylinder_num}_pulse')(
                req.on_time, req.off_time
            )
        else:
            raise ValueError(f"Invalid action: {req.action}")
        
        return {
            "status": "ok",
            "cylinder": req.cylinder_num,
            "action": req.action
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== 로봇 제어 API =====
@app.post("/api/robot_task")
async def robot_task(req: RobotTaskRequest):
    """로봇 작업 실행"""
    if not system.robot.connected:
        raise HTTPException(status_code=503, detail="로봇 미연결")
    
    response = system.robot.send_task(
        req.task_num,
        req.x,
        req.y,
        req.angle,
        req.plate_seq
    )
    
    if response:
        return {
            "status": "ok",
            "task": req.task_num,
            "response": response
        }
    else:
        raise HTTPException(status_code=500, detail="로봇 응답 없음")

@app.post("/api/robot_init")
async def robot_init():
    """로봇 초기화"""
    if not system.robot.connected:
        raise HTTPException(status_code=503, detail="로봇 미연결")
    
    response = system.robot.robot_init()
    return {"status": "ok" if response else "error", "response": response}

# ===== 시퀀스 실행 API =====
@app.post("/api/execute_sequence")
async def execute_sequence(req: SequenceRequest):
    """복합 작업 시퀀스 실행"""
    results = []
    
    print(f"\n시퀀스 실행: {req.name}")
    print("=" * 40)
    
    for i, step in enumerate(req.steps):
        print(f"Step {i+1}: {step.type}")
        
        try:
            if step.type == "cylinder":
                cylinder_num = step.params['cylinder']
                action = step.params['action']
                
                if action == "on":
                    getattr(system.cylinder, f'cylinder_{cylinder_num}_on')()
                elif action == "off":
                    getattr(system.cylinder, f'cylinder_{cylinder_num}_off')()
                elif action == "pulse":
                    on_time = step.params.get('on_time', 1.0)
                    off_time = step.params.get('off_time', 1.0)
                    getattr(system.cylinder, f'cylinder_{cylinder_num}_pulse')(
                        on_time, off_time
                    )
                
                results.append({
                    "step": i+1,
                    "type": "cylinder",
                    "result": f"Cylinder {cylinder_num} {action}"
                })
                
            elif step.type == "robot":
                task_num = step.params['task']
                x = step.params.get('x', 0)
                y = step.params.get('y', 0)
                angle = step.params.get('angle', 0)
                plate_seq = step.params.get('plate_seq', 0)
                
                response = system.robot.send_task(task_num, x, y, angle, plate_seq)
                results.append({
                    "step": i+1,
                    "type": "robot",
                    "result": response
                })
                
            elif step.type == "light":
                on = step.params['on']
                brightness = step.params.get('brightness', 0)
                system.feeder.set_light(on, brightness)
                
                results.append({
                    "step": i+1,
                    "type": "light",
                    "result": f"Light {'on' if on else 'off'}, brightness: {brightness}"
                })
                
            elif step.type == "wait":
                duration = step.params['duration']
                await asyncio.sleep(duration)
                
                results.append({
                    "step": i+1,
                    "type": "wait",
                    "result": f"Waited {duration} seconds"
                })
                
            elif step.type == "camera":
                if step.params.get('action') == 'capture':
                    centroids = system.camera.get_front_centroids()
                    results.append({
                        "step": i+1,
                        "type": "camera",
                        "result": f"Detected {len(centroids)} objects",
                        "data": centroids
                    })
                    
        except Exception as e:
            results.append({
                "step": i+1,
                "type": step.type,
                "error": str(e)
            })
            print(f"  ✗ 오류: {e}")
            continue
    
    print("=" * 40)
    print("시퀀스 완료\n")
    
    return {
        "status": "completed",
        "sequence": req.name,
        "results": results
    }

# ===== 시스템 상태 API =====
@app.get("/api/system_status")
async def get_system_status():
    """전체 시스템 상태 확인"""
    return {
        "initialized": system.is_initialized,
        "modules": {
            "cylinder": {
                "connected": system.cylinder.connected,
                "status": "online" if system.cylinder.connected else "offline"
            },
            "robot": {
                "connected": system.robot.connected,
                "status": "online" if system.robot.connected else "offline",
                "host": system.robot.host if system.robot.connected else None
            },
            "camera": {
                "connected": system.camera.camera is not None,
                "status": "online" if system.camera.camera else "offline",
                "roi": system.camera.roi if system.camera.camera else None
            },
            "feeder": {
                "connected": system.feeder.client is not None,
                "status": "online" if system.feeder.client else "offline"
            }
        }
    }

# ===== 웹 페이지 라우팅 =====
@app.get("/")
async def root():
    """메인 페이지"""
    html_path = os.path.join(os.path.dirname(__file__), "..", "UI", "index.html")
    if not os.path.exists(html_path):
        return HTMLResponse(content="<h1>UI 파일을 찾을 수 없습니다</h1>", status_code=404)
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/camera")
async def camera_page():
    """카메라 페이지"""
    html_path = os.path.join(os.path.dirname(__file__), "..", "UI", "camera.html")
    if not os.path.exists(html_path):
        return HTMLResponse(content="<h1>카메라 페이지를 찾을 수 없습니다</h1>", status_code=404)
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/control")
async def control_page():
    """제어 페이지"""
    html_path = os.path.join(os.path.dirname(__file__), "..", "UI", "control.html")
    if not os.path.exists(html_path):
        return HTMLResponse(content="<h1>제어 페이지를 찾을 수 없습니다</h1>", status_code=404)
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/api/test_camera")
async def test_camera():
    frame = system.camera.get_frame()
    return {
        "has_frame": frame is not None,
        "frame_size": len(frame) if frame else 0,
        "camera_running": system.camera.running
    }

# ===== 정적 파일 서빙 =====
img_dir = os.path.join(os.path.dirname(__file__), "..", "UI", "img")
if os.path.exists(img_dir):
    app.mount("/img", StaticFiles(directory=img_dir), name="img")

css_dir = os.path.join(os.path.dirname(__file__), "..", "UI", "css")
if os.path.exists(css_dir):
    app.mount("/css", StaticFiles(directory=css_dir), name="css")

js_dir = os.path.join(os.path.dirname(__file__), "..", "UI", "js")
if os.path.exists(js_dir):
    app.mount("/js", StaticFiles(directory=js_dir), name="js")

# ===== 메인 실행 =====
if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 60)
    print("레고 & 블럭 통합 제어 시스템")
    print("=" * 60)
    print("서버 시작: http://localhost:8000")
    print("API 문서: http://localhost:8000/docs")
    print("=" * 60 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )