from pymodbus.client import ModbusTcpClient
from pypylon import pylon
import cv2
import time

def connect_camera():
    """카메라 연결 및 설정"""
    tl_factory = pylon.TlFactory.GetInstance()
    camera = pylon.InstantCamera(tl_factory.CreateFirstDevice())
    camera.Open()
    
    converter = pylon.ImageFormatConverter()
    converter.OutputPixelFormat = pylon.PixelType_BGR8packed
    converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
    
    return camera, converter

def capture_roi_image(camera, converter, filename):
    """ROI 영역 캡처 및 이진화"""
    # 고정 ROI
    roi = (711, 409, 1260, 971)
    
    camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
    
    grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
    
    if grab_result.GrabSucceeded():
        image = converter.Convert(grab_result)
        img = image.GetArray()
        
        # ROI 크롭
        x, y, w, h = roi
        roi_img = img[y:y+h, x:x+w]

        # 대비 증가
        alpha = 1.5
        roi_img = cv2.convertScaleAbs(roi_img, alpha=alpha)
        
        # 그레이스케일 변환
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        
        # 이진화 (Otsu's method)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 이진화된 이미지 저장
        cv2.imwrite(filename, binary)
        print(f"✓ 저장: {filename}")
    
    grab_result.Release()
    camera.StopGrabbing()

def main():
    # 피더 연결
    client = ModbusTcpClient('192.168.1.100', port=502)
    
    if not client.connect():
        print("✗ 피더 연결 실패")
        return
    
    print("✓ 피더 연결 성공")
    
    # 카메라 연결
    camera, converter = connect_camera()
    print("✓ 카메라 연결 성공")
    
    try:
        # 조명 켜기 (10%)
        print("\n조명 켜기 (10%)")
        client.write_register(10, 1)
        client.write_register(11, 100)
        time.sleep(0.5)
        
        # 50번 반복
        for i in range(1, 51):
            print(f"\n=== {i}/50 ===")
            
            # 바운스 0.5초
            print("바운스 동작 (0.5초)")
            client.write_register(1, 10113)
            client.write_register(0, 1)
            time.sleep(0.5)
            client.write_register(0, 0)
            time.sleep(0.2)
            
            # 집합 0.5초
            print("집합 동작 (0.5초)")
            client.write_register(1, 10114)
            client.write_register(0, 1)
            time.sleep(0.5)
            client.write_register(0, 0)
            time.sleep(2)
            
            # 캡처 (이진화)
            filename = f"./data_block/block_{i}.png"
            capture_roi_image(camera, converter, filename)
        
        print("\n완료!")
        
    except KeyboardInterrupt:
        client.write_register(0, 0)
        client.write_register(10, 0)
        print("\n\n종료합니다...")
    finally:
        camera.Close()
        client.close()

if __name__ == "__main__":
    main()