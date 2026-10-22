"""
FreeFlow Audio Recorder
Streams high-fidelity audio from the microphone into memory and outputs a 16-bit PCM WAV file.
Supports sounddevice/PortAudio primary engine with automatic native Linux fallback
using parecord (PulseAudio/PipeWire), arecord (ALSA), or ffmpeg.
Calculates real-time audio volume levels for animated HUD feedback.
"""

import logging
import math
import os
import shutil
import signal
import subprocess
import tempfile
import time
from typing import List, Optional

import numpy as np
from scipy.io import wavfile

from core.platform import get_audio_temp_path, is_linux, is_macos, is_windows

# Safely attempt sounddevice import (may fail with OSError if PortAudio is not installed)
try:
    import sounddevice as sd
except (ImportError, OSError) as e:
    sd = None

try:
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    class QObject:
        pass
    def pyqtSignal(*args):
        return None

logger = logging.getLogger("FreeFlow.Recorder")


def list_input_devices() -> List[dict]:
    """
    Query available audio input devices (microphones) via sounddevice.
    Returns list of device dictionaries with 'id', 'name', 'channels', and 'default'.
    """
    devices = []
    if sd is None:
        return devices

    try:
        dev_list = sd.query_devices()
        default_in = None
        try:
            default_in = sd.default.device[0]
        except Exception:
            pass

        for idx, dev in enumerate(dev_list):
            max_in = dev.get("max_input_channels", 0)
            if max_in > 0:
                name = dev.get("name", f"Microphone {idx}").strip()
                is_def = (idx == default_in)
                devices.append({
                    "id": idx,
                    "name": name,
                    "channels": max_in,
                    "hostapi": dev.get("hostapi", 0),
                    "default": is_def
                })
    except Exception as e:
        logger.warning(f"Failed to query audio input devices: {e}")

    return devices


def resolve_device_index(device_val) -> Optional[int]:
    """
    Safely resolve a device name string or index to a valid sounddevice input index.
    Returns None if default or device not found.
    """
    if sd is None or device_val is None:
        return None
    val_str = str(device_val).strip()
    if not val_str or val_str.lower() in ("default", "none"):
        return None

    try:
        # Check if integer index
        idx = int(val_str)
        dev = sd.query_devices(idx)
        if dev and dev.get("max_input_channels", 0) > 0:
            return idx
    except Exception:
        pass

    # Search by exact name
    try:
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0:
                if dev.get("name", "").strip() == val_str:
                    return idx
        # Fallback to substring matching
        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0:
                if val_str.lower() in dev.get("name", "").strip().lower():
                    return idx
    except Exception as e:
        logger.debug(f"Device resolution lookup error: {e}")

    return None


