"""
비디오 Object Detection
Complete port of Go's ybcore/video_object_detector.go
"""
import asyncio
from typing import List
from PIL import Image
from core.object_detector import YOLODetector, ObjectDetection


class VideoObjectDetector:
    """
    비디오 스트림에서 Object Detection
    Equivalent to Go's VideoObjectDetector struct
    """
    
    def __init__(self, detector: YOLODetector):
        """
        Args:
            detector: YOLODetector 인스턴스
        """
        self.detector = detector
        self.image_queue = asyncio.Queue()
        self.detection_queue = asyncio.Queue()
        self.running = False
        self.image_progressing = False
        self._task = None
    
    async def start(self):
        """
        Object Detection Start
        Same as Go's Start function한 동작
        """
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._detection_loop())
    
    async def _detection_loop(self):
        """
        Object Detection 루프
        Go의 Start 함수 내 goroutine과 동일
        """
        while self.running:
            try:
                # 타임아웃으로 Cleanup 가능하도록
                image = await asyncio.wait_for(self.image_queue.get(), timeout=1.0)
                
                # 이미 Handle 중이면 건너뛰기 (Go의 동작과 동일)
                if self.image_progressing:
                    continue
                
                self.image_progressing = True
                
                # 비동기로 감지 실행
                asyncio.create_task(self._detect_and_send(image))
                
            except asyncio.TimeoutError:
                # 타임아웃은 정상 (running 체크를 위함)
                continue
            except Exception as e:
                print(f"Error in detection loop: {e}")
    
    async def _detect_and_send(self, image: Image.Image):
        """
        감지 실행 및 결과 전송
        Go의 goroutine 내부 로직과 동일
        """
        try:
            # YOLO 감지 (동기 함수를 executor에서 실행)
            loop = asyncio.get_event_loop()
            detections = await loop.run_in_executor(None, self.detector.detect, image)
            
            # 결과 전송
            await self.detection_queue.put(detections)
        except Exception as e:
            print(f"Error detecting objects: {e}")
        finally:
            self.image_progressing = False
    
    async def stop(self):
        """
        Object Detection Stop
        Same as Go's Stop function
        """
        self.running = False
        
        if self._task:
            await self._task
            self._task = None
    
    def get_image_input_queue(self) -> asyncio.Queue:
        """
        이미지 입력 큐 Returns
        Go의 GetImageInputChannel과 동일
        """
        return self.image_queue
    
    def get_detection_result_queue(self) -> asyncio.Queue:
        """
        감지 결과 큐 Returns
        Go의 GetDetectionResultChannel과 동일
        """
        return self.detection_queue
    
    def is_running(self) -> bool:
        """
        실행 상태 확인
        Go의 IsRunning과 동일
        """
        return self.running

