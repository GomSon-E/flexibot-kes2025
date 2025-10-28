import json
import os
import asyncio
import cv2
import numpy as np

def camera_to_robot(camera_x, camera_y, camera_angle):
    """카메라 좌표를 로봇 좌표로 변환"""
    #robot_x = -0.0016273045 * camera_x + -0.1182909450 * camera_y + -0.0663562452 * camera_angle + 109.8510524433
    #robot_y = -0.1146515771 * camera_x + 0.0012567711 * camera_y + 0.0323767126 * camera_angle + 486.6392082585
    robot_x =  -0.1134748 * camera_y +  50.126
    robot_y =  -0.1092954 * camera_x +  408 # 409.776
    
    #robot_y = -0.1146515771 * camera_x + 0.0012567711 * camera_y + 486.6392082585
    # robot_angle = -0.0457792934 * camera_x + 0.1122743643 * camera_y + 1.1534938795 * camera_angle + 239.9608765861

    while camera_angle > 90 or camera_angle < 0 :
        #-45도 이하일 경우 90도 합산
        if camera_angle < 0:
            camera_angle += 90
        #45도 이상일 경우 90도 차감
        else :
            camera_angle -= 90      


    #1차 공식 
    robot_angle = 90 - abs(camera_angle) 
    if camera_angle < 0 :
        robot_angle = -robot_angle

    #return robot_x, robot_y, camera_angle
    return robot_x, robot_y, robot_angle

