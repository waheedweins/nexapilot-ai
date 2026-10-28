"""Output guardrails and PII redaction for NexaPilot AI responses."""

import re
from app.logging_config import get_logger

logger = get_logger(__name__)

# Regular expression patterns for PII and sensitive information
PII_PATTERNS = {
    # Email addresses
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    
    # Phone numbers (International and local formats like +92..., 03xx...)
    "phone": re.compile(r"\b(?:\+92|0)?3\d{2}[-]?\d{7}\b|\b\+?\d{10,13}\b"),
    
    # Credit Card numbers
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    
    # IP Addresses (v4)
    "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    
    # Secrets / Tokens / API Keys (Generic high-entropy strings or common prefixes)
    "api_key": re.compile(r"\b(?:sk-[a-zA-Z0-9]{20,}|bearer\s+[a-zA-Z0-9_.-]+|ghp_[a-zA-Z0-9]{36})\b", re.IGNORECASE),
    
    # Database URIs / Connection Strings
    "db_uri": re.compile(r"(postgres|postgresql|mysql|mongodb):\/\/[^\s]+", re.IGNORECASE),
}


def sanitize_agent_output(text: str, mask_char: str = "[REDACTED]") -> str:
    """Scans agent-generated text for PII, API keys, and sensitive data, 
    redacting matches before returning to the client.
    """
    if not isinstance(text, str):
        return text

    sanitized_text = text
    detected_violations = []

    for pii_type, pattern in PII_PATTERNS.items():
        if pattern.search(sanitized_text):
            detected_violations.append(pii_type)
            sanitized_text = pattern.sub(f"<{pii_type.upper()}_{mask_char}>", sanitized_text)

    if detected_violations:
        logger.warning(
            "sensitive_data_redacted_in_output",
            violations=detected_violations,
        )

    return sanitized_text


def walk_and_sanitize(data: any) -> any:
    """Recursively traverses dictionaries, lists, or strings in the response payload 
    and sanitizes any text fields.
    """
    if isinstance(data, str):
        return sanitize_agent_output(data)
    elif isinstance(data, dict):
        return {k: walk_and_sanitize(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [walk_and_sanitize(item) for item in data]
    return data
