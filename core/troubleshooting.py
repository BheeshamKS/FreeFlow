"""
FreeFlow Comprehensive Error Troubleshooting & Diagnostics
Categorizes runtime exceptions, provides step-by-step remediation guides,
browsable common troubleshooting topics, and constructs pre-filled GitHub issue templates.
"""

import logging
import os
import platform
import re
import sys
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from core.version import APP_VERSION

logger = logging.getLogger("FreeFlow.Troubleshooting")

GITHUB_REPO_URL = "https://github.com/BheeshamKS/FreeFlow"


@dataclass
class ErrorDiagnostic:
    """Structured diagnostic result with user-friendly solutions and metadata."""
    category: str
    title: str
    summary: str
    steps: List[str]
    primary_action_label: str
    primary_action_id: str
    secondary_action_label: Optional[str] = None
    secondary_action_id: Optional[str] = None
    raw_error: str = ""
    sanitized_error: str = ""
    github_issue_url: str = ""
    extra_tips: List[str] = field(default_factory=list)
    is_error: bool = True


COMMON_TOPICS: Dict[str, Dict] = {
    "api_key": {
        "title": "Groq API Key Setup & Verification",
        "category": "INVALID_API_KEY",
        "icon": "🔑",
        "summary": "How to create a free Groq API key and configure it properly in FreeFlow.",
        "steps": [
            "Visit console.groq.com/keys to generate a free personal API key.",
            "Copy your key (starts with 'gsk_') and paste it into FreeFlow Preferences.",
            "Click 'Test Connection' in Preferences to ensure the key is active and recognized.",
            "Ensure there are no leading, trailing, or hidden whitespace characters in the key field."
        ],
        "primary_label": "Open Preferences",
        "primary_id": "open_settings",
        "secondary_label": "Get Free Groq Key",
        "secondary_id": "open_groq_console",
        "extra_tips": [
            "Groq API keys are completely free for personal speech transcription.",
            "Never share your API key publicly or commit it into code repositories."
        ]
    },
    "connection": {
        "title": "Network Connection & Windows Firewall",
        "category": "NETWORK_FIREWALL",
        "icon": "🌐",
        "summary": "Resolving connection drops, proxy issues, and Windows Defender / Firewall blocks.",
        "steps": [
            "Verify your computer has an active internet connection.",
            "Windows Defender / Firewall: Ensure Python and FreeFlow are allowed outbound HTTPS access.",
            "Antivirus / VPN: If using a VPN or third-party antivirus, temporarily whitelist api.groq.com:443.",
            "DNS Resolution: Ensure your network can resolve api.groq.com.",
            "Click 'Test Connection' below to confirm connection to Groq's servers."
        ],
        "primary_label": "Test Groq Connection",
        "primary_id": "test_connection",
        "secondary_label": "Open Preferences",
        "secondary_id": "open_settings",
        "extra_tips": [
            "On corporate/school networks, AI API domains might require proxy configuration."
        ]
    },
    "microphone": {
        "title": "Microphone Selection & Audio Silence",
        "category": "AUDIO_EMPTY",
        "icon": "🎙️",
        "summary": "Resolving empty audio captures, hardware mute issues, and input device selection.",
        "steps": [
            "Open FreeFlow Preferences -> Audio Device -> select your specific hardware microphone.",
            "Click 'Refresh Devices' if your USB microphone or headset was recently plugged in.",
            "Check that your physical microphone mute switch is turned OFF.",
            "On Windows / macOS / Linux, ensure Microphone Permissions are granted to FreeFlow."
        ],
        "primary_label": "Select Microphone",
        "primary_id": "open_audio_settings",
        "secondary_label": "Open Preferences",
        "secondary_id": "open_settings",
        "extra_tips": [
            "Whisper speech recognition requires clear audible sound; whisper-level speech might be filtered by noise suppression."
        ]
    },
    "injection": {
        "title": "Text Injection & Smart Clipboard Fallback",
        "category": "INJECTION_INFO",
        "icon": "📋",
        "summary": "How FreeFlow automatically detects active text boxes vs desktop clipboard fallback.",
        "steps": [
            "When an active text box is focused: FreeFlow injects text directly and restores your previous clipboard.",
            "When NO text box is focused (desktop wallpaper, panel, or unfocused window): FreeFlow copies the text directly to your clipboard.",
            "When copied to clipboard, paste it anywhere with Ctrl+V (Cmd+V on macOS).",
            "Adjust injection delay in Preferences if your PC needs more time to register keystrokes."
        ],
        "primary_label": "Open Preferences",
        "primary_id": "open_settings",
        "secondary_label": "Test Injection",
        "secondary_id": "test_connection",
        "extra_tips": [
            "FreeFlow never leaves your transcribed text on the clipboard when a text box is active."
        ]
    },
    "rate_limit": {
        "title": "Rate Limits & Whisper Models",
        "category": "RATE_LIMIT",
        "icon": "⏱️",
        "summary": "Understanding Groq free-tier quotas and selecting speech recognition models.",
        "steps": [
            "Groq's free tier has generous per-minute (RPM) and daily audio limits.",
            "If you receive rate limit 429, wait 30–60 seconds for the window to reset.",
            "In Preferences, you can switch between 'whisper-large-v3' and 'whisper-large-v3-turbo'.",
            "You can monitor your live usage anytime at console.groq.com."
        ],
        "primary_label": "Open Groq Console",
        "primary_id": "open_groq_console",
        "secondary_label": "Open Preferences",
        "secondary_id": "open_settings",
        "extra_tips": [
            "Whisper Large v3 Turbo provides faster response times with identical accuracy."
        ]
    }
}


