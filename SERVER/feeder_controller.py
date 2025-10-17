# SERVER/feeder_controller.py
from pymodbus.client import ModbusTcpClient

class FeederController:
    """피더 제어 클래스"""
    
    def __init__(self, ip='192.168.1.100', port=502):
        self.ip = ip
        self.port = port
        self.client = None
        
    def connect(self):
        """피더 연결"""
        try:
            self.client = ModbusTcpClient(self.ip, port=self.port)
            return self.client.connect()
        except Exception as e:
            print(f"피더 연결 실패: {e}")
            return False
    
    def set_light(self, on: bool, brightness: int = 0):
        """조명 제어"""
        if not self.client:
            return False
        
        try:
            # P0.10: 조명 스위치
            self.client.write_register(10, 1 if on else 0)
            
            if on:
                # P0.11: 밝기 (0-100% -> 0-1000)
                brightness_value = int(brightness * 10)
                self.client.write_register(11, brightness_value)
            
            return True
        except Exception as e:
            print(f"조명 제어 실패: {e}")
            return False
    
    def disconnect(self):
        """연결 종료"""
        if self.client:
            self.client.close()