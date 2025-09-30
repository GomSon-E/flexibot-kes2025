import ctypes
import sys

class LPCI7230:
    """LPCI-7230 제어 클래스 (16채널 PCI)"""
    
    def __init__(self, device_path='/dev/comedi0'):
        """초기화"""
        # libcomedi 로드
        try:
            self.comedi = ctypes.CDLL('libcomedi.so.0')
        except OSError:
            raise RuntimeError("libcomedi.so.0 로드 실패")
        
        # 함수 시그니처 설정
        self._setup_functions()
        
        # 디바이스 열기
        self.dev = self.comedi.comedi_open(device_path.encode())
        if not self.dev:
            raise RuntimeError(f"디바이스 열기 실패: {device_path}")
        
        # 채널 상태 저장 (출력 상태 추적용)
        self.subdev0_state = 0x0000  # 채널 0-15 (16채널)
        
        print(f"✅ LPCI-7230 초기화 완료")
    
    def _setup_functions(self):
        """함수 시그니처 정의"""
        self.comedi.comedi_open.argtypes = [ctypes.c_char_p]
        self.comedi.comedi_open.restype = ctypes.c_void_p
        
        self.comedi.comedi_dio_bitfield2.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, 
            ctypes.POINTER(ctypes.c_uint), ctypes.c_uint
        ]
        self.comedi.comedi_dio_bitfield2.restype = ctypes.c_int
        
        self.comedi.comedi_data_write.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, 
            ctypes.c_uint, ctypes.c_uint, ctypes.c_uint
        ]
        self.comedi.comedi_data_write.restype = ctypes.c_int
        
        self.comedi.comedi_data_read.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, 
            ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)
        ]
        self.comedi.comedi_data_read.restype = ctypes.c_int
        
        self.comedi.comedi_close.argtypes = [ctypes.c_void_p]
        self.comedi.comedi_close.restype = ctypes.c_int
    
    def control_channel(self, channel, state):
        """
        채널 제어 (ON/OFF)
        
        Args:
            channel: 0-15 (16채널)
            state: 'on', 'ON', 1 -> HIGH
                   'off', 'OFF', 0 -> LOW
        
        Returns:
            True: 성공
            False: 실패
        """
        # 입력 검증
        if channel < 0 or channel > 15:
            print(f"❌ 채널은 0-15 범위여야 합니다 (입력: {channel})")
            return False
        
        # 상태 변환
        if state in ['on', 'ON', 1, '1']:
            value = 1
            state_str = "ON"
        elif state in ['off', 'OFF', 0, '0']:
            value = 0
            state_str = "OFF"
        else:
            print(f"❌ 상태는 'on' 또는 'off'여야 합니다 (입력: {state})")
            return False
        
        try:
            # 채널 0-15: Subdevice 0만 사용 (16채널)
            if value == 1:
                self.subdev0_state |= (1 << channel)
            else:
                self.subdev0_state &= ~(1 << channel)
            
            write_mask = ctypes.c_uint(1 << channel)
            bits = ctypes.c_uint(self.subdev0_state)
            
            ret = self.comedi.comedi_dio_bitfield2(
                self.dev, 0, write_mask, ctypes.byref(bits), 0
            )
            if ret < 0:
                print(f"❌ 채널 {channel} 제어 실패")
                return False
            
            print(f"✅ 채널 {channel}: {state_str}")
            return True
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            return False
    
    def check_output(self, channel):
        """
        출력 상태 확인 (내가 설정한 출력 값)
        
        Args:
            channel: 0-15
        
        Returns:
            1: ON
            0: OFF
            None: 오류
        """
        if channel < 0 or channel > 15:
            print(f"❌ 채널은 0-15 범위여야 합니다 (입력: {channel})")
            return None
        
        try:
            value = (self.subdev0_state >> channel) & 1
            
            state_str = "ON" if value == 1 else "OFF"
            print(f"📤 채널 {channel} 출력: {state_str}")
            return value
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            return None
    
    def check_channel(self, channel):
        """
        입력 신호 읽기 (외부에서 들어오는 실제 신호)
        
        Args:
            channel: 0-15
        
        Returns:
            1: HIGH
            0: LOW
            None: 오류
        """
        # 입력 검증
        if channel < 0 or channel > 15:
            print(f"❌ 채널은 0-15 범위여야 합니다 (입력: {channel})")
            return None
        
        try:
            # 채널 0-15: Subdevice 0 (비트필드 읽기)
            write_mask = ctypes.c_uint(0)  # 읽기만
            bits = ctypes.c_uint(0)
            
            ret = self.comedi.comedi_dio_bitfield2(
                self.dev, 0, write_mask, ctypes.byref(bits), 0
            )
            if ret < 0:
                print(f"❌ 채널 {channel} 읽기 실패")
                return None
            
            value = (bits.value >> channel) & 1
            
            state_str = "HIGH" if value == 1 else "LOW"
            print(f"📥 채널 {channel} 입력: {state_str}")
            return value
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            return None
    
    def close(self):
        """종료"""
        if self.dev:
            self.comedi.comedi_close(self.dev)
            print("✅ 디바이스 닫기 완료")


def main():
    """사용자 입력으로 채널 제어"""
    print("=" * 50)
    print("ADLINK LPCI-7230 채널 제어")
    print("=" * 50)
    
    try:
        # 보드 초기화
        board = LPCI7230()
        
        print("\n사용법:")
        print("  - 'set' : 채널 ON/OFF 제어")
        print("  - 'output' : 출력 상태 확인")
        print("  - 'input' : 입력 신호 읽기")
        print("  - 'q' : 종료\n")
        
        while True:
            # 명령 입력
            cmd = input("명령 (set/output/input/q): ").strip().lower()
            
            if cmd in ['q', 'quit', 'exit']:
                print("\n종료합니다...")
                break
            
            if cmd == 'set':
                # 채널 입력
                ch_input = input("  채널 번호 (0-15): ").strip()
                
                try:
                    channel = int(ch_input)
                except ValueError:
                    print("  ❌ 숫자를 입력하세요\n")
                    continue
                
                # 상태 입력
                state_input = input("  상태 (on/off): ").strip()
                
                # 채널 제어
                board.control_channel(channel, state_input)
                print()
            
            elif cmd == 'output':
                # 채널 입력
                ch_input = input("  채널 번호 (0-15): ").strip()
                
                try:
                    channel = int(ch_input)
                except ValueError:
                    print("  ❌ 숫자를 입력하세요\n")
                    continue
                
                # 출력 상태 확인
                board.check_output(channel)
                print()
            
            elif cmd == 'input':
                # 채널 입력
                ch_input = input("  채널 번호 (0-15): ").strip()
                
                try:
                    channel = int(ch_input)
                except ValueError:
                    print("  ❌ 숫자를 입력하세요\n")
                    continue
                
                # 입력 신호 읽기
                board.check_channel(channel)
                print()
            
            else:
                print("❌ 'set', 'output', 'input', 또는 'q'를 입력하세요\n")
        
        # 종료
        board.close()
        
    except KeyboardInterrupt:
        print("\n\n종료합니다...")
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()