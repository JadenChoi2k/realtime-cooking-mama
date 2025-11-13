"""
텍스트 유틸리티
Go의 utils/text_utils.go 완벽 복제
"""
import random
import string


def get_random_string(length: int) -> str:
    """
    랜덤 문자열 생성
    Go의 GetRandomString 함수와 동일한 동작
    
    Args:
        length: 생성할 문자열 길이
    
    Returns:
        랜덤 알파벳 문자열
    """
    letters = string.ascii_letters  # a-z, A-Z
    return ''.join(random.choice(letters) for _ in range(length))

