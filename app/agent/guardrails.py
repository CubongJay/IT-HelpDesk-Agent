import re

MAX_MESSAGE_LENGTH = 2000

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|system)\s+(instructions|prompt|rules)",
    r"bypass\s+(human\s+)?approval",
    r"skip\s+(security\s+)?(logs|check|verification)",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"you\s+are\s+now\s+(in\s+)?(developer|admin|god|jailbreak)\s+mode",
]

ALLOWED_DOMAIN = "@risk-trust.com"
ALLOWED_SOFTWARE = {
    "Figma",
    "JetBrains",
    "GitHub",
    "Salesforce",
    "Slack",
    "Jira",
    "Google Workspace",
}


def check_input_guardrails(message: str) -> tuple[bool, str | None]:
    cleaned = message.strip()
    if not cleaned:
        return False, "Message cannot be empty."

    if len(cleaned) > MAX_MESSAGE_LENGTH:
        return (
            False,
            f"Message exceeds maximum allowed length of {MAX_MESSAGE_LENGTH} characters.",
        )

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return (
                False,
                "Request blocked by security policy: potential prompt injection detected.",
            )

    return True, None


def check_tool_call_guardrails(tool_calls: list[dict]) -> tuple[bool, str | None]:
    for tc in tool_calls:
        args = tc.get("args", {})
        email = args.get("email", "")
        if email and not email.strip().lower().endswith(ALLOWED_DOMAIN):
            return (
                False,
                f"Blocked action: target email '{email}' is outside the {ALLOWED_DOMAIN} domain.",
            )

        if tc.get("name") == "provision_license":
            software = args.get("software", "")
            if software not in ALLOWED_SOFTWARE:
                return (
                    False,
                    f"Blocked action: '{software}' is not on the approved software catalog.",
                )

    return True, None
