# SERVER/lego_process.py
import json
import os
import time

def camera_to_robot(camera_x, camera_y):
    """카메라 좌표를 로봇 좌표로 변환"""
    robot_x = 0.0001736920 * camera_x + -0.1155149323 * camera_y + 101.5115976961
    robot_y = -0.1155644249 * camera_x + -0.0000938678 * camera_y + 490.8506301772
    return robot_x, robot_y

class LegoProcess:
    def __init__(self, system):
        self.system = system
        self.coordination_path = os.path.join(
            os.path.dirname(__file__), "..", "UI", "coordination.json"
        )
        self.load_coordination()
    
    def load_coordination(self):
        """coordination.json 로드"""
        with open(self.coordination_path, 'r', encoding='utf-8') as f:
            self.coordination = json.load(f)
        print("✓ coordination.json 로드 완료")
    
    def get_green_centroids(self):
        """카메라에서 초록색(front) 객체 좌표 리스트 가져오기"""
        centroids = self.system.camera.get_front_centroids()
        print(f"📷 검출된 레고 개수: {len(centroids)}")
        return centroids
    
    async def execute_lego_drawing(self, shape_name: str):
        """레고 그림 그리기 전체 프로세스"""
        print("\n" + "=" * 60)
        print(f"레고 그림 그리기 시작: {shape_name}")
        print("=" * 60)
        
        # 1. 석션 장착
        print("\n[Step 1] 석션 장착")
        response = self.system.robot.attach_suction()
        if not response:
            print("✗ 석션 장착 실패")
            return {"status": "error", "message": "석션 장착 실패"}
        
        # 2. coordination.json에서 플레이트 번호 리스트 가져오기
        plate_list = self.coordination.get(shape_name.lower())
        if not plate_list:
            print(f"✗ '{shape_name}' 좌표 데이터 없음")
            return {"status": "error", "message": f"'{shape_name}' 데이터 없음"}
        
        print(f"\n[Step 2] 플레이트 리스트 로드: {len(plate_list)}개")
        
        # 3. 초기 카메라 좌표 리스트 가져오기
        green_coords = self.get_green_centroids()
        
        plate_index = 0
        total_plates = len(plate_list)
        
        # 4-6. 플레이트 번호 리스트 순회
        while plate_index < total_plates:
            # 남은 초록색 객체가 없으면
            if not green_coords:
                print("\n⚠️ 초록색 객체 없음 - 피더 동작 및 재검출")
                
                # 로봇 대기 위치로 이동
                self.system.robot.robot_init()
                
                # 피더 바운스 동작
                print("  - 피더 바운스 동작")
                self.system.feeder.client.write_register(1, 10113)  # 바운스(13)
                self.system.feeder.client.write_register(0, 1)      # 시작
                time.sleep(0.5)
                self.system.feeder.client.write_register(0, 0)      # 정지
                
                # 피더 집합 동작
                print("  - 피더 집합 동작 3초")
                self.system.feeder.client.write_register(1, 10114)  # 집합(14)
                self.system.feeder.client.write_register(0, 1)      # 시작
                time.sleep(3)
                self.system.feeder.client.write_register(0, 0)      # 정지
                
                # 재검출
                time.sleep(1)
                green_coords = self.get_green_centroids()
                
                if not green_coords:
                    print("✗ 여전히 객체 없음 - 프로세스 중단")
                    break
            
            # 플레이트 번호와 좌표 가져오기
            plate_seq = plate_list[plate_index]

            # 초록색 객체 좌표 하나 가져오기
            roi_x, roi_y = green_coords.pop(0)
            camera_x = self.system.camera.roi[0] + roi_x
            camera_y = self.system.camera.roi[1] + roi_y
            
            # 좌표 변환
            robot_x, robot_y = camera_to_robot(camera_x, camera_y)
            
            print(f"\n[{plate_index + 1}/{total_plates}] Plate #{plate_seq}")
            print(f"  카메라 좌표: ({camera_x}, {camera_y})")
            print(f"  로봇 좌표: ({robot_x:.3f}, {robot_y:.3f})")
            
            # lego_pick_place 실행
            response = self.system.robot.lego_pick_place(
                x=int(robot_x),
                y=int(robot_y),
                angle=0,
                plate_seq=plate_seq
            )
            
            if not response:
                print(f"⚠️ Plate #{plate_seq} 작업 실패")
            
            plate_index += 1
        
        print("\n" + "=" * 60)
        print("모든 플레이트 작업 완료")
        print("=" * 60)
        
        # 7. 완료 후 처리
        print("\n[최종 단계] 마무리")
        
        # 대기 위치로 이동
        print("  - 대기 위치로 이동")
        self.system.robot.robot_init()
        
        # 실린더 1번 pulse
        print("  - 실린더 1번 pulse")
        self.system.cylinder.cylinder_1_pulse(on_time=1.0, off_time=1.0)
        
        # 석션 탈착
        print("  - 석션 탈착")
        self.system.robot.detach_suction()

        # 대기 위치로 이동
        print("  - 대기 위치로 이동")
        self.system.robot.robot_init()
        
        print("\n✓ 레고 그림 그리기 완료!")
        
        return {
            "status": "completed",
            "shape": shape_name,
            "total_plates": total_plates,
            "message": "레고 그림 그리기 완료"
        }