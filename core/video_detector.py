"""
Video Object Detection
Complete port of Go's ybcore/video_object_detector.go
"""
import asyncio
from typing import List
from PIL import Image
from core.object_detector import YOLODetector, ObjectDetection


class VideoObjectDetector:
    """
    Object detection from video stream
    Equivalent to Go's VideoObjectDetector struct
    """
    
    def __init__(self, detector: YOLODetector):
        """
        Args:
            detector: YOLODetector instance
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
        Same behavior as Go's Start function
        """
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._detection_loop())
    
    async def _detection_loop(self):
        """
        Object detection loop
        Same as goroutine in Go's Start function
        """
        while self.running:
            try:
                # Allow cleanup via timeout
                image = await asyncio.wait_for(self.image_queue.get(), timeout=1.0)
                
                # Skip if already handling (same as Go's behavior)
                if self.image_progressing:
                    continue
                
                self.image_progressing = True
                
                # Run detection asynchronously
                asyncio.create_task(self._detect_and_send(image))
                
            except asyncio.TimeoutError:
                # Timeout is normal (for checking running status)
                continue
            except Exception as e:
                print(f"Error in detection loop: {e}")
    
    async def _detect_and_send(self, image: Image.Image):
        """
        Run detection and send results
        Same as logic inside Go's goroutine
        """
        try:
            # YOLO detection (run sync function in executor)
            loop = asyncio.get_event_loop()
            detections = await loop.run_in_executor(None, self.detector.detect, image)
            
            # Send results
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
        Return image input queue
        Same as Go's GetImageInputChannel
        """
        return self.image_queue
    
    def get_detection_result_queue(self) -> asyncio.Queue:
        """
        Return detection result queue
        Same as Go's GetDetectionResultChannel
        """
        return self.detection_queue
    
    def is_running(self) -> bool:
        """
        Check running status
        Same as Go's IsRunning
        """
        return self.running

