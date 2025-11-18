import os
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, Optional, Tuple
import wave


class AudioLogger:
    """Utility to persist raw audio chunks, metadata, and playable WAV files."""

    def __init__(self, base_path: str = "logs/audio", enabled: Optional[bool] = None):
        if enabled is None:
            enabled = os.getenv("AUDIO_LOGGING", "true").lower() in ("1", "true", "yes", "on")
        self.enabled = enabled
        self.base_dir = Path(base_path)
        if self.enabled:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        self._wav_handles: Dict[Tuple[str, str], wave.Wave_write] = {}
        self._wav_lock = Lock()

    def session_dir(self, session_id: str) -> Path:
        if not self.enabled:
            return self.base_dir / session_id
        session_path = self.base_dir / session_id
        session_path.mkdir(parents=True, exist_ok=True)
        return session_path

    def _write_text(self, session_id: str, filename: str, content: str):
        if not self.enabled:
            return
        path = self.session_dir(session_id) / filename
        with path.open("a", encoding="utf-8") as file:
            file.write(content + "\n")

    def _write_bytes(self, session_id: str, filename: str, data: bytes):
        if not self.enabled:
            return
        path = self.session_dir(session_id) / filename
        with path.open("ab") as file:
            file.write(data)

    def _touch_raw_file(self, session_id: str, direction: str):
        if not self.enabled:
            return
        path = self.session_dir(session_id) / f"{direction}_chunks.raw"
        if not path.exists():
            path.touch()

    def ensure_wav(
        self,
        session_id: str,
        direction: str,
        sample_rate: Optional[int],
        channels: Optional[int],
    ):
        if not self.enabled:
            return
        if sample_rate is None or channels is None:
            return
        key = (session_id, direction)
        with self._wav_lock:
            if key in self._wav_handles:
                return
            wav_path = self.session_dir(session_id) / f"{direction}.wav"
            handle = wave.open(str(wav_path), "wb")
            handle.setnchannels(channels)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            self._wav_handles[key] = handle

    def log_chunk(
        self,
        session_id: str,
        direction: str,
        chunk_id: str,
        chunk_data: bytes,
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
        note: Optional[str] = None,
    ):
        if not self.enabled:
            return
        timestamp = datetime.utcnow().isoformat()
        metadata = (
            f"{timestamp} dir={direction} chunk={chunk_id} size={len(chunk_data)} "
            f"sample_rate={sample_rate} channels={channels} "
            f"first10={chunk_data[:10].hex()} note={note or ''}"
        )
        self._write_text(session_id, f"{direction}_log.txt", metadata)
        self._write_bytes(session_id, f"{direction}_chunks.raw", chunk_data)
        self._append_wav(session_id, direction, chunk_data, sample_rate, channels)

    def log_note(
        self,
        session_id: str,
        direction: str,
        note: str,
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
    ):
        if not self.enabled:
            return
        """
        Write a textual note for a direction. Ensures raw/WAV files exist even without audio.
        """
        timestamp = datetime.utcnow().isoformat()
        note_line = f"{timestamp} dir={direction} note={note}"
        self._write_text(session_id, f"{direction}_log.txt", note_line)
        self._touch_raw_file(session_id, direction)
        if sample_rate is not None and channels is not None:
            self.ensure_wav(session_id, direction, sample_rate, channels)

    def _append_wav(
        self,
        session_id: str,
        direction: str,
        chunk_data: bytes,
        sample_rate: Optional[int],
        channels: Optional[int],
    ):
        if not self.enabled:
            return
        if not chunk_data or sample_rate is None or channels is None:
            return

        key = (session_id, direction)
        with self._wav_lock:
            handle = self._wav_handles.get(key)
            if handle is None:
                wav_path = self.session_dir(session_id) / f"{direction}.wav"
                handle = wave.open(str(wav_path), "wb")
                handle.setnchannels(channels)
                handle.setsampwidth(2)  # PCM16
                handle.setframerate(sample_rate)
                self._wav_handles[key] = handle
            handle.writeframes(chunk_data)

    def log_outbound_chunk(
        self,
        session_id: str,
        chunk_id: str,
        chunk_data: bytes,
        sample_rate: int,
        channels: int,
        note: Optional[str] = None,
    ):
        self.log_chunk(session_id, "outbound", chunk_id, chunk_data, sample_rate, channels, note)

    def log_outbound_frame(
        self,
        session_id: str,
        chunk_id: str,
        chunk_data: bytes,
        sample_rate: int,
        channels: int,
        note: Optional[str] = None,
    ):
        self.log_chunk(
            session_id,
            "outbound_frame",
            chunk_id,
            chunk_data,
            sample_rate,
            channels,
            note,
        )

    def log_inbound_chunk(
        self,
        session_id: str,
        chunk_id: str,
        chunk_data: bytes,
        sample_rate: int,
        channels: int,
        note: Optional[str] = None,
    ):
        self.log_chunk(session_id, "inbound", chunk_id, chunk_data, sample_rate, channels, note)

    @property
    def is_enabled(self) -> bool:
        return self.enabled

    def close_session(self, session_id: str):
        """Close WAV files for a session so headers are finalized."""
        if not self.enabled:
            return
        with self._wav_lock:
            keys = [key for key in self._wav_handles if key[0] == session_id]
            for key in keys:
                handle = self._wav_handles.pop(key)
                handle.close()

