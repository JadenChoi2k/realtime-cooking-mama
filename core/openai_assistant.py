"""
OpenAI Assistant (레시피 추천용)
Go의 ybcore/assistant.go 일부 + yori_recipe.go의 RecommendRecipe 복제
"""
from typing import List
import json
from openai import OpenAI
from core.fridge import FridgeItem


# Go의 recommendPrompt를 완벽히 복제
RECOMMEND_PROMPT = """당신은 사용자 맥락과, 냉장고 재고 목록을 통해서 사용자에게 적합한 레시피 최소 0개, 최대 5개를 추천해줘야 합니다. 레시피 목록 info가 주어집니다. 그 중에서 선택하도록 합니다. 입력으로는 사용자의 현재 냉장고 재고 상태가, 그리고 사용자의 맥락이 주어집니다. 그리고 이를 통해 추천 레시피 목록을 추천해줍니다. 레시피 목록은 next과 같습니다. 

**레시피 목록 Start**
{
  "food_ingredients": [
    {
      "id": "brown-egg",
      "name": "달걀",
      "is_in_fridge": true
    },
    {
      "id": "crab-meat",
      "name": "게맛살",
      "is_in_fridge": true
    },
    {
      "id": "morning-roll",
      "name": "모닝빵",
      "is_in_fridge": false
    },
    {
      "id": "honey-mustard",
      "name": "허니 머스타드",
      "is_in_fridge": true
    },
    {
      "id": "mayonnaise",
      "name": "마요네즈",
      "is_in_fridge": true
    },
    {
      "id": "onion",
      "name": "양파",
      "is_in_fridge": true
    },
    {
      "id": "strawberry-jam",
      "name": "딸기잼",
      "is_in_fridge": true
    },
    {
      "id": "sweet-relish",
      "name": "스위트 렐리시",
      "is_in_fridge": true
    },
    {
      "id": "white-egg",
      "name": "삶은 달걀",
      "is_in_fridge": true
    },
    {
      "id": "chicken-breast",
      "name": "닭가슴살",
      "is_in_fridge": true
    },
    {
      "id": "salt",
      "name": "소금",
      "is_in_fridge": false
    },
    {
      "id": "pepper",
      "name": "후추",
      "is_in_fridge": false
    },
    {
      "id": "spring-onion",
      "name": "파",
      "is_in_fridge": true
    },
    {
      "id": "rice",
      "name": "밥",
      "is_in_fridge": false
    },
    {
      "id": "cooking-oil",
      "name": "식용유",
      "is_in_fridge": false
    },
    {
      "id": "soy-sauce",
      "name": "간장",
      "is_in_fridge": false
    },
    {
      "id": "oyster-sauce",
      "name": "굴소스",
      "is_in_fridge": false
    }
  ],
  "recipes": [
    {
      "id": 1,
      "name": "게살 샌드위치",
      "time": 10,
      "description": "게맛살의 크리미한 식감과 허니 머스타드의 달콤함이 만나 더욱 풍부한 맛을 즐길 수 있어요!",
      "ingredients": [
        {
          "id": "morning-roll",
          "quantity": 2,
          "unit": "개",
          "required": true
        },
        {
          "id": "sweet-relish",
          "quantity": 1,
          "unit": "T",
          "required": true
        },
        {
          "id": "onion",
          "quantity": 1,
          "unit": "/4",
          "required": true
        },
        {
          "id": "crab-meat",
          "quantity": 4,
          "unit": "ea",
          "required": true
        },
        {
          "id": "mayonnaise",
          "quantity": 4,
          "unit": "T",
          "required": true
        },
        {
          "id": "honey-mustard",
          "quantity": 2,
          "unit": "T",
          "required": true
        },
        {
          "id": "salt",
          "quantity": 1,
          "unit": "조금",
          "required": false
        },
        {
          "id": "pepper",
          "quantity": 1,
          "unit": "조금",
          "required": false
        }
      ]
    },
    {
      "id": 2,
      "time": 20,
      "name": "에그마요 샌드위치",
      "description": "에그 샌드위치 한 입이면 부드러운 달걀과 크리미한 마요네즈가 입안에서 폭발하며 감칠맛이 쫙쫙 살아나요! 배고플 때 딱 한 입만으로도 든든함과 기운이 확↗ 차오르는 간식!",
      "ingredients": [
        {
          "id": "morning-roll",
          "quantity": 2,
          "unit": "개",
          "required": true
        },
        {
          "id": "white-egg",
          "quantity": 2,
          "unit": "개",
          "required": true
        },
        {
          "id": "onion",
          "quantity": 1,
          "unit": "/4",
          "required": true
        },
        {
          "id": "honey-mustard",
          "quantity": 2,
          "unit": "T",
          "required": true
        },
        {
          "id": "mayonnaise",
          "quantity": 3,
          "unit": "T",
          "required": true
        },
        {
          "id": "sweet-relish",
          "quantity": 1,
          "unit": "T",
          "required": false
        }
      ]
    },
    {
      "id": 3,
      "time": 10,
      "name": "계란말이",
      "description": "계란을 넣어 만든 계란말이는 달걀의 풍부한 영양소와 맛을 즐길 수 있어요!",
      "ingredients": [
        {
          "id": "brown-egg",
          "quantity": 4,
          "unit": "개",
          "required": true
        },
        {
          "id": "spring-onion",
          "quantity": 1,
          "unit": "개",
          "required": false
        },
        {
          "id": "salt",
          "quantity": 1,
          "unit": "조금",
          "required": false
        },
        {
          "id": "cooking-oil",
          "quantity": 1,
          "unit": "T",
          "required": true
        }
      ]
    },
    {
      "id": 4,
      "time": 20,
      "name": "계란 볶음밥",
      "description": "계란을 넣어 만든 계란볶음밥은 달걀의 풍부한 영양소와 맛을 즐길 수 있어요!",
      "ingredients": [
        {
          "id": "brown-egg",
          "quantity": 2,
          "unit": "개",
          "required": true
        },
        {
          "id": "spring-onion",
          "quantity": 1,
          "unit": "개",
          "required": true
        },
        {
          "id": "cooking-oil",
          "quantity": 1,
          "unit": "T",
          "required": true
        },
        {
          "id": "rice",
          "quantity": 1,
          "unit": "공기",
          "required": true
        },
        {
          "id": "salt",
          "quantity": 1,
          "unit": "조금",
          "required": false
        },
        {
          "id": "soy-sauce",
          "quantity": 1,
          "unit": "T",
          "required": false
        },
        {
          "id": "oyster-sauce",
          "quantity": 1,
          "unit": "T",
          "required": false
        }
      ]
    },
    {
      "id": 5,
      "time": 15,
      "name": "황금 볶음밥",
      "description": "계란을 넣어 만든 황금 볶음밥은 달걀의 풍부한 영양소와 맛을 즐길 수 있어요!",
      "ingredients": [
        {
          "id": "brown-egg",
          "quantity": 2,
          "unit": "개",
          "required": true
        },
        {
          "id": "soy-sauce",
          "quantity": 1,
          "unit": "T",
          "required": false
        },
        {
          "id": "oyster-sauce",
          "quantity": 1,
          "unit": "T",
          "required": false
        },
        {
          "id": "salt",
          "quantity": 1,
          "unit": "조금",
          "required": false
        },
        {
          "id": "rice",
          "quantity": 1,
          "unit": "공기",
          "required": true
        },
        {
          "id": "cooking-oil",
          "quantity": 1,
          "unit": "T",
          "required": true
        }
      ]
    },
    {
      "id": 6,
      "time": 30,
      "name": "닭가슴살 샌드위치",
      "description": "닭가슴살을 넣어 만든 닭가슴살 샌드위치는 닭가슴살의 풍부한 영양소와 맛을 즐길 수 있어요!",
      "ingredients": [
        {
          "id": "chicken-breast",
          "quantity": 1,
          "unit": "개",
          "required": true
        },
        {
          "id": "honey-mustard",
          "quantity": 1,
          "unit": "T",
          "required": true
        },
        {
          "id": "mayonnaise",
          "quantity": 1,
          "unit": "T",
          "required": true
        },
        {
          "id": "sweet-relish",
          "quantity": 1,
          "unit": "T",
          "required": true
        },
        {
          "id": "onion",
          "quantity": 1,
          "unit": "/2",
          "required": true
        }
      ]
    },
    {
      "id": 7,
      "time": 30,
      "name": "닭가슴살 볶음밥",
      "description": "닭가슴살을 넣어 만든 닭가슴살 볶음밥은 닭가슴살의 풍부한 영양소와 맛을 즐길 수 있어요!",
      "ingredients": [
        {
          "id": "chicken-breast",
          "quantity": 1,
          "unit": "개",
          "required": true
        },
        {
          "id": "soy-sauce",
          "quantity": 1,
          "unit": "T",
          "required": false
        },
        {
          "id": "salt",
          "quantity": 1,
          "unit": "조금",
          "required": false
        },
        {
          "id": "rice",
          "quantity": 1,
          "unit": "공기",
          "required": true
        },
        {
          "id": "cooking-oil",
          "quantity": 1,
          "unit": "T",
          "required": true
        }
      ]
    }
  ]
}
**레시피 목록 끝**

**입력 형식**
1. 냉장고 재고 상태. 데이터 list가 주어집니다.
2. 맥락: 사용자의 현재 맥락 info가 텍스트로 주어집니다.

**유의 사항**
1. 사용자는 현재 냉장고를 둘러보는 상황입니다. 따라서 is_in_fridge가 false인 식재료 경우, 사용자가 해당 재료를 이미 가지고 있다고 판단합니다.
2. required 값이 false인 식재료는 냉장고 재고 상황에서 고려하지 않습니다.
3. 현재 냉장고 재고 상태에 적합한 레시피를 추천합니다.
4. 추천 레시피는 레시피 아이디 목록으로 Returns합니다. 주어진 레시피 내에서만 고르십시오.
5. 게맛살이 있는 경우 게살 샌드위치를 포함하여 추천합니다.

이제부터 당신은 냉장고 재료를 통해 사용자에게 추천 레시피를 전달할 준비가 되었습니다."""


