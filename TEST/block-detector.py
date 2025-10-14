import cv2
import numpy as np
from pypylon import pylon

class BlockCenterDetector:
    def __init__(self):
        self.camera = None
        self.converter = pylon.ImageFormatConverter()
        self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        
        # ROI 설정 (기존 설정 사용)
        self.roi = (684, 421, 1256, 978)
        
        # 블럭 검출 파라미터
        self.min_area = 1000      # 최소 면적
        self.max_area = 100000    # 최대 면적
        self.aspect_ratio_min = 0.6  # 최소 종횡비
        self.aspect_ratio_max = 1.7  # 최대 종횡비
    
    def connect_camera(self):
        """카메라 연결"""
        try:
            tl_factory = pylon.TlFactory.GetInstance()
            devices = tl_factory.EnumerateDevices()
            
            if len(devices) == 0:
                print("✗ 연결된 카메라가 없습니다.")
                return False
            
            self.camera = pylon.InstantCamera(tl_factory.CreateFirstDevice())
            self.camera.Open()
            
            print(f"✓ 카메라 연결: {self.camera.GetDeviceInfo().GetModelName()}")
            return True
            
        except Exception as e:
            print(f"✗ 카메라 연결 실패: {e}")
            return False
    
    def capture_image(self):
        """이미지 캡처"""
        if not self.camera:
            print("✗ 카메라가 연결되지 않았습니다.")
            return None
        
        try:
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            grab_result = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            
            if grab_result.GrabSucceeded():
                image = self.converter.Convert(grab_result)
                img = image.GetArray()
                
                # ROI 크롭
                x, y, w, h = self.roi
                roi_img = img[y:y+h, x:x+w].copy()
                
                grab_result.Release()
                self.camera.StopGrabbing()
                
                return roi_img
            
            return None
            
        except Exception as e:
            print(f"✗ 캡처 실패: {e}")
            return None
    
    def detect_block_centers(self, img):
        """
        블럭 중심점 검출 (개선 버전)
        
        Args:
            img: 입력 이미지 (컬러 또는 흑백)
        
        Returns:
            centers: [(x1, y1), (x2, y2), ...] 중심점 좌표 리스트
            debug_img: 시각화된 디버그 이미지
            binary: 이진화 이미지
        """
        # 1. 흑백 변환
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # 2. 블러링
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 3. 적응형 이진화
        binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 21, 5)
        
        # 4. 모폴로지 연산 (강화)
        kernel_large = np.ones((15, 15), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_large, iterations=2)
        
        kernel_dilate = np.ones((5, 5), np.uint8)
        binary = cv2.dilate(binary, kernel_dilate, iterations=1)
        
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_large, iterations=1)
        
        # 5. 윤곽선 검출
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 디버그용 이미지
        debug_img = img.copy() if len(img.shape) == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        
        centers = []
        
        for contour in contours:
            # 면적 필터링
            area = cv2.contourArea(contour)
            if area < self.min_area or area > self.max_area:
                continue
            
            # minAreaRect로 회전된 사각형 검출
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            
            # 중심점, 크기, 각도
            center_x, center_y = rect[0]
            width, height = rect[1]
            angle = rect[2]
            
            # 종횡비 검증 (정사각형에 가까운지)
            if width == 0 or height == 0:
                continue
            
            aspect_ratio = max(width, height) / min(width, height)
            if aspect_ratio < self.aspect_ratio_min or aspect_ratio > self.aspect_ratio_max:
                continue
            
            # 중심점 저장
            cx, cy = int(center_x), int(center_y)
            centers.append((cx, cy))
            
            # 시각화
            # 회전된 사각형 그리기 (초록색)
            cv2.drawContours(debug_img, [box], 0, (0, 255, 0), 3)
            
            # 중심점 표시 (빨간 원)
            cv2.circle(debug_img, (cx, cy), 7, (0, 0, 255), -1)
            
            # 중심점 좌표 텍스트
            cv2.putText(debug_img, f"({cx},{cy})", 
                       (cx + 10, cy - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            
            # 번호 표시
            cv2.putText(debug_img, f"#{len(centers)}", 
                       (cx - 20, cy + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # 각도 표시 (선택)
            cv2.putText(debug_img, f"{int(angle)}°", 
                       (cx - 15, cy + 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        return centers, debug_img, binary
    
    def run_live(self):
        """실시간 검출"""
        if not self.camera:
            print("✗ 카메라가 연결되지 않았습니다.")
            return
        
        try:
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            print("\n✓ 실시간 검출 시작")
            print("조작법:")
            print("  스페이스바: 현재 프레임 중심점 출력")
            print("  q 또는 ESC: 종료\n")
            
            cv2.namedWindow('Block Center Detection', cv2.WINDOW_NORMAL)
            
            while self.camera.IsGrabbing():
                grab_result = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                
                if grab_result.GrabSucceeded():
                    image = self.converter.Convert(grab_result)
                    img = image.GetArray()
                    
                    # ROI 크롭
                    x, y, w, h = self.roi
                    roi_img = img[y:y+h, x:x+w].copy()
                    
                    # 중심점 검출
                    centers, debug_img, binary = self.detect_block_centers(roi_img)
                    
                    # 상단에 정보 표시
                    info_text = f"Blocks: {len(centers)}"
                    cv2.putText(debug_img, info_text, (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                    
                    # 화면 분할 (원본 + 이진화)
                    binary_bgr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
                    display = np.hstack([debug_img, binary_bgr])
                    
                    cv2.imshow('Block Center Detection', display)
                    
                    # 키 입력 처리
                    key = cv2.waitKey(1) & 0xFF
                    
                    if key == ord('q') or key == 27:
                        print("\n종료합니다...")
                        break
                    elif key == ord(' '):
                        print(f"\n[검출된 블럭 중심점 - 총 {len(centers)}개]")
                        for i, (cx, cy) in enumerate(centers):
                            print(f"  블럭 #{i+1}: ({cx}, {cy})")
                        print()
                
                grab_result.Release()
            
        except KeyboardInterrupt:
            print("\n사용자에 의해 중단됨")
        except Exception as e:
            print(f"✗ 오류 발생: {e}")
        finally:
            self.cleanup()
    
    def capture_and_detect(self):
        """1회 캡처 후 검출"""
        img = self.capture_image()
        
        if img is None:
            return None, None
        
        centers, debug_img, binary = self.detect_block_centers(img)
        
        print(f"\n[검출된 블럭 중심점 - 총 {len(centers)}개]")
        for i, (cx, cy) in enumerate(centers):
            print(f"  블럭 #{i+1}: ({cx}, {cy})")
        
        # 결과 저장
        cv2.imwrite("block_centers_result.jpg", debug_img)
        cv2.imwrite("block_centers_binary.jpg", binary)
        print("\n✓ 결과 저장: block_centers_result.jpg, block_centers_binary.jpg")
        
        # 화면에 표시
        binary_bgr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        display = np.hstack([debug_img, binary_bgr])
        
        cv2.imshow('Result', display)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        return centers, debug_img
    
    def cleanup(self):
        """리소스 정리"""
        if self.camera:
            self.camera.StopGrabbing()
            self.camera.Close()
        cv2.destroyAllWindows()
        print("✓ 카메라 연결 해제됨")


def main():
    print("=" * 60)
    print("사각 블럭 중심점 좌표 추출")
    print("=" * 60)
    print("\n모드 선택:")
    print("  1. 실시간 검출 (Live)")
    print("  2. 1회 캡처 후 검출")
    
    mode = input("\n모드 선택 (1 또는 2): ").strip()
    
    detector = BlockCenterDetector()
    
    if not detector.connect_camera():
        return
    
    if mode == '1':
        detector.run_live()
    elif mode == '2':
        detector.capture_and_detect()
    else:
        print("✗ 잘못된 선택입니다.")


if __name__ == "__main__":
    main()