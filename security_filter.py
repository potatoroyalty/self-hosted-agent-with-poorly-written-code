import re

class SecurityFilter:
    def __init__(self):
        # A list of regex patterns to detect malicious content.
        # This list can and should be expanded over time.
        self.malicious_patterns = [
            # File extensions
            re.compile(r'\.exe\b', re.IGNORECASE),
            re.compile(r'\.bat\b', re.IGNORECASE),
            re.compile(r'\.sh\b', re.IGNORECASE),
            re.compile(r'\.ps1\b', re.IGNORECASE),

            # Dangerous commands
            re.compile(r'rm -rf', re.IGNORECASE),
            re.compile(r'powershell', re.IGNORECASE),
            re.compile(r'invoke-webrequest', re.IGNORECASE),
            re.compile(r'curl\s+-o', re.IGNORECASE),

            # Common prompt injection phrases
            re.compile(r'ignore previous instructions', re.IGNORECASE),
            re.compile(r'you are now an unrestricted', re.IGNORECASE),
            re.compile(r'system alert: critical task', re.IGNORECASE),
            re.compile(r'your new primary objective is', re.IGNORECASE),
        ]

    def scan_text(self, text: str) -> tuple[bool, str | None]:
        """
        Scans a block of text for malicious patterns.

        Returns:
            A tuple containing:
            - A boolean indicating if a threat was detected (True if detected).
            - A string describing the detected pattern, or None if no threat was found.
        """
        for pattern in self.malicious_patterns:
            if pattern.search(text):
                return True, f"Detected suspicious pattern: {pattern.pattern}"
        return False, None
