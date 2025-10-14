import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from pci7230_controller import PCI7230Controller

class CylinderController:
    """실린더 제어 클래스 - 4개의 실린더를 개별 제어"""
    
    def __init__(self):
        """초기화 - 상대 경로 자동 계산"""
        # lib 폴더의 DLL 경로
        lib_path = os.path.join(os.path.dirname(__file__), 'lib')
        dll_path = os.path.join(lib_path, 'pci7230_wrapper.dll')
        
        self.controller = PCI7230Controller(dll_path)
        self.connected = False
    
    def connect(self, card_number=0):
        """PCI-7230 카드 연결"""
        self.connected = self.controller.connect(card_number)
        return self.connected
    
    def disconnect(self):
        """연결 해제"""
        if self.connected:
            self.controller.disconnect()
            self.connected = False
    
    # 개별 ON/OFF 함수
    def cylinder_0_on(self):
        """실린더 0번 ON"""
        if not self.connected:
            print("✗ 카드 미연결")
            return False
        return self.controller.set_channel(0, True)
    
    def cylinder_0_off(self):
        """실린더 0번 OFF"""
        if not self.connected:
            print("✗ 카드 미연결")
            return False
        return self.controller.set_channel(0, False)
    
    def cylinder_1_on(self):
        """실린더 1번 ON"""
        if not self.connected:
            print("✗ 카드 미연결")
            return False
        return self.controller.set_channel(1, True)
    
    def cylinder_1_off(self):
        """실린더 1번 OFF"""
        if not self.connected:
            print("✗ 카드 미연결")
            return False
        return self.controller.set_channel(1, False)
    
    def cylinder_2_on(self):
        """실린더 2번 ON"""
        if not self.connected:
            print("✗ 카드 미연결")
            return False
        return self.controller.set_channel(2, True)
    
    def cylinder_2_off(self):
        """실린더 2번 OFF"""
        if not self.connected:
            print("✗ 카드 미연결")
            return False
        return self.controller.set_channel(2, False)
    
    def cylinder_3_on(self):
        """실린더 3번 ON"""
        if not self.connected:
            print("✗ 카드 미연결")
            return False
        return self.controller.set_channel(3, True)
    
    def cylinder_3_off(self):
        """실린더 3번 OFF"""
        if not self.connected:
            print("✗ 카드 미연결")
            return False
        return self.controller.set_channel(3, False)
    
    # 통합 펄스 함수
    def cylinder_0_pulse(self, on_time=1.0, off_time=1.0):
        """
        실린더 0번 ON → 대기 → OFF
        
        Args:
            on_time: ON 상태 유지 시간 (초)
            off_time: OFF 후 대기 시간 (초)
        """
        print(f"실린더 0번 펄스 (ON: {on_time}초, OFF 대기: {off_time}초)")
        self.cylinder_0_on()
        time.sleep(on_time)
        self.cylinder_0_off()
        time.sleep(off_time)
    
    def cylinder_1_pulse(self, on_time=1.0, off_time=1.0):
        """
        실린더 1번 ON → 대기 → OFF
        
        Args:
            on_time: ON 상태 유지 시간 (초)
            off_time: OFF 후 대기 시간 (초)
        """
        print(f"실린더 1번 펄스 (ON: {on_time}초, OFF 대기: {off_time}초)")
        self.cylinder_1_on()
        time.sleep(on_time)
        self.cylinder_1_off()
        time.sleep(off_time)
    
    def cylinder_2_pulse(self, on_time=1.0, off_time=1.0):
        """
        실린더 2번 ON → 대기 → OFF
        
        Args:
            on_time: ON 상태 유지 시간 (초)
            off_time: OFF 후 대기 시간 (초)
        """
        print(f"실린더 2번 펄스 (ON: {on_time}초, OFF 대기: {off_time}초)")
        self.cylinder_2_on()
        time.sleep(on_time)
        self.cylinder_2_off()
        time.sleep(off_time)
    
    def cylinder_3_pulse(self, on_time=1.0, off_time=1.0):
        """
        실린더 3번 ON → 대기 → OFF
        
        Args:
            on_time: ON 상태 유지 시간 (초)
            off_time: OFF 후 대기 시간 (초)
        """
        print(f"실린더 3번 펄스 (ON: {on_time}초, OFF 대기: {off_time}초)")
        self.cylinder_3_on()
        time.sleep(on_time)
        self.cylinder_3_off()
        time.sleep(off_time)
    
    def __enter__(self):
        """with 구문 지원"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """with 구문 종료 시 자동 해제"""
        self.disconnect()