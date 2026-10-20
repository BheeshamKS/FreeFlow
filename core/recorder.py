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

        # Subprocess fallback handle (for parecord / arecord)
        self._subproc: Optional[subprocess.Popen] = None
        self._subproc_wav_path = "/tmp/freeflow_audio.wav"

        # Log backend status
        if sd is not None:
            logger.info("Audio engine: sounddevice (PortAudio) initialized.")
        else:
            logger.warning("PortAudio not found. Falling back to native Linux recording tools (parecord/arecord).")

    @property
    def is_recording(self) -> bool:
        return self._is_recording

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
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype="float32",
                    device=self.device,
                    callback=self._audio_callback
                )
                self._stream.start()
                self._is_recording = True
                logger.info(f"sounddevice recording started (rate={self.sample_rate}Hz, channels={self.channels})")

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
                wav_path = "/tmp/freeflow_audio.wav"
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