def sanitize_error_text(text: str) -> str:
    """Redact API keys, tokens, and sensitive personal paths from error outputs."""
    if not text:
        return ""
    sanitized = re.sub(r'gsk_[a-zA-Z0-9_-]{10,}', 'gsk_<REDACTED_API_KEY>', text)
    sanitized = re.sub(r'(bearer\s+)[a-zA-Z0-9_\-\.]{15,}', r'\1<REDACTED_TOKEN>', sanitized, flags=re.IGNORECASE)
    home_dir = os.path.expanduser("~")
    if home_dir and home_dir in sanitized:
        sanitized = sanitized.replace(home_dir, "~")
    return sanitized


def generate_github_issue_url(
    title: str,
    category: str,
    error_details: str,
    system_info: Optional[Dict[str, str]] = None
) -> str:
    """Generate a direct URL to open a pre-filled GitHub Issue for FreeFlow."""
    sanitized_err = sanitize_error_text(error_details)
    
    sys_os = platform.system()
    sys_release = platform.release()
    sys_version = platform.version()
    py_ver = sys.version.split()[0]
    
    body = (
        f"### Description\n"
        f"FreeFlow issue in category **{category}**.\n\n"
        f"### Error Details\n"
        f"```text\n{sanitized_err}\n```\n\n"
        f"### Environment\n"
        f"- **FreeFlow Version:** v{APP_VERSION}\n"
        f"- **Operating System:** {sys_os} {sys_release} ({sys_version})\n"
        f"- **Python Version:** {py_ver}\n"
        f"- **Platform Machine:** {platform.machine()}\n\n"
        f"### Additional Context\n"
        f"<!-- Please provide any extra details or steps to reproduce here -->\n"
    )

    issue_title = f"[Bug Report]: {title}"
    params = {
        "title": issue_title,
        "body": body,
        "labels": "bug,diagnostics"
    }
    encoded_query = urllib.parse.urlencode(params)
    return f"{GITHUB_REPO_URL}/issues/new?{encoded_query}"


def get_common_diagnostic(topic_key: Optional[str] = None) -> ErrorDiagnostic:
    """
    Return a friendly, non-error diagnostic guide for common troubleshooting topics.
    Used when opening the guide manually from Settings or Tray menu without an active error.
    """
    key = topic_key if topic_key in COMMON_TOPICS else "api_key"
    topic = COMMON_TOPICS[key]

    diag = ErrorDiagnostic(
        category=topic["category"],
        title=topic["title"],
        summary=topic["summary"],
        steps=topic["steps"],
        primary_action_label=topic["primary_label"],
        primary_action_id=topic["primary_id"],
        secondary_action_label=topic["secondary_label"],
        secondary_action_id=topic["secondary_id"],
        raw_error="",
        sanitized_error="System Status: Normal. No active runtime error recorded.",
        github_issue_url=generate_github_issue_url(topic["title"], topic["category"], "User opened common troubleshooting guide"),
        extra_tips=topic.get("extra_tips", []),
        is_error=False
    )
    return diag


