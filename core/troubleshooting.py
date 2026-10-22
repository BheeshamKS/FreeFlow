"""
FreeFlow Comprehensive Error Troubleshooting & Diagnostics
Categorizes runtime exceptions, provides step-by-step remediation guides,
and constructs pre-filled GitHub issue templates with redacted secrets.
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


def sanitize_error_text(text: str) -> str:
    """Redact API keys, tokens, and sensitive personal paths from error outputs."""
    if not text:
        return ""
    # Redact Groq API Keys (e.g., gsk_1234567890abcdef...)
    sanitized = re.sub(r'gsk_[a-zA-Z0-9_-]{10,}', 'gsk_<REDACTED_API_KEY>', text)
    # Redact generic bearer/auth tokens
    sanitized = re.sub(r'(bearer\s+)[a-zA-Z0-9_\-\.]{15,}', r'\1<REDACTED_TOKEN>', sanitized, flags=re.IGNORECASE)
    # Redact user home directory names in filepaths
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
    
    # System info gathering
    sys_os = platform.system()
    sys_release = platform.release()
    sys_version = platform.version()
    py_ver = sys.version.split()[0]
    
    body = (
        f"### Description\n"
        f"FreeFlow encountered an error in category **{category}**.\n\n"
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


def diagnose_error(error_str: str, context: Optional[Dict[str, str]] = None) -> ErrorDiagnostic:
    """
    Analyze error output and return structured diagnosis with step-by-step solutions.
    Handles invalid API keys, network/firewall blocks on Windows/Linux/macOS,
    rate limits, empty audio captures, and missing models.
    """
    err = str(error_str or "").strip()
    err_lower = err.lower()
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
            extra_tips=extra_tips
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
            "Antivirus / VPN: If using a VPN, corporate proxy, or third-party antivirus (Avast, McAfee), temporarily whitelist api.groq.com.",
            "DNS Resolution: Ensure your network can resolve api.groq.com (try pinging or browsing to https://api.groq.com).",
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
            extra_tips=extra_tips
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
            extra_tips=extra_tips
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
            extra_tips=extra_tips
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
            sanitized_error=sanitized
        )
        diag.github_issue_url = generate_github_issue_url(title, category, sanitized)
        return diag

    # 6. Generic or Unknown Error Fallback
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
        sanitized_error=sanitized
    )
    diag.github_issue_url = generate_github_issue_url(title, category, sanitized)
    return diag