class OpenAIAssistant:
    """
    OpenAI Assistant (레시피 추천용)
    Go의 OpenAIAssistant 일부 기능 구현
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Args:
            api_key: OpenAI API 키
            model: 모델 이름
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = ""
    
    def set_system_prompt(self, prompt: str):
        """시스템 프롬프트 설정"""
        self.system_prompt = prompt
    
    async def handle_with_json(self, message: str, response_format: dict) -> str:
        """
        Structured Output을 사용한 요청
        Go의 HandleWithJSON과 동일
        
        Args:
            message: 사용자 메시지
            response_format: JSON 스키마
        
        Returns:
            JSON string
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": message}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": response_format
            }
        )
        
        return response.choices[0].message.content


async def recommend_recipe(openai_key: str, fridge_items: List[FridgeItem], context: str) -> List[int]:
    """
    레시피 추천
    Complete port of Go's RecommendRecipe 함수
    
    Args:
        openai_key: OpenAI API 키
        fridge_items: 냉장고 아이템 list
        context: 사용자 맥락
    
    Returns:
        추천 레시피 ID list
    """
    assistant = OpenAIAssistant(openai_key, "gpt-4o")
    assistant.set_system_prompt(RECOMMEND_PROMPT)
    
    # 냉장고 아이템을 JSON으로 Convert
    fridge_json = json.dumps([item.model_dump() for item in fridge_items])
    
    # 메시지 Create
    message = f"1. 냉장고: {fridge_json}\n2. 맥락: {context}"
    
    # Structured Output 스키마 (Go와 동일)
    response_format = {
        "name": "recommended",
        "strict": True,
        "schema": {
            "type": "object",
            "required": ["recipe"],
            "properties": {
                "recipe": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "레시피 아이디"
                }
            },
            "additionalProperties": False
        }
    }
    
    # API 호출
    response_str = await assistant.handle_with_json(message, response_format)
    
    # 파싱
    response_json = json.loads(response_str)
    recipes = response_json.get("recipe", [])
    
    return recipes