class AudioRecorder(QObject):
    """
    Microphone recorder with dual engine support:
    - Primary: sounddevice (in-memory streaming with live RMS visualizer)
    - Fallback: native Linux parecord / arecord / ffmpeg (zero external native dependencies)
    """

    # PyQt signals for UI feedback
    recording_started = pyqtSignal() if QObject is not None else None
    recording_stopped = pyqtSignal(str) if QObject is not None else None
    audio_level = pyqtSignal(float) if QObject is not None else None  # Normalized RMS level (0.0 to 1.0)
    error_occurred = pyqtSignal(str) if QObject is not None else None

    def __init__(self, sample_rate: int = 16000, channels: int = 1, device: Optional[str] = None):
        super().__init__()
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device

        self._stream = None
        self._chunks: List[np.ndarray] = []
        self._is_recording = False
        self._start_time = 0.0

        # Subprocess fallback handle (for native recording tools)
        self._subproc: Optional[subprocess.Popen] = None
        self._subproc_wav_path = get_audio_temp_path()

        # Log backend status
        if sd is not None:
            logger.info("Audio engine: sounddevice (PortAudio) initialized.")
        else:
            logger.warning("PortAudio not found. Falling back to native system recording tools.")

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def set_device(self, device: Optional[str]):
        """Update active input microphone device."""
        self.device = device
        resolved = resolve_device_index(device)
        logger.info(f"AudioRecorder device set to: '{device}' (resolved index: {resolved})")

    def start(self) -> bool:
        """Start recording from default or selected audio input device."""
        if self._is_recording:
            logger.warning("Recorder already running.")
            return True

        self._chunks = []
        self._start_time = time.time()

        # Engine 1: sounddevice (if PortAudio is installed)
        if sd is not None:
            try:
                target_dev = resolve_device_index(self.device)
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype="float32",
                    device=target_dev,
                    callback=self._audio_callback
                )
                self._stream.start()
                self._is_recording = True
                dev_name = self.device or "system default"
                logger.info(f"sounddevice recording started on '{dev_name}' (rate={self.sample_rate}Hz, channels={self.channels})")

                if self.recording_started:
                    self.recording_started.emit()
                return True
            except Exception as e:
                logger.warning(f"sounddevice start failed ({e}). Switching to native fallback engine...")
                self._stream = None

        # Engine 2: Native Linux Subprocess Fallback (parecord, arecord, ffmpeg)
        return self._start_native_fallback()

    def _start_native_fallback(self) -> bool:
        """Start audio recording via system tools (parecord, arecord, ffmpeg)."""
        cmd = None
        engine_name = "unknown"

        if is_windows():
            if shutil.which("ffmpeg"):
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f", "dshow",
                    "-i", "audio=virtual-audio-capturer" if os.environ.get("FFMPEG_AUDIO_DEV") else "audio=default",
                    "-ar", str(self.sample_rate),
                    "-ac", str(self.channels),
                    self._subproc_wav_path
                ]
                engine_name = "ffmpeg (DirectShow)"
        elif is_macos():
            if shutil.which("ffmpeg"):
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f", "avfoundation",
                    "-i", ":default",
                    "-ar", str(self.sample_rate),
                    "-ac", str(self.channels),
                    self._subproc_wav_path
                ]
                engine_name = "ffmpeg (AVFoundation)"
        else:
            # Linux / Unix fallback chain
            if shutil.which("parecord"):
                # PulseAudio / PipeWire native recorder
                cmd = [
                    "parecord",
                    f"--rate={self.sample_rate}",
                    f"--channels={self.channels}",
                    "--file-format=wav",
                    self._subproc_wav_path
                ]
                engine_name = "parecord (PulseAudio/PipeWire)"
            elif shutil.which("arecord"):
                # ALSA native recorder
                cmd = [
                    "arecord",
                    "-q",
                    "-f", "S16_LE",
                    "-r", str(self.sample_rate),
                    "-c", str(self.channels),
                    "-t", "wav",
                    self._subproc_wav_path
                ]
                engine_name = "arecord (ALSA)"
            elif shutil.which("ffmpeg"):
                # FFmpeg pulse capture
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f", "pulse",
                    "-i", "default",
                    "-ar", str(self.sample_rate),
                    "-ac", str(self.channels),
                    self._subproc_wav_path
                ]
                engine_name = "ffmpeg (pulse)"

        if not cmd:
            if is_windows():
                err = "No audio recording backend found. Please install portaudio or ffmpeg."
            elif is_macos():
                err = "No audio recording backend found. Run: brew install portaudio ffmpeg"
            else:
                err = (
                    "No audio recording tool found. Please install libportaudio2:\n"
                    "  sudo apt install -y libportaudio2 portaudio19-dev"
                )
            logger.error(err)
            if self.error_occurred:
                self.error_occurred.emit(err)
            return False

        try:
            # Remove previous file if exists
            if os.path.exists(self._subproc_wav_path):
                os.remove(self._subproc_wav_path)

            self._subproc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self._is_recording = True
            logger.info(f"Native audio fallback recording started using {engine_name}.")

            if self.recording_started:
                self.recording_started.emit()

            # Emit dummy subtle audio level pulses for HUD animation
            if self.audio_level:
                self.audio_level.emit(0.3)

            return True
        except Exception as e:
            err_msg = f"Failed to start fallback recorder: {e}"
            logger.error(err_msg)
            if self.error_occurred:
                self.error_occurred.emit(err_msg)
            return False

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Streaming callback executed in sounddevice audio thread."""
        if status:
            logger.debug(f"Audio stream status notice: {status}")

        if not self._is_recording:
            return

        self._chunks.append(indata.copy())

        # Calculate RMS amplitude for real-time visualizer
        if self.audio_level and len(indata) > 0:
            rms = float(np.sqrt(np.mean(indata ** 2)))
            level = min(1.0, max(0.0, rms * 4.0))
            try:
                self.audio_level.emit(level)
            except Exception:
                pass

    def stop(self) -> Optional[str]:
        """
        Stop recording and return WAV file path.
        """
        if not self._is_recording:
            logger.warning("Recorder is not active.")
            return None

        self._is_recording = False
        duration = time.time() - self._start_time

        # 1. Handle sounddevice stream if active
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.debug(f"Stream close notice: {e}")
            finally:
                self._stream = None

            if not self._chunks:
                logger.warning("No audio frames recorded.")
                return None

            if duration < 0.3:
                logger.info(f"Discarding recording: too short ({duration:.2f}s).")
                return None

            try:
                audio_data = np.concatenate(self._chunks, axis=0)
                audio_int16 = (audio_data * 32767.0).clip(-32768, 32767).astype(np.int16)
                wav_path = get_audio_temp_path()
                wavfile.write(wav_path, self.sample_rate, audio_int16)
                logger.info(f"Recorded {duration:.2f}s audio saved to {wav_path}")

                if self.recording_stopped:
                    self.recording_stopped.emit(wav_path)
                return wav_path
            except Exception as e:
                err_msg = f"Failed to save recorded audio: {e}"
                logger.error(err_msg)
                if self.error_occurred:
                    self.error_occurred.emit(err_msg)
                return None

        # 2. Handle native subprocess recorder if active
        if self._subproc:
            try:
                # Send SIGINT to arecord/parecord to finalize WAV headers
                self._subproc.send_signal(signal.SIGINT)
                try:
                    self._subproc.wait(timeout=1.5)
                except subprocess.TimeoutExpired:
                    self._subproc.kill()
            except Exception as e:
                logger.debug(f"Subprocess termination notice: {e}")
            finally:
                self._subproc = None

            if duration < 0.3:
                logger.info(f"Discarding recording: too short ({duration:.2f}s).")
                return None

            if os.path.isfile(self._subproc_wav_path) and os.path.getsize(self._subproc_wav_path) > 100:
                logger.info(f"Fallback audio saved to {self._subproc_wav_path} ({duration:.2f}s)")
                if self.recording_stopped:
                    self.recording_stopped.emit(self._subproc_wav_path)
                return self._subproc_wav_path
            else:
                logger.warning("Fallback audio file was not written or is empty.")
                return None

        return None
