import socket
import time

class RobotClient:
    """로봇 TCP/IP 통신 클라이언트"""
    
    def __init__(self, host='192.168.0.10', port=64512, max_retries=3, max_connect_retries=100):
        """
        초기화
        
        Args:
            host: 로봇 IP 주소
            port: 로봇 포트 번호
            max_retries: 최대 재시도 횟수
            max_connect_retries: 최대 연결 시도 횟수
        """
        self.host = host
        self.port = port
        self.max_retries = max_retries
        self.max_connect_retries = max_connect_retries
        self.sock = None
        self.connected = False
    
    def connect(self):
        """로봇 연결 (최대 100회 시도)"""
        for attempt in range(1, self.max_connect_retries + 1):
            try:
                print(f"연결 시도 {attempt}/{self.max_connect_retries}...")
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(30)  # 30초 타임아웃
                self.sock.connect((self.host, self.port))
                self.connected = True
                print(f"✓ 로봇 연결 성공: {self.host}:{self.port}")
                return True
            except Exception as e:
                print(f"✗ 연결 실패 ({attempt}/{self.max_connect_retries}): {e}")
                self.connected = False
                if self.sock:
                    self.sock.close()
                if attempt < self.max_connect_retries:
                    time.sleep(1)  # 1초 대기 후 재시도
        
        print(f"\n✗ 최대 연결 시도 횟수 초과 ({self.max_connect_retries}회)")
        return False
    
    def disconnect(self):
        """연결 종료"""
        if self.sock:
            self.sock.close()
            self.connected = False
            print("✓ 로봇 연결 종료")
    
    def send_task(self, task_num, x=0, y=0, angle=0, plate_seq=0):
        """
        Task 전송 및 응답 대기 (재시도 로직 포함)
        
        Args:
            task_num: Task 번호 (0-8)
            x: X 좌표
            y: Y 좌표
            angle: 회전각
            plate_seq: 플레이트 순번
            
        Returns:
            str: 로봇 응답 메시지
            None: 실패
        """
        retry_count = 0
        
        while retry_count < self.max_retries:
            # 재시도 시 재연결
            if retry_count > 0:
                print(f"\n⚠️  재시도 {retry_count}/{self.max_retries}")
                self.disconnect()
                time.sleep(1)
                if not self.connect():
                    retry_count += 1
                    continue
            
            # 연결 확인
            if not self.connected:
                print("✗ 로봇이 연결되지 않았습니다")
                retry_count += 1
                continue
            
            try:
                # 메시지 생성: ,A,B,C,D,E,\n
                message = f",{task_num},{x},{y},{angle},{plate_seq},\n"
                
                print(f"→ 전송: {message.strip()}")
                
                # 메시지 전송
                self.sock.sendall(message.encode('utf-8'))
                
                # 응답 대기 (블로킹)
                response = self.sock.recv(1024).decode('utf-8').strip()

                if response == "":
                    print("✗ 빈 응답 수신")
                    retry_count += 1
                    continue
                
                print(f"← 응답: {response}")
                return response
                
            except socket.timeout:
                print("✗ 응답 타임아웃")
                retry_count += 1
                continue
            except Exception as e:
                print(f"✗ 통신 오류: {e}")
                retry_count += 1
                continue
        
        print(f"\n✗ 최대 재시도 횟수 초과 ({self.max_retries}회)")
        return None
    
    # Task 0: 로봇 초기화
    def robot_init(self):
        """로봇 초기화"""
        print("\n[Task 0] 로봇 초기화")
        return self.send_task(0)
    
    # Task 1: 툴 플레이트 초기화
    def tool_plate_init(self):
        """툴 플레이트 초기화"""
        print("\n[Task 1] 툴 플레이트 초기화")
        return self.send_task(1)
    
    # Task 2: 그리퍼 장착
    def attach_gripper(self):
        """그리퍼 장착"""
        print("\n[Task 2] 그리퍼 장착")
        return self.send_task(2)
    
    # Task 3: 그리퍼 탈착
    def detach_gripper(self):
        """그리퍼 탈착"""
        print("\n[Task 3] 그리퍼 탈착")
        return self.send_task(3)
    
    # Task 4: 석션 장착
    def attach_suction(self):
        """석션 장착"""
        print("\n[Task 4] 석션 장착")
        return self.send_task(4)
    
    # Task 5: 석션 탈착
    def detach_suction(self):
        """석션 탈착"""
        print("\n[Task 5] 석션 탈착")
        return self.send_task(5)
    
    # Task 6: 블럭 P&P
    def block_pick_place(self, x, y, angle, plate_seq):
        """
        블럭 Pick & Place
        
        Args:
            x: 픽업 X 좌표
            y: 픽업 Y 좌표
            angle: 회전각
            plate_seq: 플레이트 순번
        """
        print(f"\n[Task 6] 블럭 P&P - 위치({x}, {y}), 각도{angle}°, Plate#{plate_seq}")
        return self.send_task(6, x, y, angle, plate_seq)
    
    # Task 7: 레고 P&P
    def lego_pick_place(self, x, y, angle, plate_seq):
        """
        레고 Pick & Place
        
        Args:
            x: 픽업 X 좌표
            y: 픽업 Y 좌표
            angle: 회전각
            plate_seq: 플레이트 순번
        """
        print(f"\n[Task 7] 레고 P&P - 위치({x}, {y}), 각도{angle}°, Plate#{plate_seq}")
        return self.send_task(7, x, y, angle, plate_seq)
    
    # Task 8: 잔량배출 P&P
    def waste_pick_place(self, x, y, angle, plate_seq):
        """
        잔량배출 Pick & Place
        
        Args:
            x: 픽업 X 좌표
            y: 픽업 Y 좌표
            angle: 회전각
            plate_seq: 플레이트 순번
        """
        print(f"\n[Task 8] 잔량배출 P&P - 위치({x}, {y}), 각도{angle}°, Plate#{plate_seq}")
        return self.send_task(8, x, y, angle, plate_seq)


