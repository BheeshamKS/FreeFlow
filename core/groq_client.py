"""
FreeFlow Groq API Integration
Handles ultra-fast Whisper speech-to-text audio transcription
and optional Llama 3 LLM post-processing for grammar and filler-word removal.
"""

import logging
import os
from typing import Optional, Tuple

try:
    from groq import Groq, AuthenticationError, APIError
except ImportError:
    Groq = None
    AuthenticationError = Exception
    APIError = Exception

try:
    from PyQt6.QtCore import QThread, pyqtSignal
except ImportError:
    class QThread:
        pass
    def pyqtSignal(*args):
        return None

from core.config import AppConfig

logger = logging.getLogger("FreeFlow.Groq")


class GroqService:
    """Encapsulates Groq API calls for audio transcription and text formatting."""

    def __init__(self, api_key: str):
        self.api_key = api_key.strip()
        self._client: Optional[Groq] = None
        if self.api_key and Groq is not None:
            self._client = Groq(api_key=self.api_key)

    def set_api_key(self, api_key: str):
        self.api_key = api_key.strip()
        if self.api_key and Groq is not None:
            self._client = Groq(api_key=self.api_key)
        else:
            self._client = None

    def test_connection(self) -> Tuple[bool, str]:
        """Verify API key validity against Groq's servers."""
        if not self.api_key:
            return False, "API key is empty. Please enter your Groq API key."

        if Groq is None:
            return False, "The 'groq' Python library is not installed."

        try:
            client = Groq(api_key=self.api_key)
            models = client.models.list()
            return True, f"Connection successful! {len(models.data)} models available."
        except AuthenticationError:
            return False, "Authentication failed: Invalid Groq API key."
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def transcribe(self, audio_file_path: str, model: str = "whisper-large-v3") -> str:
        """Transcribe an audio file using Groq Whisper."""
        if not self._client:
            raise ValueError("Groq client not initialized. Please configure your GROQ_API_KEY.")

        if not os.path.isfile(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        file_size = os.path.getsize(audio_file_path)
        if file_size < 100:
            raise ValueError("Recorded audio file is empty.")

        logger.info(f"Transcribing audio ({file_size} bytes) via Groq model '{model}'...")

        with open(audio_file_path, "rb") as f:
            file_bytes = f.read()

        filename = os.path.basename(audio_file_path)
        response = self._client.audio.transcriptions.create(
            file=(filename, file_bytes),
            model=model,
            response_format="text"
        )

        raw_text = str(response).strip()
        logger.info(f"Raw transcription received ({len(raw_text)} chars): '{raw_text}'")
        return raw_text

    def format_text(
        self,
        raw_text: str,
        model: str = "openai/gpt-oss-20b",
        system_prompt: Optional[str] = None
    ) -> str:
        """Pass transcription through Groq LLM to remove filler words and format punctuation."""
        if not self._client:
            raise ValueError("Groq client not initialized.")

        if not raw_text.strip():
            return ""

        if not system_prompt:
            system_prompt = (
                "You are an expert transcription editor. Clean up the provided raw speech-to-text transcription. "
                "Fix punctuation, capitalization, and minor grammatical slips. "
                "Remove stuttering and verbal filler words (such as 'um', 'uh', 'you know', 'like', 'ah'). "
                "Do NOT change the underlying meaning, tone, or technical jargon. "
                "Return ONLY the finalized, ready-to-paste text without any preamble, quotes, markdown formatting or commentary."
            )

        candidate_models = [model]
        # Common active chat models as fallbacks
        for fallback in ["openai/gpt-oss-20b", "qwen/qwen3.8-27b", "llama-3.1-8b-instant", "llama3-8b-8192"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        last_exception = None
        for current_model in candidate_models:
            try:
                logger.info(f"Formatting text via Groq LLM model '{current_model}'...")
                completion = self._client.chat.completions.create(
                    model=current_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": raw_text}
                    ],
                    temperature=0.1,
                    max_tokens=1500
                )
                formatted_text = completion.choices[0].message.content.strip()
                logger.info(f"Formatted text ready via '{current_model}' ({len(formatted_text)} chars): '{formatted_text}'")
                return formatted_text
            except Exception as e:
                logger.warning(f"Groq LLM model '{current_model}' failed: {e}. Trying fallback if available...")
                last_exception = e

        if last_exception:
            raise last_exception
        return raw_text


class GroqWorker(QThread):
    """Asynchronous background worker to transcribe and format without freezing UI."""

    status_changed = pyqtSignal(str) if QThread is not None else None  # 'transcribing', 'formatting', 'done', 'error'
    completed = pyqtSignal(str) if QThread is not None else None       # Final text payload
    error = pyqtSignal(str) if QThread is not None else None

    def __init__(self, config: AppConfig, audio_path: str):
        super().__init__()
        self.config = config
        self.audio_path = audio_path
        self.service = GroqService(config.groq_api_key)

    def run(self):
        try:
            if self.status_changed:
                self.status_changed.emit("transcribing")

            raw_text = self.service.transcribe(
                self.audio_path,
                model=self.config.transcription_model
            )

            final_text = raw_text
            if self.config.format_text and raw_text.strip():
                if self.status_changed:
                    self.status_changed.emit("formatting")
                try:
                    final_text = self.service.format_text(
                        raw_text,
                        model=self.config.format_model,
                        system_prompt=self.config.system_prompt
                    )
                except Exception as format_err:
                    logger.warning(
                        f"LLM formatting model '{self.config.format_model}' failed ({format_err}). "
                        f"Gracefully falling back to raw transcription."
                    )
                    # Gracefully fall back to raw transcription so user text is NEVER lost!
                    final_text = raw_text

            if self.status_changed:
                self.status_changed.emit("done")

            if self.completed:
                self.completed.emit(final_text)

        except Exception as e:
            err_msg = str(e)
            logger.error(f"Groq processing failed: {err_msg}")
            if self.status_changed:
                self.status_changed.emit("error")
            if self.error:
                self.error.emit(err_msg)
