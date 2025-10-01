import os
import yaml
from ultralytics import YOLO
import torch

def train_yolo():    
    dataset_path = "./data_lego_train"
    yaml_path = os.path.join(dataset_path, 'data.yaml')
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    data['path'] = os.path.abspath(dataset_path)
    
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    print(f"데이터셋 정보:")
    print(f"  경로: {data['path']}")
    print(f"  클래스 수: {data.get('nc', 'Unknown')}")
    print(f"  클래스 이름: {data.get('names', 'Unknown')}")
    
    device = '0' if torch.cuda.is_available() else 'cpu'
    
    model_name = 'yolo11n-seg.pt'
    model = YOLO(model_name)
    print("모델 로드 완료")
    
    try:
        results = model.train(
            data=yaml_path,
            epochs=100,
            imgsz=640,
            batch=4,
            device=device,
            project='../models',
            name='yolov11_lego_seg',
            
            # 과적합 방지
            patience=20,             # Early stopping
            
            # 데이터 증강
            degrees=15,              # 회전
            translate=0.2,           # 이동
            scale=0.5,               # 스케일
            shear=5,                 # 전단
            flipud=0.3,              # 상하 반전
            fliplr=0.5,              # 좌우 반전
            mosaic=1.0,              # 모자이크
            mixup=0.15,              # 믹스업
            copy_paste=0.3,          # 객체 복사-붙여넣기
            
            # 학습률
            lr0=0.001,               # 낮게 시작
            lrf=0.01,
            
            save=True,
            val=True,
            plots=True,
            verbose=True
        )
        metrics = model.val()
        print(f"mAP50 (seg): {metrics.seg.map50:.4f}")
        print(f"mAP50-95 (seg): {metrics.seg.map:.4f}")
        
        return results
        
    except Exception as e:
        print(f"학습 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    train_yolo()