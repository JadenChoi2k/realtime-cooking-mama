"""
Text Utilities
Complete port of Go's utils/text_utils.go
"""
import random
import string


def get_random_string(length: int) -> str:
    """
    Generate random string
    Same behavior as Go's GetRandomString function
    
    Args:
        length: Length of string to generate
    
    Returns:
        Random alphabetic string
    """
    letters = string.ascii_letters  # a-z, A-Z
    return ''.join(random.choice(letters) for _ in range(length))
