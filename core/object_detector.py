"""
YOLO Object Detection
Go's ybcore/object_detector.go replaced with Ultralytics
"""
from typing import List
import yaml
from PIL import Image
from pydantic import BaseModel
from ultralytics import YOLO


class ObjectDetection(BaseModel):
    """
    Object Detection result
    Equivalent to Go's ObjectDetection struct
    """
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int


def parse_class_names(yaml_path: str) -> List[str]:
    """
    Parse class names from YAML file
    Same as Go's ParseClassNames function
    
    Args:
        yaml_path: YAML file path
    
    Returns:
        List of class names
    """
    with open(yaml_path, 'r', encoding='utf-8') as f:
        yaml_data = yaml.safe_load(f)
    
    names_dict = yaml_data.get('names', {})
    
    # Sort by index order
    class_names = []
    for idx in sorted(names_dict.keys()):
        class_names.append(names_dict[idx])
    
    return class_names


class YOLODetector:
    """
    YOLO Object Detector
    Go's YOLODetector replaced with Ultralytics
    """
    
    def __init__(self, model_path: str, yaml_path: str, confidence: float):
        """
        Args:
            model_path: ONNX model path
            yaml_path: Class name YAML path
            confidence: confidence threshold
        """
        self.model = YOLO(model_path)
        self.class_names = parse_class_names(yaml_path)
        self.confidence = confidence
    
    def detect(self, image: Image.Image) -> List[ObjectDetection]:
        """
        Detect objects in image
        Same output as Go's Detect function
        
        Args:
            image: PIL Image
        
        Returns:
            List of ObjectDetection
        """
        # Ultralytics YOLO inference
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
                
                # Get class name
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

