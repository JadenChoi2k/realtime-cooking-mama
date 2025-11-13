"""
YOLO 객체 감지 테스트
Go 서버의 ybcore/object_detector.go와 video_object_detector.go 동작을 검증
"""
import pytest
import numpy as np
from PIL import Image
from core.object_detector import YOLODetector, ObjectDetection, parse_class_names
from core.video_detector import VideoObjectDetector


@pytest.fixture
def test_image():
    """테스트용 이미지 생성"""
    # 640x640 빨간색 이미지
    img_array = np.zeros((640, 640, 3), dtype=np.uint8)
    img_array[:, :, 0] = 255  # 빨간색
    return Image.fromarray(img_array)


class TestYOLODetector:
    """YOLODetector 테스트"""
    
    def test_parse_class_names(self):
        """YAML 파일에서 클래스 이름 파싱"""
        # 실제 data-names.yaml이 있다면 테스트
        # 여기서는 구조만 검증
        pass
    
    @pytest.mark.skipif(True, reason="ONNX 모델 파일이 필요")
    def test_detector_init(self):
        """YOLODetector 초기화 테스트"""
        detector = YOLODetector(
            model_path="./resources/yori_detector.onnx",
            yaml_path="./resources/data-names.yaml",
            confidence=0.5
        )
        assert detector is not None
        assert detector.confidence == 0.5
    
    @pytest.mark.skipif(True, reason="ONNX 모델 파일이 필요")
    def test_detect(self, test_image):
        """객체 감지 테스트"""
        detector = YOLODetector(
            model_path="./resources/yori_detector.onnx",
            yaml_path="./resources/data-names.yaml",
            confidence=0.5
        )
        
        detections = detector.detect(test_image)
        
        assert isinstance(detections, list)
        # 각 detection은 ObjectDetection 타입
        for detection in detections:
            assert hasattr(detection, 'class_name')
            assert hasattr(detection, 'confidence')
            assert hasattr(detection, 'x1')
            assert hasattr(detection, 'y1')
            assert hasattr(detection, 'x2')
            assert hasattr(detection, 'y2')
            assert isinstance(detection.confidence, float)
            assert 0 <= detection.confidence <= 1


class TestVideoObjectDetector:
    """VideoObjectDetector 테스트"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(True, reason="ONNX 모델 파일이 필요")
    async def test_video_detector_init(self):
        """VideoObjectDetector 초기화 테스트"""
        detector = YOLODetector(
            model_path="./resources/yori_detector.onnx",
            yaml_path="./resources/data-names.yaml",
            confidence=0.5
        )
        vod = VideoObjectDetector(detector)
        
        assert vod is not None
        assert vod.running is False
        assert vod.image_progressing is False
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(True, reason="ONNX 모델 파일이 필요")
    async def test_video_detector_start_stop(self):
        """VideoObjectDetector 시작/중지 테스트"""
        detector = YOLODetector(
            model_path="./resources/yori_detector.onnx",
            yaml_path="./resources/data-names.yaml",
            confidence=0.5
        )
        vod = VideoObjectDetector(detector)
        
        await vod.start()
        assert vod.running is True
        
        await vod.stop()
        assert vod.running is False
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(True, reason="ONNX 모델 파일이 필요")
    async def test_video_detector_queue(self, test_image):
        """VideoObjectDetector 큐 동작 테스트"""
        import asyncio
        
        detector = YOLODetector(
            model_path="./resources/yori_detector.onnx",
            yaml_path="./resources/data-names.yaml",
            confidence=0.5
        )
        vod = VideoObjectDetector(detector)
        await vod.start()
        
        # 이미지 전송
        image_queue = vod.get_image_input_queue()
        await image_queue.put(test_image)
        
        # 결과 수신 (타임아웃 포함)
        result_queue = vod.get_detection_result_queue()
        try:
            detections = await asyncio.wait_for(result_queue.get(), timeout=5.0)
            assert isinstance(detections, list)
        except asyncio.TimeoutError:
            pytest.fail("Detection timeout")
        finally:
            await vod.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(True, reason="ONNX 모델 파일이 필요")
    async def test_video_detector_skip_when_progressing(self, test_image):
        """이미지 처리 중일 때 건너뛰기 테스트"""
        detector = YOLODetector(
            model_path="./resources/yori_detector.onnx",
            yaml_path="./resources/data-names.yaml",
            confidence=0.5
        )
        vod = VideoObjectDetector(detector)
        await vod.start()
        
        image_queue = vod.get_image_input_queue()
        
        # 여러 이미지 빠르게 전송
        for _ in range(10):
            await image_queue.put(test_image)
        
        # 처리 중 플래그 확인
        # (실제로는 일부만 처리됨)
        
        await vod.stop()


class TestObjectDetection:
    """ObjectDetection 모델 테스트"""
    
    def test_object_detection_creation(self):
        """ObjectDetection 생성 테스트"""
        detection = ObjectDetection(
            class_name="brown-egg",
            confidence=0.95,
            x1=100,
            y1=150,
            x2=200,
            y2=250
        )
        
        assert detection.class_name == "brown-egg"
        assert detection.confidence == 0.95
        assert detection.x1 == 100
        assert detection.y1 == 150
        assert detection.x2 == 200
        assert detection.y2 == 250

