"""
Video Object Detection
Complete port of Go's ybcore/video_object_detector.go
"""
import asyncio
import time
from asyncio import QueueEmpty
from typing import List, Optional
from PIL import Image
from core.object_detector import YOLODetector, ObjectDetection


class VideoObjectDetector:
    """
    Object detection from video stream
    Equivalent to Go's VideoObjectDetector struct
    Now with GPT Vision fallback support
    """
    
    def __init__(self, detector: YOLODetector, fallback_detector=None, gpt_throttle_seconds: float = 2.5):
        """
        Args:
            detector: YOLODetector instance
            fallback_detector: Optional GPTVisionDetector for fallback
            gpt_throttle_seconds: Minimum seconds between GPT Vision calls (default 5.0)
        """
        self.detector = detector
        self.fallback_detector = fallback_detector
        self.gpt_throttle_seconds = gpt_throttle_seconds
        self.last_gpt_call_time = 0.0
        self.image_queue = asyncio.Queue()
        self.detection_queue = asyncio.Queue()
        self.running = False
        self.image_progressing = False
        self._task = None
        self.gpt_processing = False
    
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
        Now with GPT Vision fallback when YOLO returns empty
        """
        try:
            # YOLO detection (run sync function in executor)
            loop = asyncio.get_event_loop()
            detections = await loop.run_in_executor(None, self.detector.detect, image)
            
            # If empty and fallback available, check throttle
            if len(detections) == 0 and self.fallback_detector is not None:
                current_time = time.time()
                time_since_last_call = current_time - self.last_gpt_call_time
                
                if time_since_last_call >= self.gpt_throttle_seconds:
                    print(f"YOLO returned empty, calling GPT Vision fallback (last call: {time_since_last_call:.1f}s ago)")
                    self.gpt_processing = True
                    self._clear_pending_images()
                    try:
                        detections = await loop.run_in_executor(None, self.fallback_detector.detect, image)
                        self.last_gpt_call_time = current_time
                    finally:
                        self.gpt_processing = False
                else:
                    print(f"YOLO returned empty, but GPT throttled (last call: {time_since_last_call:.1f}s ago)")
            
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

    def is_gpt_processing(self) -> bool:
        """
        Whether GPT Vision fallback is currently running.
        Used so higher layers can pause frame ingestion while GPT is busy.
        """
        return self.gpt_processing

    def _clear_pending_images(self):
        """
        Drop any frames that piled up while YOLO was running.
        Prevents a backlog of stale frames once GPT fallback kicks in so audio loops keep up.
        """
        cleared = 0
        while True:
            try:
                self.image_queue.get_nowait()
                cleared += 1
            except QueueEmpty:
                break
        if cleared:
            print(f"Cleared {cleared} pending frames before GPT Vision fallback")

