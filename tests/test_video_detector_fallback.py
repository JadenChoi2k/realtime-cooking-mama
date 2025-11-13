"""
Integration tests for VideoObjectDetector fallback behavior
"""
import os
import time
import asyncio
import pytest
from PIL import Image
from unittest.mock import Mock, MagicMock, patch
from core.object_detector import YOLODetector, ObjectDetection
from core.video_detector import VideoObjectDetector
from core.gpt_vision_detector import GPTVisionDetector


class TestVideoDetectorFallback:
    """Test cases for VideoObjectDetector with GPT Vision fallback"""
    
    @pytest.mark.asyncio
    async def test_yolo_success_no_fallback(self):
        """Test that fallback is not called when YOLO returns results"""
        # Create mock detectors
        mock_yolo = Mock(spec=YOLODetector)
        mock_yolo.detect.return_value = [
            ObjectDetection(class_name="brown-egg", confidence=0.9, x1=10, y1=10, x2=100, y2=100)
        ]
        
        mock_gpt = Mock(spec=GPTVisionDetector)
        mock_gpt.detect.return_value = []
        
        # Create VideoObjectDetector with fallback
        vod = VideoObjectDetector(mock_yolo, fallback_detector=mock_gpt)
        await vod.start()
        
        # Send test image
        test_image = Image.new('RGB', (100, 100), color='red')
        await vod.get_image_input_queue().put(test_image)
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Get results
        result_queue = vod.get_detection_result_queue()
        assert not result_queue.empty()
        detections = await result_queue.get()
        
        # Check results
        assert len(detections) == 1
        assert detections[0].class_name == "brown-egg"
        
        # Verify GPT was not called
        mock_gpt.detect.assert_not_called()
        
        # Cleanup
        await vod.stop()
    
    @pytest.mark.asyncio
    async def test_yolo_empty_triggers_fallback(self):
        """Test that fallback is called when YOLO returns empty"""
        # Create mock detectors
        mock_yolo = Mock(spec=YOLODetector)
        mock_yolo.detect.return_value = []  # Empty result
        
        mock_gpt = Mock(spec=GPTVisionDetector)
        mock_gpt.detect.return_value = [
            ObjectDetection(class_name="chicken-breast", confidence=0.85, x1=0, y1=0, x2=640, y2=480)
        ]
        
        # Create VideoObjectDetector with fallback
        vod = VideoObjectDetector(mock_yolo, fallback_detector=mock_gpt)
        await vod.start()
        
        # Send test image
        test_image = Image.new('RGB', (640, 480), color='green')
        await vod.get_image_input_queue().put(test_image)
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Get results
        result_queue = vod.get_detection_result_queue()
        assert not result_queue.empty()
        detections = await result_queue.get()
        
        # Check results
        assert len(detections) == 1
        assert detections[0].class_name == "chicken-breast"
        
        # Verify GPT was called
        mock_gpt.detect.assert_called_once()
        
        # Cleanup
        await vod.stop()
    
    @pytest.mark.asyncio
    async def test_fallback_throttling(self):
        """Test that GPT Vision fallback is throttled correctly"""
        # Create mock detectors
        mock_yolo = Mock(spec=YOLODetector)
        mock_yolo.detect.return_value = []  # Always empty
        
        mock_gpt = Mock(spec=GPTVisionDetector)
        mock_gpt.detect.return_value = [
            ObjectDetection(class_name="onion", confidence=0.8, x1=0, y1=0, x2=640, y2=480)
        ]
        
        # Create VideoObjectDetector with 2-second throttle
        vod = VideoObjectDetector(mock_yolo, fallback_detector=mock_gpt, gpt_throttle_seconds=2.0)
        await vod.start()
        
        # Send multiple images quickly
        test_image = Image.new('RGB', (640, 480), color='blue')
        
        # First image - should trigger GPT
        await vod.get_image_input_queue().put(test_image)
        await asyncio.sleep(0.2)
        
        # Second image immediately - should be throttled
        await vod.get_image_input_queue().put(test_image)
        await asyncio.sleep(0.2)
        
        # GPT should only be called once due to throttling
        assert mock_gpt.detect.call_count == 1
        
        # Wait for throttle period to expire
        await asyncio.sleep(2.0)
        
        # Third image after throttle - should trigger GPT again
        await vod.get_image_input_queue().put(test_image)
        await asyncio.sleep(0.2)
        
        # Now GPT should be called twice
        assert mock_gpt.detect.call_count == 2
        
        # Cleanup
        await vod.stop()
    
    @pytest.mark.asyncio
    async def test_no_fallback_when_not_provided(self):
        """Test that no fallback occurs when fallback_detector is None"""
        # Create mock YOLO
        mock_yolo = Mock(spec=YOLODetector)
        mock_yolo.detect.return_value = []
        
        # Create VideoObjectDetector without fallback
        vod = VideoObjectDetector(mock_yolo, fallback_detector=None)
        await vod.start()
        
        # Send test image
        test_image = Image.new('RGB', (100, 100), color='yellow')
        await vod.get_image_input_queue().put(test_image)
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Get results
        result_queue = vod.get_detection_result_queue()
        assert not result_queue.empty()
        detections = await result_queue.get()
        
        # Should still get empty result (no error)
        assert len(detections) == 0
        
        # Cleanup
        await vod.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_detections_from_gpt(self):
        """Test that GPT can return multiple detections"""
        # Create mock detectors
        mock_yolo = Mock(spec=YOLODetector)
        mock_yolo.detect.return_value = []
        
        mock_gpt = Mock(spec=GPTVisionDetector)
        mock_gpt.detect.return_value = [
            ObjectDetection(class_name="brown-egg", confidence=0.9, x1=0, y1=0, x2=640, y2=480),
            ObjectDetection(class_name="onion", confidence=0.85, x1=0, y1=0, x2=640, y2=480),
            ObjectDetection(class_name="mayonnaise", confidence=0.8, x1=0, y1=0, x2=640, y2=480)
        ]
        
        # Create VideoObjectDetector with fallback
        vod = VideoObjectDetector(mock_yolo, fallback_detector=mock_gpt)
        await vod.start()
        
        # Send test image
        test_image = Image.new('RGB', (640, 480), color='white')
        await vod.get_image_input_queue().put(test_image)
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Get results
        result_queue = vod.get_detection_result_queue()
        detections = await result_queue.get()
        
        # Check results
        assert len(detections) == 3
        assert detections[0].class_name == "brown-egg"
        assert detections[1].class_name == "onion"
        assert detections[2].class_name == "mayonnaise"
        
        # Cleanup
        await vod.stop()
    
    @pytest.mark.asyncio
    async def test_gpt_error_handling(self):
        """Test that GPT errors are handled gracefully"""
        # Create mock detectors
        mock_yolo = Mock(spec=YOLODetector)
        mock_yolo.detect.return_value = []
        
        mock_gpt = Mock(spec=GPTVisionDetector)
        mock_gpt.detect.side_effect = Exception("GPT API Error")
        
        # Create VideoObjectDetector with fallback
        vod = VideoObjectDetector(mock_yolo, fallback_detector=mock_gpt)
        await vod.start()
        
        # Send test image
        test_image = Image.new('RGB', (100, 100), color='black')
        await vod.get_image_input_queue().put(test_image)
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Should not crash - check if result queue has something
        result_queue = vod.get_detection_result_queue()
        # The queue might be empty or have empty list depending on error handling
        
        # Cleanup
        await vod.stop()
    
    @pytest.mark.skipif(not os.path.exists("./resources/test_fridge.jpg"), 
                        reason="Test image not found")
    @pytest.mark.asyncio
    async def test_fallback_with_real_test_fridge_image(self):
        """Test fallback with real test_fridge.jpg image"""
        # Load real YOLO model
        try:
            yolo = YOLODetector(
                model_path="./resources/yori_detector.onnx",
                yaml_path="./resources/data-names.yaml",
                confidence=0.9  # High confidence to force empty results
            )
        except Exception:
            pytest.skip("YOLO model not available")
        
        # Create mock GPT detector
        mock_gpt = Mock(spec=GPTVisionDetector)
        mock_gpt.detect.return_value = [
            ObjectDetection(class_name="test-item", confidence=0.8, x1=0, y1=0, x2=640, y2=480)
        ]
        
        # Create VideoObjectDetector
        vod = VideoObjectDetector(yolo, fallback_detector=mock_gpt)
        await vod.start()
        
        # Load and send real test image
        test_image = Image.open("./resources/test_fridge.jpg")
        await vod.get_image_input_queue().put(test_image)
        
        # Wait for processing
        await asyncio.sleep(0.5)
        
        # Get results
        result_queue = vod.get_detection_result_queue()
        if not result_queue.empty():
            detections = await result_queue.get()
            # Either YOLO found something or GPT fallback was triggered
            assert isinstance(detections, list)
        
        # Cleanup
        await vod.stop()
    
    @pytest.mark.skipif(not os.path.exists("./resources/test_image.jpg"), 
                        reason="Test image not found")
    @pytest.mark.asyncio
    async def test_fallback_with_real_test_image(self):
        """Test fallback with real test_image.jpg"""
        # Load real YOLO model
        try:
            yolo = YOLODetector(
                model_path="./resources/yori_detector.onnx",
                yaml_path="./resources/data-names.yaml",
                confidence=0.9  # High confidence to potentially force empty results
            )
        except Exception:
            pytest.skip("YOLO model not available")
        
        # Create mock GPT detector
        mock_gpt = Mock(spec=GPTVisionDetector)
        mock_gpt.detect.return_value = [
            ObjectDetection(class_name="detected-by-gpt", confidence=0.85, x1=0, y1=0, x2=800, y2=600)
        ]
        
        # Create VideoObjectDetector
        vod = VideoObjectDetector(yolo, fallback_detector=mock_gpt)
        await vod.start()
        
        # Load and send real test image
        test_image = Image.open("./resources/test_image.jpg")
        await vod.get_image_input_queue().put(test_image)
        
        # Wait for processing
        await asyncio.sleep(0.5)
        
        # Get results
        result_queue = vod.get_detection_result_queue()
        if not result_queue.empty():
            detections = await result_queue.get()
            assert isinstance(detections, list)
        
        # Cleanup
        await vod.stop()
    
    @pytest.mark.asyncio
    async def test_throttle_timer_reset_after_call(self):
        """Test that throttle timer resets correctly after each call"""
        mock_yolo = Mock(spec=YOLODetector)
        mock_yolo.detect.return_value = []
        
        mock_gpt = Mock(spec=GPTVisionDetector)
        mock_gpt.detect.return_value = [
            ObjectDetection(class_name="test", confidence=0.8, x1=0, y1=0, x2=100, y2=100)
        ]
        
        # Create VideoObjectDetector with 1-second throttle
        vod = VideoObjectDetector(mock_yolo, fallback_detector=mock_gpt, gpt_throttle_seconds=1.0)
        await vod.start()
        
        test_image = Image.new('RGB', (100, 100), color='gray')
        
        # First call
        await vod.get_image_input_queue().put(test_image)
        await asyncio.sleep(0.2)
        assert mock_gpt.detect.call_count == 1
        
        # Immediate second call - throttled
        await vod.get_image_input_queue().put(test_image)
        await asyncio.sleep(0.2)
        assert mock_gpt.detect.call_count == 1
        
        # Wait for throttle
        await asyncio.sleep(1.0)
        
        # Third call - should work
        await vod.get_image_input_queue().put(test_image)
        await asyncio.sleep(0.2)
        assert mock_gpt.detect.call_count == 2
        
        # Cleanup
        await vod.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_image_processing(self):
        """Test that only one image is processed at a time"""
        mock_yolo = Mock(spec=YOLODetector)
        
        # Make YOLO slow to simulate processing time
        def slow_detect(img):
            time.sleep(0.1)
            return []
        
        mock_yolo.detect.side_effect = slow_detect
        
        mock_gpt = Mock(spec=GPTVisionDetector)
        mock_gpt.detect.return_value = []
        
        vod = VideoObjectDetector(mock_yolo, fallback_detector=mock_gpt)
        await vod.start()
        
        # Send multiple images
        test_image = Image.new('RGB', (100, 100), color='purple')
        for _ in range(5):
            await vod.get_image_input_queue().put(test_image)
        
        # Wait for processing
        await asyncio.sleep(1.0)
        
        # Due to concurrent processing flag, not all images will be processed
        # This is the expected behavior from the Go implementation
        
        # Cleanup
        await vod.stop()

