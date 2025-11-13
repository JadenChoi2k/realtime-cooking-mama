"""
GPT Vision Detector
Fallback object detection using OpenAI's GPT-4 Vision API
"""
import base64
import io
import json
from typing import List
from PIL import Image
from openai import OpenAI
from core.object_detector import ObjectDetection


class GPTVisionDetector:
    """
    GPT Vision-based object detector for food ingredients
    Used as fallback when YOLO returns empty results
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Args:
            api_key: OpenAI API key
            model: Model name (gpt-4o for vision)
        """
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=api_key)
        
        # System prompt for food ingredient detection
        self.system_prompt = """You are a food ingredient detection system. 
Analyze the image and identify all food ingredients visible.
Focus on raw ingredients like eggs, vegetables, meats, condiments, sauces, bread, etc.
Return ONLY a JSON array with this exact format:
[{"name": "ingredient-name", "confidence": 0.95}]

Rules:
- Use lowercase, hyphenated names (e.g., "brown-egg", "chicken-breast")
- Confidence should be 0.7-1.0 based on visibility and certainty
- Only include items you're confident about
- If no food ingredients visible, return empty array []
"""
    
    def detect(self, image: Image.Image) -> List[ObjectDetection]:
        """
        Detect food ingredients using GPT Vision API
        
        Args:
            image: PIL Image
        
        Returns:
            List of ObjectDetection objects
        """
        try:
            # Convert PIL Image to base64
            image_base64 = self._image_to_base64(image)
            
            # Call GPT Vision API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Identify all food ingredients in this image:"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                    "detail": "low"  # Use low detail for cost optimization
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.3  # Lower temperature for more consistent results
            )
            
            # Parse response
            content = response.choices[0].message.content
            detections = self._parse_response(content, image.size)
            
            print(f"GPT Vision detected {len(detections)} ingredients")
            return detections
            
        except Exception as e:
            print(f"Error in GPT Vision detection: {e}")
            return []
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """
        Convert PIL Image to base64 string
        
        Args:
            image: PIL Image
        
        Returns:
            Base64 encoded string
        """
        # Resize image to reduce API cost (max 512x512 for low detail)
        max_size = 512
        if image.width > max_size or image.height > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Convert to JPEG format
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)
        
        # Encode to base64
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _parse_response(self, content: str, image_size: tuple) -> List[ObjectDetection]:
        """
        Parse GPT Vision response into ObjectDetection list
        
        Args:
            content: Response content from GPT
            image_size: (width, height) of original image
        
        Returns:
            List of ObjectDetection objects
        """
        try:
            # Extract JSON from response (handle markdown code blocks)
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Parse JSON
            ingredients = json.loads(content)
            
            if not isinstance(ingredients, list):
                print(f"Unexpected response format: {content}")
                return []
            
            # Convert to ObjectDetection format
            # Note: GPT Vision doesn't provide bounding boxes,
            # so we use full image dimensions
            detections = []
            width, height = image_size
            
            for item in ingredients:
                if not isinstance(item, dict):
                    continue
                
                name = item.get("name", "").strip()
                confidence = float(item.get("confidence", 0.8))
                
                if not name:
                    continue
                
                # Create ObjectDetection with full image as bounding box
                detection = ObjectDetection(
                    class_name=name,
                    confidence=confidence,
                    x1=0,
                    y1=0,
                    x2=width,
                    y2=height
                )
                detections.append(detection)
            
            return detections
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse GPT Vision response as JSON: {e}")
            print(f"Content: {content}")
            return []
        except Exception as e:
            print(f"Error parsing GPT Vision response: {e}")
            return []

