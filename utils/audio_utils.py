"""
Audio Utilities
Complete port of Go's utils/audio_utils.go
"""
import base64
from typing import List
import opuslib


def bytes_to_int16_list(b: bytes) -> List[int]:
    """
    Convert byte array to int16 list
    Same as Go's BytesToInt16Slice function
    
    Args:
        b: byte array
    
    Returns:
        int16 list
    """
    pcm = []
    for i in range(0, len(b), 2):
        if i + 1 < len(b):
            # Little-endian: lower byte | (upper byte << 8)
            value = b[i] | (b[i + 1] << 8)
            # Convert to signed int16
            if value >= 32768:
                value -= 65536
            pcm.append(value)
    return pcm


def int16_list_to_bytes(pcm: List[int]) -> bytes:
    """
    int16 list를 byte array로 Convert
    Same as Go's Int16ToBytes function
    
    Args:
        pcm: int16 list
    
    Returns:
        byte array
    """
    b = bytearray(len(pcm) * 2)
    for i, value in enumerate(pcm):
        # Convert signed int16 to unsigned
        if value < 0:
            value += 65536
        # Little-endian
        b[i * 2] = value & 0xFF
        b[i * 2 + 1] = (value >> 8) & 0xFF
    return bytes(b)


def resample_pcm(pcm: List[int], from_sample_rate: int, to_sample_rate: int) -> List[int]:
    """
    Resample PCM data (Linear interpolation)
    Same as Go's ResamplePCM function한 알고리즘
    
    Args:
        pcm: input PCM data
        from_sample_rate: 원본 sample rate
        to_sample_rate: 목표 sample rate
    
    Returns:
        resampled PCM data
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
            # Linear interpolation
            frac = src_index - src_pos
            value = pcm[src_pos] * (1 - frac) + pcm[src_pos + 1] * frac
            resampled.append(int(value))
        elif src_pos < len(pcm):
            # last index
            resampled.append(pcm[src_pos])
        else:
            # out of range
            break
    
    return resampled


def pcm16_with_single_channel(pcm: List[int]) -> List[int]:
    """
    2채널 PCM을 1채널로 Convert (Extract left channel only)
    Same as Go's PCM16WithSingleAC function
    
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
    Increase channel count (Replicate each sample)
    Same as Go's PCM16WithMultipleAC function
    
    Args:
        pcm: input PCM data
        from_ac: 원본 number of channels
        to_ac: 목표 number of channels
    
    Returns:
        PCM data with increased channels
    
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
    PCM16 데이터를 base64로 Encode
    Same as Go's Base64EncodePCM16 function (청크 단위 Handle)
    
    Args:
        pcm: PCM byte data
    
    Returns:
        base64 Encode된 string
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
    Opus codec handler
    Equivalent to Go's OpusHandler struct
    """
    
    def __init__(self, sample_rate: int, channels: int):
        """
        Args:
            sample_rate: sample rate (e.g.: 48000)
            channels: number of channels (1: mono, 2: stereo)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.decoder = opuslib.Decoder(sample_rate, channels)
        self.encoder = opuslib.Encoder(sample_rate, channels, opuslib.APPLICATION_AUDIO)
    
    def decode(self, opus_data: bytes) -> bytes:
        """
        Opus 데이터를 PCM16으로 Decode
        
        Args:
            opus_data: Opus Encode된 데이터
        
        Returns:
            PCM16 바이트 데이터
        """
        # 20ms Calculate frame size
        frame_size = (self.sample_rate // 1000) * 20
        pcm_data = self.decoder.decode(opus_data, frame_size)
        return bytes(pcm_data)
    
    def encode(self, pcm_data: bytes) -> bytes:
        """
        PCM16 데이터를 Opus로 Encode
        
        Args:
            pcm_data: PCM16 바이트 데이터
        
        Returns:
            Opus Encode된 데이터
        """
        # 20ms Calculate frame size
        frame_size = (self.sample_rate // 1000) * 20
        opus_data = self.encoder.encode(pcm_data, frame_size)
        return bytes(opus_data)

