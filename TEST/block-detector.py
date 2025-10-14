import cv2
import numpy as np
import os

def check_pickable_blocks(image_path, min_distance=100, padding=20, min_area=5000, max_area=50000):
    """정사각형 블럭 검출 및 회전된 바운딩 박스"""
    if not os.path.exists(image_path):
        print(f"❌ 파일을 찾을 수 없습니다: {image_path}")
        return None, []
    
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ 이미지를 읽을 수 없습니다: {image_path}")
        return None, []
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    result = img.copy()
    centers = []
    rotated_rects = []
    
    # 정사각형 필터링
    for cnt in contours:
        area = cv2.contourArea(cnt)
        
        print(f"검출된 윤곽선 면적: {area}")

        # 크기 필터
        if area < min_area or area > max_area:
            continue
        
        # 최소 회전 사각형
        rect = cv2.minAreaRect(cnt)
        (cx, cy), (w, h), angle = rect
        
        # 정사각형 판별
        aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
        if aspect_ratio > 1.15:
            continue
        
        centers.append((int(cx), int(cy)))
        
        # 패딩 추가
        w_pad = w + 2 * padding
        h_pad = h + 2 * padding
        rotated_rects.append(((cx, cy), (w_pad, h_pad), angle))
    
    # picking 가능 여부 판단
    for i, ((cx, cy), rect) in enumerate(zip(centers, rotated_rects)):
        min_dist = float('inf')
        for j, (ox, oy) in enumerate(centers):
            if i != j:
                dist = np.sqrt((cx - ox)**2 + (cy - oy)**2)
                min_dist = min(min_dist, dist)
        
        if min_dist >= min_distance:
            color = (0, 255, 0)
            status = "O"
        else:
            color = (0, 0, 255)
            status = "X"
        
        # 회전된 바운딩 박스
        box = cv2.boxPoints(rect)
        box = np.int32(box)
        cv2.drawContours(result, [box], 0, color, 2)
        
        # 중심점
        cv2.circle(result, (cx, cy), 5, color, -1)
        
        # 상태 텍스트
        cv2.putText(result, status, (cx + 10, cy - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        angle = rect[2]
        print(f"블럭 {i+1}: 위치({cx}, {cy}), 각도={angle:.1f}°, 최소거리={min_dist:.1f}px, Picking={status}")
    
    return result, centers

result, centers = check_pickable_blocks(
    r'..\MODEL\data_block\block_8.png',
    min_distance=100,
    padding=20,
    min_area=28000,   # 최소 면적
    max_area=30000   # 최대 면적
)

if result is not None:
    cv2.imwrite('result.png', result)
    cv2.imshow('Result', result)
    cv2.waitKey(0)
    cv2.destroyAllWindows()