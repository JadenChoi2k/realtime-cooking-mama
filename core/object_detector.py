"""
YOLO 객체 감지
Go의 ybcore/object_detector.go를 Ultralytics로 대체
"""
from typing import List
import yaml
from PIL import Image
from pydantic import BaseModel
from ultralytics import YOLO


class ObjectDetection(BaseModel):
    """
    객체 감지 결과
    Go의 ObjectDetection 구조체와 동일
    """
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int


def parse_class_names(yaml_path: str) -> List[str]:
    """
    YAML 파일에서 클래스 이름 파싱
    Go의 ParseClassNames 함수와 동일
    
    Args:
        yaml_path: YAML 파일 경로
    
    Returns:
        클래스 이름 리스트
    """
    with open(yaml_path, 'r', encoding='utf-8') as f:
        yaml_data = yaml.safe_load(f)
    
    names_dict = yaml_data.get('names', {})
    
    # 인덱스 순서대로 정렬
    class_names = []
    for idx in sorted(names_dict.keys()):
        class_names.append(names_dict[idx])
    
    return class_names


class YOLODetector:
    """
    YOLO 객체 감지기
    Go의 YOLODetector를 Ultralytics로 대체
    """
    
    def __init__(self, model_path: str, yaml_path: str, confidence: float):
        """
        Args:
            model_path: ONNX 모델 경로
            yaml_path: 클래스 이름 YAML 경로
            confidence: confidence threshold
        """
        self.model = YOLO(model_path)
        self.class_names = parse_class_names(yaml_path)
        self.confidence = confidence
    
    def detect(self, image: Image.Image) -> List[ObjectDetection]:
        """
        이미지에서 객체 감지
        Go의 Detect 함수와 동일한 출력
        
        Args:
            image: PIL Image
        
        Returns:
            ObjectDetection 리스트
        """
        # Ultralytics YOLO 추론
        results = self.model(image, conf=self.confidence, verbose=False)
        
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()
                
                # 클래스 이름 가져오기
                if cls_id < len(self.class_names):
                    class_name = self.class_names[cls_id]
                else:
                    class_name = f"class_{cls_id}"
                
                detection = ObjectDetection(
                    class_name=class_name,
                    confidence=conf,
                    x1=int(xyxy[0]),
                    y1=int(xyxy[1]),
                    x2=int(xyxy[2]),
                    y2=int(xyxy[3])
                )
                detections.append(detection)
        
        return detections

