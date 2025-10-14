import ctypes
import os

class PCI7230Controller:
    def __init__(self, dll_path='pci7230_wrapper.dll'):
        if not os.path.exists(dll_path):
            raise FileNotFoundError(f"DLL 없음: {dll_path}")
        
        self.dll = ctypes.CDLL(dll_path)
        
        # 함수 시그니처
        self.dll.PCI7230_Init.argtypes = [ctypes.c_int]
        self.dll.PCI7230_Init.restype = ctypes.c_short
        
        self.dll.PCI7230_Release.restype = ctypes.c_short
        
        self.dll.PCI7230_SetChannel.argtypes = [ctypes.c_int, ctypes.c_int]
        self.dll.PCI7230_SetChannel.restype = ctypes.c_short
        
        self.dll.PCI7230_ReadChannel.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.dll.PCI7230_ReadChannel.restype = ctypes.c_short
        
        self.dll.PCI7230_WritePort.argtypes = [ctypes.c_uint32]  # c_ushort -> c_uint32
        self.dll.PCI7230_WritePort.restype = ctypes.c_short
        
        self.dll.PCI7230_ReadPort.argtypes = [ctypes.POINTER(ctypes.c_uint32)]  # c_ushort -> c_uint32
        self.dll.PCI7230_ReadPort.restype = ctypes.c_short
        
        self.connected = False
    
    def connect(self, card_number=0):
        result = self.dll.PCI7230_Init(card_number)
        if result < 0:
            print(f"✗ 초기화 실패: {result}")
            return False
        self.connected = True
        print(f"✓ 연결 성공 (카드: {result})")
        return True
    
    def disconnect(self):
        if self.connected:
            self.dll.PCI7230_Release()
            self.connected = False
            print("✓ 연결 해제")
    
    def set_channel(self, channel, state):
        if not self.connected:
            print("✗ 미연결")
            return False
        
        result = self.dll.PCI7230_SetChannel(channel, 1 if state else 0)
        if result < 0:
            print(f"✗ 채널 {channel} 제어 실패")
            return False
        
        print(f"✓ 채널 {channel}: {'ON' if state else 'OFF'}")
        return True
    
    def read_channel(self, channel):
        if not self.connected:
            return None
        
        state = ctypes.c_int()
        result = self.dll.PCI7230_ReadChannel(channel, ctypes.byref(state))
        if result < 0:
            return None
        return state.value
    
    def write_port(self, value):
        if not self.connected:
            return False
        result = self.dll.PCI7230_WritePort(value)
        if result < 0:
            print(f"✗ 포트 쓰기 실패")
            return False
        print(f"✓ 포트 출력: 0x{value:08X}")
        return True
    
    def read_port(self):
        if not self.connected:
            return None
        value = ctypes.c_uint32()  # c_ushort -> c_uint32
        result = self.dll.PCI7230_ReadPort(ctypes.byref(value))
        if result < 0:
            return None
        print(f"📥 포트 입력: 0x{value.value:08X}")
        return value.value
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()