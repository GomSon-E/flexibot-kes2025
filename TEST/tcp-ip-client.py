import socket
import time

class RobotClient:
    """로봇 TCP/IP 통신 클라이언트"""
    
    def __init__(self, host='192.168.1.200', port=5000):
        """
        초기화
        
        Args:
            host: 로봇 IP 주소
            port: 로봇 포트 번호
        """
        self.host = host
        self.port = port
        self.sock = None
        self.connected = False
    
    def connect(self):
        """로봇 연결"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(30)  # 30초 타임아웃
            self.sock.connect((self.host, self.port))
            self.connected = True
            print(f"✓ 로봇 연결 성공: {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ 로봇 연결 실패: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """연결 종료"""
        if self.sock:
            self.sock.close()
            self.connected = False
            print("✓ 로봇 연결 종료")
    
    def send_task(self, task_num, x=0, y=0, angle=0, plate_seq=0):
        """
        Task 전송 및 응답 대기
        
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
        if not self.connected:
            print("✗ 로봇이 연결되지 않았습니다")
            return None
        
        try:
            # 메시지 생성: (A,B,C,D,E)
            message = f"({task_num},{x},{y},{angle},{plate_seq})\n"
            
            print(f"→ 전송: {message.strip()}")
            
            # 메시지 전송
            self.sock.sendall(message.encode('utf-8'))
            
            # 응답 대기 (블로킹)
            response = self.sock.recv(1024).decode('utf-8').strip()
            
            print(f"← 응답: {response}")
            
            return response
            
        except socket.timeout:
            print("✗ 응답 타임아웃")
            return None
        except Exception as e:
            print(f"✗ 통신 오류: {e}")
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


def main():
    """테스트 코드"""
    print("=" * 50)
    print("로봇 TCP/IP 통신 테스트")
    print("=" * 50)
    
    # 로봇 IP와 포트 입력
    host = input("로봇 IP (기본 127.0.0.1): ").strip() or "127.0.0.1"
    port = input("로봇 포트 (기본 5000): ").strip() or "5000"
    
    # 로봇 연결
    robot = RobotClient(host, int(port))
    
    if not robot.connect():
        return
    
    try:
        # 초기화
        robot.robot_init()
        
        # 그리퍼 장착
        robot.attach_gripper()
        
        # 레고 Pick & Place 예시
        robot.lego_pick_place(x=100, y=200, angle=45, plate_seq=1)
        robot.lego_pick_place(x=150, y=250, angle=90, plate_seq=2)
        
        # 블럭 Pick & Place 예시
        robot.block_pick_place(x=300, y=400, angle=0, plate_seq=3)
        
        print("\n✓ 테스트 완료!")
        
    except KeyboardInterrupt:
        print("\n\n종료합니다...")
    finally:
        robot.disconnect()


if __name__ == "__main__":
    main()