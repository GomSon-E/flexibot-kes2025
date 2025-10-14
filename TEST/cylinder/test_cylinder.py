from pci7230_controller import PCI7230Controller
import time
import os

print("=" * 50)
print("PCI-7230 실린더 제어 테스트")
print("=" * 50)

# 절대 경로 사용
dll_path = os.path.join(os.path.dirname(__file__), 'pci7230_wrapper.dll')
print(f"DLL 경로: {dll_path}")
print(f"DLL 존재: {os.path.exists(dll_path)}\n")

ctrl = PCI7230Controller(dll_path)

if ctrl.connect(card_number=0):
    try:      
        # 여러 채널 순차 제어 테스트
        print("\n[테스트 2] 채널 0-3 순차 ON & OFF")
        for i in range(4):
            ctrl.set_channel(i, True)
            time.sleep(1)
            ctrl.set_channel(i, False)
            time.sleep(3)
        
    except KeyboardInterrupt:
        print("\n\n사용자가 중단했습니다.")
    
    finally:
        ctrl.disconnect()
else:
    print("\n✗ PCI-7230 카드를 찾을 수 없습니다.")
    print("  - 카드가 제대로 연결되어 있는지 확인하세요")
    print("  - 드라이버가 설치되어 있는지 확인하세요")