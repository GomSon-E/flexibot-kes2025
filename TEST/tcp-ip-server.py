import socket
import threading
import time

class RobotMockServer:
    """로봇 시뮬레이터 (테스트용)"""
    
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        
        self.task_names = {
            0: "로봇 초기화",
            1: "툴 플레이트 초기화",
            2: "그리퍼 장착",
            3: "그리퍼 탈착",
            4: "석션 장착",
            5: "석션 탈착",
            6: "블럭 P&P",
            7: "레고 P&P",
            8: "잔량배출 P&P"
        }
    
    def start(self):
        """서버 시작"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            self.running = True
            
            print("=" * 60)
            print(f"🤖 로봇 시뮬레이터 시작: {self.host}:{self.port}")
            print("=" * 60)
            print("클라이언트 연결 대기 중...\n")
            
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    print(f"✓ 클라이언트 연결: {addr}")
                    
                    # 클라이언트 처리 (별도 스레드)
                    thread = threading.Thread(
                        target=self.handle_client, 
                        args=(client_socket,)
                    )
                    thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"✗ 오류: {e}")
        
        except Exception as e:
            print(f"✗ 서버 시작 실패: {e}")
    
    def handle_client(self, client_socket):
        """클라이언트 요청 처리"""
        try:
            while self.running:
                # 메시지 수신
                data = client_socket.recv(1024).decode('utf-8').strip()
                
                if not data:
                    break
                
                print(f"\n{'='*60}")
                print(f"📨 수신: {data}")
                
                # 메시지 파싱: (A,B,C,D,E)
                try:
                    # 괄호 제거 후 파싱
                    values = data.strip('()').split(',')
                    task_num = int(values[0])
                    x = int(values[1])
                    y = int(values[2])
                    angle = int(values[3])
                    plate_seq = int(values[4])
                    
                    task_name = self.task_names.get(task_num, "알 수 없는 Task")
                    
                    print(f"┌─ Task {task_num}: {task_name}")
                    
                    if task_num in [6, 7, 8]:
                        print(f"│  좌표: ({x}, {y})")
                        print(f"│  각도: {angle}°")
                        print(f"│  Plate: #{plate_seq}")
                    
                    # Task 처리 시뮬레이션
                    print(f"│  작업 수행 중...")
                    time.sleep(1)  # 작업 시간 시뮬레이션
                    
                    # 응답 전송
                    response = f"OK,{task_num}\n"
                    client_socket.sendall(response.encode('utf-8'))
                    
                    print(f"└─ 📤 응답: {response.strip()}")
                    print(f"{'='*60}")
                    
                except (ValueError, IndexError) as e:
                    print(f"✗ 메시지 파싱 오류: {e}")
                    error_response = "ERROR,INVALID_FORMAT\n"
                    client_socket.sendall(error_response.encode('utf-8'))
        
        except Exception as e:
            print(f"✗ 클라이언트 처리 오류: {e}")
        
        finally:
            client_socket.close()
            print("\n✓ 클라이언트 연결 종료\n")
    
    def stop(self):
        """서버 종료"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("\n✓ 서버 종료")


if __name__ == "__main__":
    server = RobotMockServer(host='127.0.0.1', port=5000)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n\n종료 중...")
        server.stop()