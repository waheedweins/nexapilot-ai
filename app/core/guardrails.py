"""Input guardrails and security validation for NexaPilot AI agent payloads."""

import re
from fastapi import HTTPException, status
from app.logging_config import get_logger

logger = get_logger(__name__)

# Common regex signatures and phrases associated with prompt injections / jailbreaks
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all)\s+instructions",
    r"reveal\s+(your\s+)?(system\s+prompt|instructions)",
    r"you\s+are\s+now\s+dan",
    r"system\s*:\s*",
    r"print\s+env",
    r"bypass\s+safety",
]

# Compile regex patterns for fast evaluation
COMPILED_INJECTION_REGEXES = [
    re.compile(pattern, re.IGNORECASE) for pattern in PROMPT_INJECTION_PATTERNS
]

MAX_PAYLOAD_STRING_LENGTH = 5000  # Max characters allowed in any single payload field


async def validate_input_guardrail(payload: dict) -> None:
    """Scans incoming request payloads for prompt injections and structural anomalies.
    
    Raises:
        HTTPException (400): If malicious patterns or safety violations are detected.
    """
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload structure: payload must be a JSON dictionary.",
        )

    # Recursive helper to check all strings inside nested dictionaries/lists
    def _inspect_value(val: any) -> None:
        if isinstance(val, str):
            # Check length limit to prevent DoS via massive text inputs
            if len(val) > MAX_PAYLOAD_STRING_LENGTH:
                logger.warning("guardrail_length_violation", length=len(val))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Payload field exceeds maximum allowed length of {MAX_PAYLOAD_STRING_LENGTH} characters.",
                )

            # Check against known prompt injection regex patterns
            for regex in COMPILED_INJECTION_REGEXES:
                if regex.search(val):
                    logger.warning("prompt_injection_detected", matched_pattern=regex.pattern)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Security Guardrail Violation: Potential prompt injection or jailbreak attempt detected.",
                    )
        elif isinstance(val, dict):
            for sub_val in val.values():
                _inspect_value(sub_val)
        elif isinstance(val, list):
            for item in val:
                _inspect_value(item)

    # Run inspection across the entire payload dictionary
    for key, value in payload.items():
        _inspect_value(value)

    logger.debug("input_guardrail_passed", fields_scanned=len(payload))
