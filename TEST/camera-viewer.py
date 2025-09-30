'''
카메라 IP 설정 : sudo ip addr add 169.254.1.100/16 dev enp8s0
'''

from pypylon import pylon
import cv2
import numpy as np
import sys

class BaslerViewer:
    def __init__(self):
        self.camera = None
        self.converter = pylon.ImageFormatConverter()
        self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        
        # ROI 관련 변수
        self.roi = None  # (x, y, width, height)
        self.drawing = False
        self.start_point = None
        self.temp_roi = None
        
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
    
    def mouse_callback(self, event, x, y, flags, param):
        """마우스 이벤트 처리 - ROI 선택"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start_point = (x, y)
            
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.temp_roi = (self.start_point[0], self.start_point[1], 
                               x - self.start_point[0], y - self.start_point[1])
                
        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            if self.start_point:
                x1, y1 = self.start_point
                w = x - x1
                h = y - y1
                
                # 음수 너비/높이 보정
                if w < 0:
                    x1 = x
                    w = abs(w)
                if h < 0:
                    y1 = y
                    h = abs(h)
                    
                self.roi = (x1, y1, w, h)
                self.temp_roi = None
                print(f"ROI 설정: x={x1}, y={y1}, w={w}, h={h}")
    
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
    
    def start_viewing(self):
        """실시간 뷰어 시작"""
        if not self.camera:
            print("카메라가 연결되지 않았습니다.")
            return
        
        try:
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            print("\n카메라 뷰어 시작...")
            print("조작법:")
            print("  q 또는 ESC: 종료")
            print("  s: 스크린샷 저장")
            print("  f: FPS 표시 토글")
            print("  r: ROI 초기화")
            print("  마우스 드래그: ROI 선택")
            
            cv2.namedWindow('Basler Camera Viewer', cv2.WINDOW_NORMAL)
            cv2.setMouseCallback('Basler Camera Viewer', self.mouse_callback)
            
            show_fps = False
            frame_count = 0
            fps = 0
            
            import time
            start_time = time.time()
            
            while self.camera.IsGrabbing():
                grab_result = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                
                if grab_result.GrabSucceeded():
                    image = self.converter.Convert(grab_result)
                    img = image.GetArray()
                    display_img = img.copy()
                    
                    # FPS 계산
                    frame_count += 1
                    if time.time() - start_time > 1.0:
                        fps = frame_count / (time.time() - start_time)
                        frame_count = 0
                        start_time = time.time()
                    
                    # 저장된 ROI 그리기 (초록색)
                    if self.roi:
                        x, y, w, h = self.roi
                        cv2.rectangle(display_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        
                        # ROI 작은 화면 표시
                        roi_img = img[y:y+h, x:x+w]
                        if roi_img.size > 0:
                            small_h, small_w = 150, 150
                            roi_resized = cv2.resize(roi_img, (small_w, small_h))
                            
                            # 오른쪽 상단에 배치
                            y_offset = 10
                            x_offset = display_img.shape[1] - small_w - 10
                            
                            # 테두리
                            cv2.rectangle(display_img, 
                                        (x_offset-2, y_offset-2), 
                                        (x_offset+small_w+2, y_offset+small_h+2), 
                                        (0, 255, 0), 2)
                            
                            # ROI 이미지 삽입
                            display_img[y_offset:y_offset+small_h, 
                                      x_offset:x_offset+small_w] = roi_resized
                    
                    # 임시 ROI 그리기 (노란색)
                    if self.temp_roi:
                        x, y, w, h = self.temp_roi
                        cv2.rectangle(display_img, (x, y), (x + w, y + h), (0, 255, 255), 2)
                    
                    # FPS 표시
                    if show_fps:
                        cv2.putText(display_img, f"FPS: {fps:.1f}", (10, 30),
                                  cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    # ROI 좌표 표시
                    if self.roi:
                        x, y, w, h = self.roi
                        roi_text = f"ROI: x={x}, y={y}, w={w}, h={h}"
                        cv2.putText(display_img, roi_text, (10, display_img.shape[0] - 20),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    cv2.imshow('Basler Camera Viewer', display_img)
                    
                    # 키 입력 처리
                    key = cv2.waitKey(1) & 0xFF
                    
                    if key == ord('q') or key == 27:
                        print("종료합니다...")
                        break
                    elif key == ord('s'):
                        filename = f"basler_capture_{int(time.time())}.png"
                        cv2.imwrite(filename, img)
                        print(f"저장됨: {filename}")
                    elif key == ord('f'):
                        show_fps = not show_fps
                        print(f"FPS 표시: {'ON' if show_fps else 'OFF'}")
                    elif key == ord('r'):
                        self.roi = None
                        print("ROI 초기화됨")
                
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
        viewer.set_camera_parameters()
        viewer.start_viewing()
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()