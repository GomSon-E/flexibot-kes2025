'''
카메라 IP 설정 (Linux) : sudo ip addr add 169.254.1.100/16 dev enp8s0
카메라 IP 설정 (Window) : New-NetIPAddress -InterfaceAlias "이더넷 2" -IPAddress 169.254.1.100 -PrefixLength 16  
'''

from pypylon import pylon
import cv2
import numpy as np
import sys
import time

def camera_to_robot(camera_x, camera_y, camera_angle):
    """카메라 좌표를 로봇 좌표로 변환"""
    
    robot_x =  -0.1134748 * camera_y +  50.126
    robot_y =  -0.1092955 * camera_x +  409.776
    
    
    while camera_angle > 90 or camera_angle < 0 :
        #-45도 이하일 경우 90도 합산
        if camera_angle < 0:
            camera_angle += 90
        #45도 이상일 경우 90도 차감
        else :
            camera_angle -= 90        


    #1차 공식 
    robot_angle = 90 - abs(camera_angle) 
    
    #if camera_angle < 0 :
    #    robot_angle = -robot_angle

    #return robot_x, robot_y, camera_angle
    return robot_x, robot_y, robot_angle


def check_pickable_blocks(img, min_distance=100, padding=20, min_area=5000, max_area=50000):
    """정사각형 블럭 검출 및 회전된 바운딩 박스 (중심점과 각도 시각화)"""
    if img is None:
        print(f"❌ 이미지가 유효하지 않습니다")
        return None, []
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 139, 255, cv2.THRESH_BINARY_INV)
    
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    result = img.copy()
    centers = []
    rotated_rects = []
    angles = []
    
    # 정사각형 필터링
    for cnt in contours:
        area = cv2.contourArea(cnt)
        
        print(f"검출된 윤곽선 면적: {area}")

        # 크기 필터
        if area < min_area or area > max_area:
            continue
        
        # 최소 회전 사각형
        rect = cv2.minAreaRect(cnt)
        (cx, cy), (w, h), angle = rect
        
        # 정사각형 판별
        aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
        if aspect_ratio > 1.15:
            continue
        
        centers.append((cx, cy))
        
        # 패딩 추가
        w_pad = w + 2 * padding
        h_pad = h + 2 * padding
        rotated_rects.append(((cx, cy), (w_pad, h_pad), angle))
        angles.append(angle)
    
    # picking 가능 여부 판단 및 시각화
    for i, ((cx, cy), rect, angle) in enumerate(zip(centers, rotated_rects, angles)):
        min_dist = float('inf')
        for j, (ox, oy) in enumerate(centers):
            if i != j:
                dist = np.sqrt((cx - ox)**2 + (cy - oy)**2)
                min_dist = min(min_dist, dist)
        
        if min_dist >= min_distance:
            color = (0, 255, 0)  # 초록색
            status = "O"
        else:
            color = (0, 0, 255)  # 빨간색
            status = "X"
        
        # 회전된 바운딩 박스
        box = cv2.boxPoints(rect)
        box = np.int32(box)
        cv2.drawContours(result, [box], 0, color, 2)
        
        # 중심점 표시 (더 크게)
        cv2.circle(result, (int(cx), int(cy)), 8, color, -1)
        cv2.circle(result, (int(cx), int(cy)), 10, (255, 255, 255), 2)
        
        # 상태 텍스트 (위쪽)
        cv2.putText(result, status, 
                    (int(cx) - 20, int(cy) - 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
        
        # 좌표 텍스트 (소숫점 3자리)
        coord_text = f"({cx:.3f}, {cy:.3f})"
        cv2.putText(result, coord_text, 
                    (int(cx) - 80, int(cy) - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(result, coord_text, 
                    (int(cx) - 80, int(cy) - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
        
        # 각도 텍스트 (소숫점 3자리)
        angle_text = f"{angle:.3f}"
        cv2.putText(result, angle_text, 
                    (int(cx) - 40, int(cy) + 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(result, angle_text, 
                    (int(cx) - 40, int(cy) + 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
        
        #로봇 좌표 변환
        robot_x,robot_y,robot_angle = camera_to_robot(cx,cy,angle)

        # 콘솔 출력
        print(f"블럭 {i+1}: 위치({cx:.3f}, {cy:.3f}), 각도={angle:.3f}°, 최소거리={min_dist:.1f}px, Picking={status}")
        print(f"로봇 {i+1}: 위치({robot_x:.3f}, {robot_y:.3f}), 각도={robot_angle:.3f}°") 
    
    return result, centers

class BaslerBlockDetector:
    def __init__(self):
        self.camera = None
        self.converter = pylon.ImageFormatConverter()
        self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        
        # 고정 ROI 설정
        self.roi = (684, 421, 1256, 978)
        
        # 검출 파라미터
        self.min_distance = 100
        self.padding = 20
        self.min_area = 28000
        self.max_area = 30000
        
        # 현재 프레임 및 결과 저장
        self.current_frame = None
        self.result_frame = None
        self.show_result = False
        
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
    
    def start_viewing(self):
        """실시간 뷰어 시작"""
        if not self.camera:
            print("카메라가 연결되지 않았습니다.")
            return
        
        try:
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            
            print("\n========================================")
            print("블럭 검출 카메라 뷰어")
            print("========================================")
            print("조작법:")
            print("  d: 현재 프레임 캡처 및 블럭 검출")
            print("  r: 원본 화면으로 복귀")
            print("  s: 결과 이미지 저장")
            print("  q 또는 ESC: 종료")
            print("========================================\n")
            
            window_name = 'Block Detector'
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            
            while self.camera.IsGrabbing():
                grab_result = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                
                if grab_result.GrabSucceeded():
                    image = self.converter.Convert(grab_result)
                    img = image.GetArray()
                    
                    # ROI 영역만 크롭
                    x, y, w, h = self.roi
                    display_img = img[y:y+h, x:x+w].copy()
                    
                    # 현재 프레임 저장
                    self.current_frame = display_img
                    
                    # 결과 표시 모드 확인
                    if self.show_result and self.result_frame is not None:
                        cv2.imshow(window_name, self.result_frame)
                    else:
                        # 안내 텍스트 표시
                        info_img = display_img.copy()
                        cv2.putText(info_img, "Press 'D' to Detect Blocks", 
                                  (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                                  1.5, (0, 255, 0), 3)
                        cv2.imshow(window_name, info_img)
                    
                    # 키 입력 처리
                    key = cv2.waitKey(1) & 0xFF
                    
                    if key == ord('q') or key == 27:
                        print("종료합니다...")
                        break
                    elif key == ord('d'):
                        # 블럭 검출 실행
                        print("\n🔍 블럭 검출 시작...")
                        result, centers = check_pickable_blocks(
                            self.current_frame,
                            self.min_distance,
                            self.padding,
                            self.min_area,
                            self.max_area
                        )
                        
                        if result is not None:
                            self.result_frame = result
                            self.show_result = True
                            print(f"✓ {len(centers)}개 블럭 검출 완료\n")
                        else:
                            print("✗ 블럭 검출 실패\n")
                    
                    elif key == ord('r'):
                        # 원본 화면으로 복귀
                        self.show_result = False
                        print("원본 화면으로 복귀\n")
                    
                    elif key == ord('s'):
                        # 결과 저장
                        if self.show_result and self.result_frame is not None:
                            filename = f"block_result_{int(time.time())}.png"
                            cv2.imwrite(filename, self.result_frame)
                            print(f"✓ 결과 이미지 저장: {filename}\n")
                        else:
                            filename = f"block_capture_{int(time.time())}.png"
                            cv2.imwrite(filename, self.current_frame)
                            print(f"✓ 원본 이미지 저장: {filename}\n")
                
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
    detector = BaslerBlockDetector()
    
    if detector.connect_camera():
        detector.start_viewing()
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()