class BlockProcess:
    def __init__(self, system):
        self.system = system
        self.coordination_path = os.path.join(
            os.path.dirname(__file__), "..", "UI", "coordination.json"
        )
        self.load_coordination()
        
        # 블럭 검출 파라미터
        self.min_distance = 80
        self.padding = 20
        self.min_area = 28000
        self.max_area = 30000
    
    def load_coordination(self):
        """coordination.json 로드"""
        with open(self.coordination_path, 'r', encoding='utf-8') as f:
            self.coordination = json.load(f)
        print("✓ coordination.json 로드 완료")
    
    def detect_pickable_blocks(self):
        """
        picking 가능한 블럭만 검출
        Returns: [(center_x, center_y, angle), ...]
        """
        # 현재 프레임 가져오기
        with self.system.camera.lock:
            if self.system.camera.current_frame is None:
                return []
            img = self.system.camera.current_frame.copy()
        
        # 그레이스케일 변환 및 이진화
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        
        # 윤곽선 검출
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        centers = []
        rotated_rects = []
        angles = []
        
        # 정사각형 필터링
        for cnt in contours:
            area = cv2.contourArea(cnt)
            
            # 크기 필터
            if area < self.min_area or area > self.max_area:
                continue
            
            # 최소 회전 사각형
            rect = cv2.minAreaRect(cnt)
            (cx, cy), (w, h), angle = rect
            
            # 정사각형 판별 (종횡비 1.15 이하)
            aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
            if aspect_ratio > 1.15:
                continue
            
            centers.append((cx, cy))
            
            # 패딩 추가
            w_pad = w + 2 * self.padding
            h_pad = h + 2 * self.padding
            rotated_rects.append(((cx, cy), (w_pad, h_pad), angle))
            angles.append(angle)
        
        # picking 가능 여부 판단
        pickable_blocks = []
        for i, ((cx, cy), rect, angle) in enumerate(zip(centers, rotated_rects, angles)):
            min_dist = float('inf')
            for j, (ox, oy) in enumerate(centers):
                if i != j:
                    dist = np.sqrt((cx - ox)**2 + (cy - oy)**2)
                    min_dist = min(min_dist, dist)
            
            # 최소 거리가 기준 이상이면 picking 가능
            if min_dist >= self.min_distance:
                pickable_blocks.append((cx, cy, angle))
                print(f"✓ Picking 가능 블럭: 위치({cx:.3f}, {cy:.3f}), 각도={angle:.3f}°")
        
        print(f"📷 총 {len(pickable_blocks)}개 블럭 picking 가능")
        return pickable_blocks
    
    async def execute_block_writing(self, alphabet: str):
        """블럭 알파벳 쓰기 전체 프로세스"""
        print("\n" + "=" * 60)
        print(f"블럭 알파벳 쓰기 시작: {alphabet}")
        print("=" * 60)
        
        # 1. 그리퍼 장착
        print("\n[Step 1] 그리퍼 장착")
        response = self.system.robot.attach_gripper()
        if not response:
            print("✗ 그리퍼 장착 실패")
            return {"status": "error", "message": "그리퍼 장착 실패"}
        
        # 2. 대기 위치 가기
        self.system.robot.robot_init()

        print("  - 실린더 0번 pulse")
        self.system.cylinder.cylinder_0_pulse(on_time=1.0, off_time=1.0)
        print("  - 실린더 2번 pulse")
        self.system.cylinder.cylinder_2_pulse(on_time=1.0, off_time=1.0) 
        
        # 3. coordination.json에서 플레이트 번호 리스트 가져오기
        plate_list = self.coordination.get(alphabet)
        if not plate_list:
            print(f"✗ '{alphabet}' 좌표 데이터 없음")
            return {"status": "error", "message": f"'{alphabet}' 데이터 없음"}
        
        print(f"\n[Step 2] 플레이트 리스트 로드: {len(plate_list)}개")
        
        # 4. 초기 블럭 좌표 리스트 가져오기
        pickable_blocks = self.detect_pickable_blocks()
        
        plate_index = 0
        total_plates = len(plate_list)
        
        # 5-7. 플레이트 번호 리스트 순회
        while plate_index < total_plates:
            # 남은 picking 가능한 블럭이 없으면
            if not pickable_blocks:
                print("\n⚠️ Picking 가능한 블럭 없음 - 피더 동작 및 재검출")
                
                # 로봇 대기 위치로 이동
                self.system.robot.robot_init()
                
                # 피더 바운스 동작
                print("  - 피더 바운스 동작")
                self.system.feeder.client.write_register(1, 10113)  # 바운스(13)
                self.system.feeder.client.write_register(0, 1)      # 시작
                await asyncio.sleep(0.5)
                self.system.feeder.client.write_register(0, 0)      # 정지
                
                # 피더 집합 동작
                print("  - 피더 집합 동작")
                self.system.feeder.client.write_register(1, 10114)  # 집합(14)
                self.system.feeder.client.write_register(0, 1)      # 시작
                await asyncio.sleep(0.2)
                self.system.feeder.client.write_register(0, 0)      # 정지
                
                # 재검출
                await asyncio.sleep(1.0)
                pickable_blocks = self.detect_pickable_blocks()
                
                # if not pickable_blocks:
                #     print("✗ 여전히 블럭 없음 - 프로세스 중단")
                #     break
            
            # 플레이트 번호와 좌표 가져오기
            plate_seq = plate_list[plate_index]
            
            # picking 가능한 블럭 좌표 하나 가져오기
            roi_x, roi_y, roi_angle = pickable_blocks.pop(0)
            camera_x = + roi_x
            camera_y = + roi_y
            camera_angle = roi_angle
            
            # 로봇 좌표로 변환
            robot_x, robot_y, robot_angle = camera_to_robot(camera_x, camera_y, camera_angle)
            
            print(f"\n[{plate_index + 1}/{total_plates}] Plate #{plate_seq}")
            print(f"  (블럭)카메라 좌표: ({camera_x:.3f}, {camera_y:.3f}), 각도: {camera_angle:.3f}°")
            print(f"  (블럭)로봇 좌표: ({robot_x:.3f}, {robot_y:.3f}), 각도: {robot_angle:.3f}°")
            
            # block_pick_place 실행
            response = self.system.robot.block_pick_place(
                x=round(robot_x, 3),
                y=round(robot_y, 3),
                angle=round(robot_angle, 3),
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
        
        # 실린더 3번 pulse
        print("  - 실린더 3번 pulse")
        self.system.cylinder.cylinder_3_pulse(on_time=1.0, off_time=1.0)
        
        # 그리퍼 탈착
        print("  - 그리퍼 탈착")
        self.system.robot.detach_gripper()
        
        # 대기 위치로 이동
        print("  - 대기 위치로 이동")
        self.system.robot.robot_init()
        
        print("\n✓ 블럭 알파벳 쓰기 완료!")
        
        return {
            "status": "completed",
            "alphabet": alphabet,
            "total_plates": total_plates,
            "message": "블럭 알파벳 쓰기 완료"
        }