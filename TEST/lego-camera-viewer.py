'''
카메라 IP 설정 (Linux) : sudo ip addr add 169.254.1.100/16 dev enp8s0
카메라 IP 설정 (Window) : New-NetIPAddress -InterfaceAlias "이더넷 2" -IPAddress 169.254.1.100 -PrefixLength 16  
'''

from pypylon import pylon
import cv2
import numpy as np
from ultralytics import YOLO
import sys
import time

class BaslerViewer:
    def __init__(self):
        self.camera = None
        self.converter = pylon.ImageFormatConverter()
        self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        
        # 고정 ROI 설정
        self.roi = (684, 421, 1256, 978)
        
        # 마우스 클릭 좌표 저장
        self.last_click = None
        self.show_crosshair = False
        
        # 현재 프레임 저장
        self.current_frame = None
        
        # YOLO 모델 로드
        self.model = YOLO('../MODEL/final_lego_model.pt')
        print("✓ YOLO 모델 로드 완료")
        
        # 검출된 객체 저장
        self.detections = []
        
    def detect_and_show_centroids(self, img):
        """YOLO로 객체 검출하고 중심 좌표 표시"""
        # YOLO 추론
        results = self.model(img, verbose=False)
        
        annotated = img.copy()
        self.detections = []
        
        if results[0].boxes is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            classes = results[0].boxes.cls.cpu().numpy()
            confs = results[0].boxes.conf.cpu().numpy()
            
            for i, (box, cls, conf) in enumerate(zip(boxes, classes, confs)):
                if conf < 0.8:
                    continue
                
                x1, y1, x2, y2 = box
                
                # 소수점 중심 좌표
                center_x = (x1 + x2) / 2.0
                center_y = (y1 + y2) / 2.0
                
                # 색상 설정
                if int(cls) == 0:  # back
                    color = (0, 0, 255)
                    label = "back"
                else:  # front
                    color = (0, 255, 0)
                    label = "front"
                
                # 검출 정보 저장
                self.detections.append({
                    'center': (center_x, center_y),
                    'label': label,
                    'color': color
                })
                
                # 바운딩 박스
                cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                
                # 중심점 표시
                cv2.circle(annotated, (int(center_x), int(center_y)), 5, color, -1)
            
            print(f"\n✓ {len(self.detections)}개 객체 검출됨 (클릭하여 좌표 확인)")
        
        return annotated
        
    def mouse_callback(self, event, x, y, flags, param):
        """마우스 이벤트 콜백 함수"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # 클릭 위치에 가장 가까운 검출 객체 찾기
            min_dist = float('inf')
            closest = None
            
            for detection in self.detections:
                center_x, center_y = detection['center']
                dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                if dist < min_dist:
                    min_dist = dist
                    closest = detection
            
            if closest and min_dist < 50:  # 50픽셀 이내
                center_x, center_y = closest['center']
                original_x = self.roi[0] + center_x
                original_y = self.roi[1] + center_y
                
                print(f"\n=== 클릭한 객체 ({closest['label']}) ===")
                print(f"{original_x:.3f}\t{original_y:.3f}")
                print(f"원본 좌표: ({original_x:.3f}, {original_y:.3f})")
                print(f"ROI 좌표: ({center_x:.3f}, {center_y:.3f})")
                
                self.last_click = (int(center_x), int(center_y))
                self.show_crosshair = True
            else:
                print("\n클릭 위치 근처에 객체가 없습니다.")
                
        elif event == cv2.EVENT_RBUTTONDOWN:
            self.show_crosshair = False
            print("\n크로스헤어 제거됨")
            
    def connect_camera(self):
        """카메라 연결"""
        try:
            tl_factory = pylon.TlFactory.GetInstance()
            devices = tl_factory.EnumerateDevices()
            
            if len(devices) == 0:
                print("연결된 카메라가 없습니다.")
                return False
            
            print(f"발견된 카메라: {len(devices)}대")
            for i, device in enumerate(devices):
                print(f"{i}: {device.GetFriendlyName()}")
            
            self.camera = pylon.InstantCamera(tl_factory.CreateFirstDevice())
            self.camera.Open()
            
            print(f"\n연결됨: {self.camera.GetDeviceInfo().GetModelName()}")
            print(f"시리얼 번호: {self.camera.GetDeviceInfo().GetSerialNumber()}")
            
            return True
            
        except Exception as e:
            print(f"카메라 연결 실패: {e}")
            return False
    
    def set_camera_parameters(self):
        """카메라 파라미터 설정"""
        try:
            ## 자동 노출 설정
            # self.camera.ExposureAuto.SetValue('Continuous')
            
            ## 수동 노출 설정 (마이크로초 단위)
            # self.camera.ExposureTime.SetValue(10000)
            
            ## 게인 설정
            # self.camera.Gain.SetValue(0)
            
            pass
        except Exception as e:
            print(f"파라미터 설정 경고: {e}")
    
    def draw_overlay(self, img, mouse_pos=None):
        """이미지에 오버레이 그리기"""
        overlay = img.copy()
        
        # 크로스헤어 그리기
        if self.show_crosshair and self.last_click:
            x, y = self.last_click
            # 십자선
            cv2.line(overlay, (x, 0), (x, img.shape[0]), (0, 255, 0), 1)
            cv2.line(overlay, (0, y), (img.shape[1], y), (0, 255, 0), 1)
            
            # 클릭 위치에 작은 원
            cv2.circle(overlay, (x, y), 5, (0, 0, 255), 2)
            
            # 좌표 텍스트 표시
            original_x = self.roi[0] + x
            original_y = self.roi[1] + y
            text = f"Original: ({original_x}, {original_y})"
            cv2.putText(overlay, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.7, (0, 255, 0), 2)
        
        # 현재 마우스 위치 표시 (옵션)
        if mouse_pos:
            mx, my = mouse_pos
            if 0 <= mx < img.shape[1] and 0 <= my < img.shape[0]:
                # 마우스 위치에 작은 십자 표시
                cv2.drawMarker(overlay, (mx, my), (255, 255, 0), 
                             cv2.MARKER_CROSS, 10, 1)
        
        return overlay
    
    def start_viewing(self):
        """실시간 뷰어 시작"""
        if not self.camera:
            print("카메라가 연결되지 않았습니다.")
            return
        
        try:
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            
            print("\n========================================")
            print("카메라 뷰어 시작...")
            print("========================================")
            print("조작법:")
            print("  좌클릭: 좌표 출력 및 크로스헤어")
            print("  우클릭: 크로스헤어 제거")
            print("  d: YOLO 검출 및 좌표 출력")
            print("  s: 스크린샷 저장")
            print("  c: 좌표 정보 초기화")
            print("  q 또는 ESC: 종료")
            print("========================================\n")
            
            window_name = 'Basler Camera Viewer'
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.setMouseCallback(window_name, self.mouse_callback)
            
            while self.camera.IsGrabbing():
                grab_result = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                
                if grab_result.GrabSucceeded():
                    image = self.converter.Convert(grab_result)
                    img = image.GetArray()
                    
                    # ROI 영역만 크롭
                    x, y, w, h = self.roi
                    display_img = img[y:y+h, x:x+w].copy()
                    
                    # 현재 프레임 저장 (서브픽셀 계산용)
                    self.current_frame = display_img
                    
                    # 오버레이 그리기
                    display_img = self.draw_overlay(display_img)
                    
                    cv2.imshow(window_name, display_img)
                    
                    # 키 입력 처리
                    key = cv2.waitKey(1) & 0xFF
                    
                    if key == ord('q') or key == 27:
                        print("종료합니다...")
                        break
                    elif key == ord('d'):
                        # YOLO 검출 및 좌표 출력
                        display_img = self.detect_and_show_centroids(display_img)
                    elif key == ord('s'):
                        # 전체 이미지 저장
                        filename = f"basler_capture_{int(time.time())}.png"
                        cv2.imwrite(filename, img)
                        print(f"전체 이미지 저장됨: {filename}")
                        
                        # ROI 이미지도 저장
                        roi_filename = f"basler_roi_{int(time.time())}.png"
                        cv2.imwrite(roi_filename, display_img)
                        print(f"ROI 이미지 저장됨: {roi_filename}")
                    elif key == ord('c'):
                        # 좌표 정보 초기화
                        self.show_crosshair = False
                        self.last_click = None
                        print("\n좌표 정보 초기화됨")
                
                grab_result.Release()
            
        except KeyboardInterrupt:
            print("\n사용자에 의해 중단됨")
        except Exception as e:
            print(f"오류 발생: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """리소스 정리"""
        if self.camera:
            self.camera.StopGrabbing()
            self.camera.Close()
        cv2.destroyAllWindows()
        print("카메라 연결 해제됨")

def main():
    viewer = BaslerViewer()
    
    if viewer.connect_camera():
        viewer.start_viewing()
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()