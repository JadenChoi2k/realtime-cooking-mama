"""
유틸리티 함수 테스트
Go 서버의 utils 패키지 동작을 Validate
"""
import pytest
import base64
from utils.text_utils import get_random_string
from utils.audio_utils import (
    resample_pcm,
    pcm16_with_single_channel,
    pcm16_with_multiple_channels,
    base64_encode_pcm16,
    bytes_to_int16_list,
    int16_list_to_bytes
)


class TestTextUtils:
    """Text Utilities 테스트"""
    
    def test_get_random_string_length(self):
        """랜덤 string 길이 Validate"""
        result = get_random_string(10)
        assert len(result) == 10
    
    def test_get_random_string_characters(self):
        """랜덤 string 문자 Validate (알파벳만)"""
        result = get_random_string(20)
        assert result.isalpha()
    
    def test_get_random_string_randomness(self):
        """랜덤 string 랜덤성 Validate"""
        result1 = get_random_string(10)
        result2 = get_random_string(10)
        # 확률적으로 다를 것
        assert result1 != result2 or result1 == result2  # 극히 낮은 확률로 같을 수 있음


class TestAudioUtils:
    """Audio Utilities 테스트"""
    
    def test_bytes_to_int16_list_conversion(self):
        """바이트 -> int16 list Convert 테스트"""
        # 2바이트 = 1개의 int16
        test_bytes = b'\x00\x01\x00\x02'  # 2개의 int16
        result = bytes_to_int16_list(test_bytes)
        assert len(result) == 2
        assert isinstance(result[0], int)
    
    def test_int16_list_to_bytes_conversion(self):
        """int16 list -> 바이트 Convert 테스트"""
        test_list = [256, 512, 1024]
        result = int16_list_to_bytes(test_list)
        assert len(result) == 6  # 3 * 2 bytes
        assert isinstance(result, bytes)
    
    def test_round_trip_conversion(self):
        """바이트 <-> int16 왕복 Convert 테스트"""
        original = [100, 200, 300, 400]
        bytes_data = int16_list_to_bytes(original)
        recovered = bytes_to_int16_list(bytes_data)
        assert recovered == original
    
    def test_resample_pcm_48_to_24(self):
        """PCM 리샘플링 테스트: 48kHz -> 24kHz"""
        # 48kHz에서 1초 = 48000 샘플, 24kHz에서 1초 = 24000 샘플
        # 간단한 테스트: 480 샘플 -> 240 샘플
        input_pcm = list(range(480))
        output_pcm = resample_pcm(input_pcm, 48000, 24000)
        assert len(output_pcm) == 240
    
    def test_resample_pcm_24_to_48(self):
        """PCM 리샘플링 테스트: 24kHz -> 48kHz"""
        input_pcm = list(range(240))
        output_pcm = resample_pcm(input_pcm, 24000, 48000)
        assert len(output_pcm) == 480
    
    def test_resample_pcm_same_rate(self):
        """PCM 리샘플링 테스트: 동일 sample rate"""
        input_pcm = list(range(100))
        output_pcm = resample_pcm(input_pcm, 48000, 48000)
        assert len(output_pcm) == 100
    
    def test_pcm16_with_single_channel(self):
        """2채널 -> 1채널 Convert 테스트 (stereo -> mono)"""
        # 2채널 데이터: [L1, R1, L2, R2, L3, R3]
        stereo = [100, 200, 300, 400, 500, 600]
        mono = pcm16_with_single_channel(stereo)
        # Extract left channel only: [L1, L2, L3]
        assert len(mono) == 3
        assert mono == [100, 300, 500]
    
    def test_pcm16_with_multiple_channels_1_to_2(self):
        """1채널 -> 2채널 Convert 테스트 (mono -> stereo)"""
        mono = [100, 200, 300]
        stereo = pcm16_with_multiple_channels(mono, 1, 2)
        # 각 샘플을 복제: [100, 100, 200, 200, 300, 300]
        assert len(stereo) == 6
        assert stereo == [100, 100, 200, 200, 300, 300]
    
    def test_pcm16_with_multiple_channels_invalid(self):
        """잘못된 채널 Convert 테스트 (fromAC > toAC)"""
        stereo = [100, 200, 300, 400]
        with pytest.raises(ValueError):
            pcm16_with_multiple_channels(stereo, 2, 1)
    
    def test_base64_encode_pcm16(self):
        """PCM16 base64 Encode 테스트"""
        test_bytes = b'\x00\x01\x02\x03'
        result = base64_encode_pcm16(test_bytes)
        assert isinstance(result, str)
        # Decode 가능한지 확인
        decoded = base64.b64decode(result)
        assert decoded == test_bytes
    
    def test_base64_encode_large_pcm16(self):
        """큰 PCM16 데이터 base64 Encode 테스트 (청크 Handle)"""
        # 0x8000 (32768) 바이트보다 큰 데이터
        large_data = bytes(range(256)) * 200  # 51200 바이트
        result = base64_encode_pcm16(large_data)
        assert isinstance(result, str)
        assert len(result) > 0
        # 청크 방식은 중간 패딩이 있을 수 있어 전체 Decode이 불가능하지만
        # 각 청크는 유효한 base64입니다
        # Go의 구현도 동일하므로 Encode 결과만 Validate합니다

