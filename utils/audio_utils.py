"""
오디오 유틸리티
Go의 utils/audio_utils.go 완벽 복제
"""
import base64
from typing import List
import opuslib


def bytes_to_int16_list(b: bytes) -> List[int]:
    """
    바이트 배열을 int16 리스트로 변환
    Go의 BytesToInt16Slice 함수와 동일
    
    Args:
        b: 바이트 배열
    
    Returns:
        int16 리스트
    """
    pcm = []
    for i in range(0, len(b), 2):
        if i + 1 < len(b):
            # Little-endian: 하위 바이트 | (상위 바이트 << 8)
            value = b[i] | (b[i + 1] << 8)
            # signed int16으로 변환
            if value >= 32768:
                value -= 65536
            pcm.append(value)
    return pcm


def int16_list_to_bytes(pcm: List[int]) -> bytes:
    """
    int16 리스트를 바이트 배열로 변환
    Go의 Int16ToBytes 함수와 동일
    
    Args:
        pcm: int16 리스트
    
    Returns:
        바이트 배열
    """
    b = bytearray(len(pcm) * 2)
    for i, value in enumerate(pcm):
        # signed int16을 unsigned로 변환
        if value < 0:
            value += 65536
        # Little-endian
        b[i * 2] = value & 0xFF
        b[i * 2 + 1] = (value >> 8) & 0xFF
    return bytes(b)


def resample_pcm(pcm: List[int], from_sample_rate: int, to_sample_rate: int) -> List[int]:
    """
    PCM 데이터 리샘플링 (선형 보간)
    Go의 ResamplePCM 함수와 동일한 알고리즘
    
    Args:
        pcm: 입력 PCM 데이터
        from_sample_rate: 원본 샘플레이트
        to_sample_rate: 목표 샘플레이트
    
    Returns:
        리샘플링된 PCM 데이터
    """
    if from_sample_rate == to_sample_rate:
        return pcm[:]
    
    ratio = to_sample_rate / from_sample_rate
    out_length = int(len(pcm) * ratio)
    resampled = []
    
    for i in range(out_length):
        src_index = i / ratio
        src_pos = int(src_index)
        
        if src_pos + 1 < len(pcm):
            # 선형 보간
            frac = src_index - src_pos
            value = pcm[src_pos] * (1 - frac) + pcm[src_pos + 1] * frac
            resampled.append(int(value))
        elif src_pos < len(pcm):
            # 마지막 인덱스
            resampled.append(pcm[src_pos])
        else:
            # 범위 초과
            break
    
    return resampled


def pcm16_with_single_channel(pcm: List[int]) -> List[int]:
    """
    2채널 PCM을 1채널로 변환 (왼쪽 채널만 추출)
    Go의 PCM16WithSingleAC 함수와 동일
    
    Args:
        pcm: 2채널 PCM 데이터 [L1, R1, L2, R2, ...]
    
    Returns:
        1채널 PCM 데이터 [L1, L2, ...]
    """
    shrinked = []
    for i in range(0, len(pcm), 2):
        shrinked.append(pcm[i])
    return shrinked


def pcm16_with_multiple_channels(pcm: List[int], from_ac: int, to_ac: int) -> List[int]:
    """
    채널 수 증가 (각 샘플 복제)
    Go의 PCM16WithMultipleAC 함수와 동일
    
    Args:
        pcm: 입력 PCM 데이터
        from_ac: 원본 채널 수
        to_ac: 목표 채널 수
    
    Returns:
        증가된 채널의 PCM 데이터
    
    Raises:
        ValueError: from_ac > to_ac인 경우
    """
    if from_ac > to_ac:
        raise ValueError("from_ac must be less than or equal to to_ac")
    
    if from_ac == to_ac:
        return pcm[:]
    
    m_factor = to_ac // from_ac
    multiplied = []
    for value in pcm:
        for _ in range(m_factor):
            multiplied.append(value)
    return multiplied


def base64_encode_pcm16(pcm: bytes) -> str:
    """
    PCM16 데이터를 base64로 인코딩
    Go의 Base64EncodePCM16 함수와 동일 (청크 단위 처리)
    
    Args:
        pcm: PCM 바이트 데이터
    
    Returns:
        base64 인코딩된 문자열
    """
    chunk_size = 0x8000  # 32768 바이트
    result = ""
    
    for i in range(0, len(pcm), chunk_size):
        end = min(i + chunk_size, len(pcm))
        chunk = pcm[i:end]
        result += base64.b64encode(chunk).decode('ascii')
    
    return result


class OpusHandler:
    """
    Opus 코덱 핸들러
    Go의 OpusHandler 구조체와 동일
    """
    
    def __init__(self, sample_rate: int, channels: int):
        """
        Args:
            sample_rate: 샘플레이트 (예: 48000)
            channels: 채널 수 (1: 모노, 2: 스테레오)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.decoder = opuslib.Decoder(sample_rate, channels)
        self.encoder = opuslib.Encoder(sample_rate, channels, opuslib.APPLICATION_AUDIO)
    
    def decode(self, opus_data: bytes) -> bytes:
        """
        Opus 데이터를 PCM16으로 디코딩
        
        Args:
            opus_data: Opus 인코딩된 데이터
        
        Returns:
            PCM16 바이트 데이터
        """
        # 20ms 프레임 크기 계산
        frame_size = (self.sample_rate // 1000) * 20
        pcm_data = self.decoder.decode(opus_data, frame_size)
        return bytes(pcm_data)
    
    def encode(self, pcm_data: bytes) -> bytes:
        """
        PCM16 데이터를 Opus로 인코딩
        
        Args:
            pcm_data: PCM16 바이트 데이터
        
        Returns:
            Opus 인코딩된 데이터
        """
        # 20ms 프레임 크기 계산
        frame_size = (self.sample_rate // 1000) * 20
        opus_data = self.encoder.encode(pcm_data, frame_size)
        return bytes(opus_data)