def print_menu():
    """메뉴 출력"""
    print("\n" + "=" * 50)
    print("로봇 제어 메뉴")
    print("=" * 50)
    print("0. 로봇 초기화")
    print("1. 툴 플레이트 초기화")
    print("2. 그리퍼 장착")
    print("3. 그리퍼 탈착")
    print("4. 석션 장착")
    print("5. 석션 탈착")
    print("6. 블럭 Pick & Place")
    print("7. 레고 Pick & Place")
    print("8. 잔량배출 Pick & Place")
    print("9. 종료")
    print("=" * 50)


def get_task_params(task_num):
    """Task 파라미터 입력받기"""
    try:
        print(f"\n[Task {task_num}] 파라미터 입력 (기본값: 0)")
        
        x_input = input("  X 좌표 (Enter=0): ").strip()
        x = float(x_input) if x_input else 0
        
        y_input = input("  Y 좌표 (Enter=0): ").strip()
        y = float(y_input) if y_input else 0
        
        angle_input = input("  회전각 (Enter=0): ").strip()
        angle = float(angle_input) if angle_input else 0
        
        plate_seq_input = input("  플레이트 순번 (Enter=0): ").strip()
        plate_seq = int(plate_seq_input) if plate_seq_input else 0
        
        return x, y, angle, plate_seq
    except ValueError:
        print("✗ 잘못된 입력입니다.")
        return None


def main():
    """대화형 로봇 제어"""
    print("=" * 50)
    print("로봇 TCP/IP 통신 대화형 제어")
    print("=" * 50)
    
    # 로봇 IP와 포트 입력
    host = input("로봇 IP (기본 192.168.0.10): ").strip() or "192.168.0.10"
    port = input("로봇 포트 (기본 64512): ").strip() or "64512"
    
    # 로봇 연결
    robot = RobotClient(host, int(port), max_retries=3)
    
    if not robot.connect():
        print("\n로봇 연결에 실패했습니다.")
        return
    
    try:
        while True:
            print_menu()
            choice = input("명령을 선택하세요: ").strip()
            
            if choice == '0':
                params = get_task_params(0)
                if params:
                    robot.send_task(0, *params)
                
            elif choice == '1':
                params = get_task_params(1)
                if params:
                    robot.send_task(1, *params)
                
            elif choice == '2':
                params = get_task_params(2)
                if params:
                    robot.send_task(2, *params)
                
            elif choice == '3':
                params = get_task_params(3)
                if params:
                    robot.send_task(3, *params)
                
            elif choice == '4':
                params = get_task_params(4)
                if params:
                    robot.send_task(4, *params)
                
            elif choice == '5':
                params = get_task_params(5)
                if params:
                    robot.send_task(5, *params)
                    
            elif choice == '6':
                params = get_task_params(6)
                if params:
                    robot.send_task(6, *params)
                    
            elif choice == '7':
                params = get_task_params(7)
                if params:
                    robot.send_task(7, *params)
                    
            elif choice == '8':
                params = get_task_params(8)
                if params:
                    robot.send_task(8, *params)
                    
            elif choice == '9':
                print("\n종료합니다...")
                break
                
            else:
                print("\n✗ 잘못된 선택입니다. 다시 선택해주세요.")
            
            input("\n계속하려면 Enter를 누르세요...")
    
    except KeyboardInterrupt:
        print("\n\n강제 종료합니다...")
    
    finally:
        robot.disconnect()


if __name__ == "__main__":
    main()