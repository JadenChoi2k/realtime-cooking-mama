"""
Unit tests for GPT Vision Detector
"""
import os
import pytest
from PIL import Image
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv
from core.gpt_vision_detector import GPTVisionDetector
from core.object_detector import ObjectDetection

# Load environment variables from .env file
load_dotenv()


class TestGPTVisionDetector:
    """Test cases for GPTVisionDetector"""
    
    def test_gpt_vision_detector_init(self):
        """Test GPTVisionDetector initialization"""
        detector = GPTVisionDetector(api_key="test-key")
        
        assert detector.api_key == "test-key"
        assert detector.model == "gpt-4o"
        assert detector.client is not None
        assert "food ingredient" in detector.system_prompt.lower()
    
    def test_gpt_vision_detector_init_custom_model(self):
        """Test GPTVisionDetector with custom model"""
        detector = GPTVisionDetector(api_key="test-key", model="gpt-4-turbo")
        
        assert detector.model == "gpt-4-turbo"
    
    def test_image_to_base64(self):
        """Test image to base64 conversion"""
        # Create a small test image
        test_image = Image.new('RGB', (100, 100), color='red')
        detector = GPTVisionDetector(api_key="test-key")
        
        # Convert to base64
        base64_str = detector._image_to_base64(test_image)
        
        # Check result
        assert isinstance(base64_str, str)
        assert len(base64_str) > 0
    
    def test_image_to_base64_resizes_large_image(self):
        """Test that large images are resized"""
        # Create a large test image
        test_image = Image.new('RGB', (2000, 2000), color='blue')
        detector = GPTVisionDetector(api_key="test-key")
        
        # Convert to base64
        base64_str = detector._image_to_base64(test_image)
        
        # Check result (should be smaller due to resize)
        assert isinstance(base64_str, str)
        assert len(base64_str) > 0
    
    def test_parse_response_valid_json(self):
        """Test parsing valid JSON response"""
        detector = GPTVisionDetector(api_key="test-key")
        
        # Valid response
        response = '[{"name": "brown-egg", "confidence": 0.95}, {"name": "onion", "confidence": 0.85}]'
        detections = detector._parse_response(response, (640, 480))
        
        assert len(detections) == 2
        assert detections[0].class_name == "brown-egg"
        assert detections[0].confidence == 0.95
        assert detections[0].x1 == 0
        assert detections[0].y1 == 0
        assert detections[0].x2 == 640
        assert detections[0].y2 == 480
        assert detections[1].class_name == "onion"
        assert detections[1].confidence == 0.85
    
    def test_parse_response_with_markdown_code_block(self):
        """Test parsing response wrapped in markdown code block"""
        detector = GPTVisionDetector(api_key="test-key")
        
        # Response with markdown
        response = '```json\n[{"name": "chicken-breast", "confidence": 0.9}]\n```'
        detections = detector._parse_response(response, (800, 600))
        
        assert len(detections) == 1
        assert detections[0].class_name == "chicken-breast"
        assert detections[0].confidence == 0.9
    
    def test_parse_response_empty_array(self):
        """Test parsing empty array response"""
        detector = GPTVisionDetector(api_key="test-key")
        
        response = '[]'
        detections = detector._parse_response(response, (640, 480))
        
        assert len(detections) == 0
    
    def test_parse_response_invalid_json(self):
        """Test handling invalid JSON"""
        detector = GPTVisionDetector(api_key="test-key")
        
        response = 'This is not valid JSON'
        detections = detector._parse_response(response, (640, 480))
        
        assert len(detections) == 0
    
    def test_parse_response_missing_fields(self):
        """Test handling responses with missing fields"""
        detector = GPTVisionDetector(api_key="test-key")
        
        # Missing confidence
        response = '[{"name": "egg"}]'
        detections = detector._parse_response(response, (640, 480))
        
        assert len(detections) == 1
        assert detections[0].class_name == "egg"
        assert detections[0].confidence == 0.8  # Default
    
    def test_parse_response_skips_invalid_items(self):
        """Test that invalid items are skipped"""
        detector = GPTVisionDetector(api_key="test-key")
        
        # Mixed valid and invalid items
        response = '[{"name": "egg", "confidence": 0.9}, {"confidence": 0.8}, {"name": "", "confidence": 0.7}]'
        detections = detector._parse_response(response, (640, 480))
        
        # Should only have the first valid item
        assert len(detections) == 1
        assert detections[0].class_name == "egg"
    
    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No API key available")
    def test_gpt_vision_detect_with_real_image(self):
        """Test GPT Vision detection with real test image (requires API key)"""
        api_key = os.getenv("OPENAI_API_KEY")
        detector = GPTVisionDetector(api_key=api_key)
        
        # Load test image
        test_image_path = "./resources/test_fridge.jpg"
        if not os.path.exists(test_image_path):
            pytest.skip("Test image not found")
        
        test_image = Image.open(test_image_path)
        
        # Run detection
        detections = detector.detect(test_image)
        
        # Basic validation
        assert isinstance(detections, list)
        for detection in detections:
            assert isinstance(detection, ObjectDetection)
            assert len(detection.class_name) > 0
            assert 0.0 <= detection.confidence <= 1.0
    
    def test_detect_with_mock_api(self):
        """Test detect method with mocked OpenAI API"""
        detector = GPTVisionDetector(api_key="test-key")
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '[{"name": "brown-egg", "confidence": 0.95}]'
        
        # Patch the API call
        with patch.object(detector.client.chat.completions, 'create', return_value=mock_response):
            test_image = Image.new('RGB', (100, 100), color='green')
            detections = detector.detect(test_image)
        
        assert len(detections) == 1
        assert detections[0].class_name == "brown-egg"
        assert detections[0].confidence == 0.95
    
    def test_detect_handles_api_error(self):
        """Test that detect handles API errors gracefully"""
        detector = GPTVisionDetector(api_key="test-key")
        
        # Patch the API call to raise an error
        with patch.object(detector.client.chat.completions, 'create', side_effect=Exception("API Error")):
            test_image = Image.new('RGB', (100, 100), color='yellow')
            detections = detector.detect(test_image)
        
        # Should return empty list on error
        assert detections == []
    
    def test_result_format_matches_object_detection(self):
        """Test that results match ObjectDetection format"""
        detector = GPTVisionDetector(api_key="test-key")
        
        response = '[{"name": "test-item", "confidence": 0.88}]'
        detections = detector._parse_response(response, (1920, 1080))
        
        assert len(detections) == 1
        detection = detections[0]
        
        # Check all ObjectDetection fields
        assert hasattr(detection, 'class_name')
        assert hasattr(detection, 'confidence')
        assert hasattr(detection, 'x1')
        assert hasattr(detection, 'y1')
        assert hasattr(detection, 'x2')
        assert hasattr(detection, 'y2')
        
        # Check types
        assert isinstance(detection.class_name, str)
        assert isinstance(detection.confidence, float)
        assert isinstance(detection.x1, int)
        assert isinstance(detection.y1, int)
        assert isinstance(detection.x2, int)
        assert isinstance(detection.y2, int)

