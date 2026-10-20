"""
FreeFlow Dictation History & Metrics Manager
Persists dictation history locally so users can review, search, and copy past transcriptions.
"""

import datetime
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

try:
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    class QObject:
        pass
    def pyqtSignal(*args):
        return None

from core.platform import get_history_file

logger = logging.getLogger("FreeFlow.History")
HISTORY_FILE = get_history_file()


@dataclass
class HistoryEntry:
    id: str
    timestamp: float
    time_str: str
    text: str
    word_count: int
    duration_sec: float


class HistoryManager(QObject):
    """Manages local transcription history storage."""

    history_updated = pyqtSignal() if QObject is not None else None

    def __init__(self, max_entries: int = 200, parent=None):
        super().__init__(parent)
        self.max_entries = max_entries
        self.entries: List[HistoryEntry] = []
        self._load()

    def _load(self):
        """Load history entries from JSON file."""
        if not HISTORY_FILE.is_file():
            self.entries = []
            return

        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.entries = [
                    HistoryEntry(
                        id=item.get("id", str(item.get("timestamp", time.time()))),
                        timestamp=item.get("timestamp", time.time()),
                        time_str=item.get("time_str", ""),
                        text=item.get("text", ""),
                        word_count=item.get("word_count", 0),
                        duration_sec=item.get("duration_sec", 0.0)
                    )
                    for item in data
                ]
            logger.info(f"Loaded {len(self.entries)} history entries.")
        except Exception as e:
            logger.warning(f"Could not load dictation history: {e}")
            self.entries = []

    def _save(self):
        """Save history entries to JSON file."""
        try:
            HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([asdict(e) for e in self.entries[:self.max_entries]], f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save dictation history: {e}")

    def add_entry(self, text: str, duration_sec: float = 0.0) -> HistoryEntry:
        """Add new transcription entry."""
        stripped = text.strip()
        if not stripped:
            return None

        words = len(stripped.split())
        now = time.time()
        time_str = time.strftime("%b %d, %I:%M %p", time.localtime(now))

        entry = HistoryEntry(
            id=f"{int(now * 1000)}",
            timestamp=now,
            time_str=time_str,
            text=stripped,
            word_count=words,
            duration_sec=round(duration_sec, 2)
        )

        self.entries.insert(0, entry)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[:self.max_entries]

        self._save()
        if self.history_updated:
            self.history_updated.emit()
        return entry

    def clear(self):
        """Clear all history entries."""
        self.entries = []
        self._save()
        if self.history_updated:
            self.history_updated.emit()

    def get_total_words(self) -> int:
        return sum(e.word_count for e in self.entries)

    def get_total_count(self) -> int:
        return len(self.entries)

    def get_today_count(self) -> int:
        now = datetime.datetime.now()
        local_midnight = datetime.datetime(now.year, now.month, now.day).timestamp()
        return sum(1 for e in self.entries if e.timestamp >= local_midnight)

    def get_today_words(self) -> int:
        now = datetime.datetime.now()
        local_midnight = datetime.datetime(now.year, now.month, now.day).timestamp()
        return sum(e.word_count for e in self.entries if e.timestamp >= local_midnight)
