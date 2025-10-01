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
        
        # 고정 ROI 설정
        self.roi = (684, 421, 1256, 978)
        
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
            
            cv2.namedWindow('Basler Camera Viewer', cv2.WINDOW_NORMAL)
            
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
                    
                    # ROI 영역만 크롭
                    x, y, w, h = self.roi
                    display_img = img[y:y+h, x:x+w].copy()
                    
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