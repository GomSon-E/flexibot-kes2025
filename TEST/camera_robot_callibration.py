import numpy as np
from typing import Tuple, List

class CameraRobotCalibration:
    """카메라 좌표를 로봇 좌표로 변환하는 캘리브레이션 클래스"""
    
    def __init__(self):
        self.transformation_matrix = None
        self.calibration_points = {
            'camera': [],
            'robot': []
        }
        
    def add_calibration_point(self, camera_point: Tuple[float, float], 
                             robot_point: Tuple[float, float]):
        """캘리브레이션 포인트 추가"""
        self.calibration_points['camera'].append(camera_point)
        self.calibration_points['robot'].append(robot_point)
        
    def calculate_transformation(self):
        """변환 행렬 계산"""
        if len(self.calibration_points['camera']) < 3:
            raise ValueError("최소 3개의 캘리브레이션 포인트가 필요합니다.")
        
        # 카메라 좌표를 homogeneous 좌표로 변환 (x, y, 1)
        camera_points = []
        for point in self.calibration_points['camera']:
            camera_points.append([point[0], point[1], 1])
        camera_matrix = np.array(camera_points)
        
        # 로봇 좌표
        robot_matrix = np.array(self.calibration_points['robot'])
        
        # 최소자승법으로 변환 행렬 계산
        self.transformation_matrix = np.linalg.lstsq(camera_matrix, robot_matrix, rcond=None)[0]
        
        return self.transformation_matrix
    
    def transform_point(self, camera_x: float, camera_y: float) -> Tuple[float, float]:
        """카메라 좌표를 로봇 좌표로 변환"""
        if self.transformation_matrix is None:
            raise ValueError("먼저 calculate_transformation()을 실행해주세요.")
        
        camera_point = np.array([camera_x, camera_y, 1])
        robot_point = np.dot(camera_point, self.transformation_matrix)
        
        return robot_point[0], robot_point[1]
    
    def transform_points(self, camera_points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """여러 카메라 좌표를 로봇 좌표로 변환"""
        robot_points = []
        for camera_point in camera_points:
            robot_point = self.transform_point(camera_point[0], camera_point[1])
            robot_points.append(robot_point)
        return robot_points
    
    def get_transformation_formula(self) -> str:
        """변환 공식을 문자열로 반환"""
        if self.transformation_matrix is None:
            return "변환 행렬이 계산되지 않았습니다."
        
        T = self.transformation_matrix
        formula = f"""
변환 공식:
robot_x = {T[0,0]:.10f} * camera_x + {T[1,0]:.10f} * camera_y + {T[2,0]:.10f}
robot_y = {T[0,1]:.10f} * camera_x + {T[1,1]:.10f} * camera_y + {T[2,1]:.10f}
"""
        return formula
    
    def verify_calibration(self) -> dict:
        """캘리브레이션 정확도 검증"""
        if self.transformation_matrix is None:
            raise ValueError("먼저 calculate_transformation()을 실행해주세요.")
        
        results = {
            'points': [],
            'avg_error': {'x': 0, 'y': 0},
            'max_error': {'x': 0, 'y': 0}
        }
        
        total_error_x = 0
        total_error_y = 0
        
        for camera_point, expected_robot in zip(self.calibration_points['camera'], 
                                               self.calibration_points['robot']):
            calculated_robot = self.transform_point(camera_point[0], camera_point[1])
            
            error_x = abs(calculated_robot[0] - expected_robot[0])
            error_y = abs(calculated_robot[1] - expected_robot[1])
            
            results['points'].append({
                'camera': camera_point,
                'expected_robot': expected_robot,
                'calculated_robot': calculated_robot,
                'error': (error_x, error_y)
            })
            
            total_error_x += error_x
            total_error_y += error_y
            
            results['max_error']['x'] = max(results['max_error']['x'], error_x)
            results['max_error']['y'] = max(results['max_error']['y'], error_y)
        
        num_points = len(self.calibration_points['camera'])
        results['avg_error']['x'] = total_error_x / num_points
        results['avg_error']['y'] = total_error_y / num_points
        
        return results
    
    def print_verification_results(self):
        """검증 결과를 보기 좋게 출력"""
        results = self.verify_calibration()
        
        print("=" * 60)
        print("캘리브레이션 검증 결과")
        print("=" * 60)
        
        for i, point_result in enumerate(results['points'], 1):
            print(f"\n포인트 {i}:")
            print(f"  카메라 좌표: {point_result['camera']}")
            print(f"  예상 로봇 좌표: {point_result['expected_robot']}")
            print(f"  계산된 로봇 좌표: ({point_result['calculated_robot'][0]:.3f}, "
                  f"{point_result['calculated_robot'][1]:.3f})")
            print(f"  오차: (x: {point_result['error'][0]:.6f}, y: {point_result['error'][1]:.6f})")
        
        print(f"\n평균 오차: x={results['avg_error']['x']:.6f}, y={results['avg_error']['y']:.6f}")
        print(f"최대 오차: x={results['max_error']['x']:.6f}, y={results['max_error']['y']:.6f}")


def main():
    """메인 실행 함수"""
    # 캘리브레이션 객체 생성
    calibrator = CameraRobotCalibration()
    
    # 주어진 캘리브레이션 포인트 추가
    calibration_data = [
        ((725, 462), (47.5, 407.289)),
        ((1899, 462), (48.275, 271.557)),
        ((725, 1362), (-57.132, 407.185))
    ]
    
    for camera_point, robot_point in calibration_data:
        calibrator.add_calibration_point(camera_point, robot_point)
    
    # 변환 행렬 계산
    transformation_matrix = calibrator.calculate_transformation()
    
    print("=" * 60)
    print("카메라-로봇 좌표 캘리브레이션")
    print("=" * 60)
    
    print("\n변환 행렬:")
    print(transformation_matrix)
    
    # 변환 공식 출력
    print(calibrator.get_transformation_formula())
    
    # 검증 결과 출력
    calibrator.print_verification_results()
    
    # 사용 예제
    print("\n" + "=" * 60)
    print("사용 예제")
    print("=" * 60)
    
    test_points = [
        (1000, 800),
        (1500, 1000),
        (500, 500)
    ]
    
    print("\n새로운 카메라 좌표 변환:")
    for camera_point in test_points:
        robot_point = calibrator.transform_point(camera_point[0], camera_point[1])
        print(f"카메라 {camera_point} -> 로봇 ({robot_point[0]:.3f}, {robot_point[1]:.3f})")
    
    # 실제 사용을 위한 간단한 함수
    print("\n" + "=" * 60)
    print("간단한 변환 함수 (복사해서 사용)")
    print("=" * 60)
    
    T = transformation_matrix
    print(f"""
def camera_to_robot(camera_x, camera_y):
    \"\"\"카메라 좌표를 로봇 좌표로 변환\"\"\"
    robot_x = {T[0,0]} * camera_x + {T[1,0]} * camera_y + {T[2,0]}
    robot_y = {T[0,1]} * camera_x + {T[1,1]} * camera_y + {T[2,1]}
    return robot_x, robot_y
""")


if __name__ == "__main__":
    main()