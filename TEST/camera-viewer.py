"""
Basler Camera Viewer using pypylon
Ubuntu 22.04 / Pop OS 호환
"""

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
            # 사용 가능한 카메라 찾기
            tl_factory = pylon.TlFactory.GetInstance()
            devices = tl_factory.EnumerateDevices()
            
            if len(devices) == 0:
                print("연결된 카메라가 없습니다.")
                return False
            
            print(f"발견된 카메라: {len(devices)}대")
            for i, device in enumerate(devices):
                print(f"{i}: {device.GetFriendlyName()}")
            
            # 첫 번째 카메라 연결
            self.camera = pylon.InstantCamera(tl_factory.CreateFirstDevice())
            self.camera.Open()
            
            print(f"\n연결됨: {self.camera.GetDeviceInfo().GetModelName()}")
            print(f"시리얼 번호: {self.camera.GetDeviceInfo().GetSerialNumber()}")
            
            return True
            
        except Exception as e:
            print(f"카메라 연결 실패: {e}")
            return False
    
    def set_camera_parameters(self):
        """카메라 파라미터 설정 (선택사항)"""
        try:
            # 자동 노출 설정
            # self.camera.ExposureAuto.SetValue('Continuous')
            
            # 수동 노출 설정 예시 (마이크로초 단위)
            # self.camera.ExposureTime.SetValue(10000)
            
            # 게인 설정
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
            
            show_fps = False
            frame_count = 0
            fps = 0
            
            import time
            start_time = time.time()
            
            while self.camera.IsGrabbing():
                grab_result = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                
                if grab_result.GrabSucceeded():
                    # 이미지 변환
                    image = self.converter.Convert(grab_result)
                    img = image.GetArray()
                    
                    # FPS 계산
                    frame_count += 1
                    if time.time() - start_time > 1.0:
                        fps = frame_count / (time.time() - start_time)
                        frame_count = 0
                        start_time = time.time()
                    
                    # FPS 표시
                    if show_fps:
                        cv2.putText(img, f"FPS: {fps:.1f}", (10, 30),
                                  cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    # 이미지 표시
                    cv2.imshow('Basler Camera Viewer', img)
                    
                    # 키 입력 처리
                    key = cv2.waitKey(1) & 0xFF
                    
                    if key == ord('q') or key == 27:  # q 또는 ESC
                        print("종료합니다...")
                        break
                    elif key == ord('s'):  # 스크린샷
                        filename = f"basler_capture_{int(time.time())}.png"
                        cv2.imwrite(filename, img)
                        print(f"저장됨: {filename}")
                    elif key == ord('f'):  # FPS 토글
                        show_fps = not show_fps
                        print(f"FPS 표시: {'ON' if show_fps else 'OFF'}")
                
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