def diagnose_error(error_str: str, context: Optional[Dict[str, str]] = None) -> ErrorDiagnostic:
    """
    Analyze error output and return structured diagnosis with step-by-step solutions.
    If no error is provided, returns the Common Troubleshooting Guide.
    """
    err = str(error_str or "").strip()
    err_lower = err.lower()

    # Normal check or empty: return Common Troubleshooting Guide
    if not err or err_lower in (
        "normal", "general", "status check: normal diagnostics",
        "normal diagnostics check", "common", "help", "common troubleshooting"
    ):
        return get_common_diagnostic("api_key")

    sanitized = sanitize_error_text(err)

    # 1. Invalid or Missing Groq API Key
    if any(k in err_lower for k in [
        "invalid api key", "authenticationerror", "401", "unauthorized",
        "invalid_api_key", "groq client not initialized", "api key is empty",
        "please configure your groq_api_key", "incorrect api key provided"
    ]):
        category = "INVALID_API_KEY"
        title = "Invalid or Missing Groq API Key"
        summary = (
            "Groq rejected your API key. FreeFlow requires an active Groq API key "
            "to perform Whisper speech-to-text transcription."
        )
        steps = [
            "Open FreeFlow Preferences (Settings tab).",
            "Ensure your API key starts with 'gsk_' and contains no leading or trailing whitespace.",
            "If you don't have a key, create a free API key at console.groq.com/keys.",
            "Paste the new key into Preferences and click 'Test Connection'."
        ]
        extra_tips = [
            "Groq API keys are 100% free with generous rate limits for personal dictation.",
            "Make sure you didn't copy the placeholder text 'gsk_your_key_here'."
        ]
        diag = ErrorDiagnostic(
            category=category,
            title=title,
            summary=summary,
            steps=steps,
            primary_action_label="Open Preferences",
            primary_action_id="open_settings",
            secondary_action_label="Get Free Groq Key",
            secondary_action_id="open_groq_console",
            raw_error=err,
            sanitized_error=sanitized,
            extra_tips=extra_tips,
            is_error=True
        )
        diag.github_issue_url = generate_github_issue_url(title, category, sanitized)
        return diag

    # 2. Network Connection / Firewall / SSL Certificate Issue (Common on Windows)
    if any(k in err_lower for k in [
        "connection error", "apiconnectionerror", "connection refused", "winerror 10060",
        "winerror 10061", "urlerror", "temporary failure in name resolution",
        "certificate_verify_failed", "ssl error", "socket.timeout", "timed out",
        "cannot connect to proxy", "name or service not known", "getaddrinfo failed"
    ]):
        category = "NETWORK_FIREWALL"
        title = "Network Connection / Firewall Blocked"
        summary = (
            "FreeFlow could not establish a connection to Groq's servers (api.groq.com:443). "
            "On Windows, this is commonly caused by Windows Firewall, antivirus, or VPN blocking outbound traffic."
        )
        steps = [
            "Verify your computer has an active internet connection.",
            "Windows Defender / Firewall: Ensure Python or FreeFlow is allowed through Windows Defender Firewall.",
            "Antivirus / VPN: If using a VPN, corporate proxy, or third-party antivirus, temporarily whitelist api.groq.com:443.",
            "DNS Resolution: Ensure your network can resolve api.groq.com.",
            "Click 'Test Connection' below to verify when connectivity is restored."
        ]
        extra_tips = [
            "If your network requires a proxy, configure HTTP_PROXY and HTTPS_PROXY environment variables.",
            "Corporate or school networks may block AI API endpoints by default."
        ]
        diag = ErrorDiagnostic(
            category=category,
            title=title,
            summary=summary,
            steps=steps,
            primary_action_label="Test Connection",
            primary_action_id="test_connection",
            secondary_action_label="Open Preferences",
            secondary_action_id="open_settings",
            raw_error=err,
            sanitized_error=sanitized,
            extra_tips=extra_tips,
            is_error=True
        )
        diag.github_issue_url = generate_github_issue_url(title, category, sanitized)
        return diag

    # 3. Rate Limit Reached (HTTP 429)
    if any(k in err_lower for k in ["429", "ratelimiterror", "rate limit reached", "rate_limit_exceeded"]):
        category = "RATE_LIMIT"
        title = "Groq Rate Limit Reached"
        summary = (
            "You have temporarily exceeded the requests-per-minute (RPM) or daily audio quota "
            "for Groq's free tier."
        )
        steps = [
            "Wait 30 to 60 seconds and try speaking again.",
            "Keep recordings concise to stay well under per-minute rate limits.",
            "Check your current quota usage on the Groq Console at console.groq.com."
        ]
        extra_tips = [
            "Groq's free tier automatically resets every minute and midnight UTC."
        ]
        diag = ErrorDiagnostic(
            category=category,
            title=title,
            summary=summary,
            steps=steps,
            primary_action_label="Open Groq Console",
            primary_action_id="open_groq_console",
            secondary_action_label="Open Preferences",
            secondary_action_id="open_settings",
            raw_error=err,
            sanitized_error=sanitized,
            extra_tips=extra_tips,
            is_error=True
        )
        diag.github_issue_url = generate_github_issue_url(title, category, sanitized)
        return diag

    # 4. Microphone Audio Silence / Capture Failure
    if any(k in err_lower for k in [
        "recorded audio file is empty", "audio file is empty", "audio too short",
        "could not be decoded", "file size is 0", "silence", "no sound recorded"
    ]):
        category = "AUDIO_EMPTY"
        title = "Microphone Silence or Capture Failure"
        summary = (
            "The recorded audio buffer was silent or empty (0 bytes). "
            "Groq Whisper requires audible sound to transcribe."
        )
        steps = [
            "Open FreeFlow Preferences -> Audio Device -> Select your specific microphone.",
            "Check that your physical microphone is connected, turned on, and not muted.",
            "Windows / macOS / Linux: Verify Microphone Permissions are granted to this application in System Settings.",
            "Speak clearly into the microphone after pressing the recording hotkey."
        ]
        extra_tips = [
            "If your headset has a hardware mute switch or inline volume wheel, make sure it is unmuted.",
            "Try clicking 'Refresh Devices' in FreeFlow Preferences to detect newly plugged-in USB microphones."
        ]
        diag = ErrorDiagnostic(
            category=category,
            title=title,
            summary=summary,
            steps=steps,
            primary_action_label="Select Microphone Device",
            primary_action_id="open_audio_settings",
            secondary_action_label="Open Preferences",
            secondary_action_id="open_settings",
            raw_error=err,
            sanitized_error=sanitized,
            extra_tips=extra_tips,
            is_error=True
        )
        diag.github_issue_url = generate_github_issue_url(title, category, sanitized)
        return diag

    # 5. Model Deprecation / Offline / 404
    if any(k in err_lower for k in ["model_not_found", "model not found", "404", "does not exist", "decommissioned"]):
        category = "MODEL_ERROR"
        title = "Groq Model Unavailable"
        summary = (
            "The configured Whisper or LLM model was not recognized by Groq servers. "
            "It may have been deprecated or decommissioned."
        )
        steps = [
            "Open FreeFlow Preferences -> Speech Recognition Model.",
            "Select 'whisper-large-v3' or 'whisper-large-v3-turbo'.",
            "Under Formatting Model, select a supported model such as 'llama-3.1-8b-instant' or 'openai/gpt-oss-20b'."
        ]
        diag = ErrorDiagnostic(
            category=category,
            title=title,
            summary=summary,
            steps=steps,
            primary_action_label="Open Preferences",
            primary_action_id="open_settings",
            raw_error=err,
            sanitized_error=sanitized,
            is_error=True
        )
        diag.github_issue_url = generate_github_issue_url(title, category, sanitized)
        return diag

    # 6. Generic or Unknown Error Fallback (Only when an actual error string was given)
    category = "UNKNOWN"
    title = "Transcription Error Encountered"
    summary = (
        "FreeFlow encountered an error while communicating with the transcription service. "
        "Review the technical details below and try the suggested troubleshooting steps."
    )
    steps = [
        "Verify your internet connection and check if Groq's servers are online at status.groq.com.",
        "Check that your Groq API key is valid in FreeFlow Preferences.",
        "Restart FreeFlow and try speaking again.",
        "If the problem persists, click 'Report Issue on GitHub' below with the diagnostic trace."
    ]
    diag = ErrorDiagnostic(
        category=category,
        title=title,
        summary=summary,
        steps=steps,
        primary_action_label="Open Preferences",
        primary_action_id="open_settings",
        secondary_action_label="Report Issue on GitHub",
        secondary_action_id="report_github",
        raw_error=err,
        sanitized_error=sanitized,
        is_error=True
    )
    diag.github_issue_url = generate_github_issue_url(title, category, sanitized)
    return diag
