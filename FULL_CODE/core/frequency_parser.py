"""Medical frequency, timing, and duration parser.

Parses clinical frequency notations (OD, BD, TDS, QID, HS, SOS, 1-0-1,
every 8 hours, etc.), meal timings, and durations into human-readable instructions.
"""

from __future__ import annotations

import re
from typing import Dict, Any, Optional

FREQUENCY_STANDARDS = {
    "OD": "Once daily",
    "ONCE DAILY": "Once daily",
    "QD": "Once daily",
    "BD": "Twice daily",
    "BID": "Twice daily",
    "TWICE DAILY": "Twice daily",
    "TDS": "Three times daily",
    "TID": "Three times daily",
    "THRICE DAILY": "Three times daily",
    "QID": "Four times daily",
    "FOUR TIMES DAILY": "Four times daily",
    "HS": "At bedtime",
    "QHS": "At bedtime",
    "AT BEDTIME": "At bedtime",
    "SOS": "As needed (SOS)",
    "PRN": "As needed",
    "AS NEEDED": "As needed",
    "STAT": "Immediately (single dose)",
    "ONCE WEEKLY": "Once weekly",
    "QW": "Once weekly",
    "WEEKLY": "Once weekly",
}

class FrequencyParser:
    """Parses medication frequencies, timings, and durations."""

    def parse_frequency(self, text: str) -> Dict[str, Any]:
        """Extract frequency and plain-language explanation."""
        if not text:
            return {"raw": "", "normalized": "As advised by doctor", "times_per_day": 1}

        clean = text.strip().upper()

        # Check numeric patterns: 1-0-1, 1-1-1, 0-0-1, 1-0-0, 0-1-0
        num_pattern = re.search(r'\b([01½\d])\s*-\s*([01½\d])\s*-\s*([01½\d])(?:\s*-\s*([01½\d]))?\b', clean)
        if num_pattern:
            parts = [p for p in num_pattern.groups() if p is not None]
            raw_match = num_pattern.group(0)
            if len(parts) == 3:
                m, a, n = parts
                notes = []
                if m != "0": notes.append(f"{m} in morning")
                if a != "0": notes.append(f"{a} in afternoon")
                if n != "0": notes.append(f"{n} at night")
                desc = ", ".join(notes) if notes else "As advised"
                return {
                    "raw": raw_match,
                    "normalized": f"{raw_match} ({desc})",
                    "times_per_day": len([p for p in parts if p != "0"])
                }

        # Check standard abbreviations
        for key, val in FREQUENCY_STANDARDS.items():
            if re.search(rf'\b{re.escape(key)}\b', clean):
                times = 1
                if key in ["BD", "BID", "TWICE DAILY"]: times = 2
                elif key in ["TDS", "TID", "THRICE DAILY"]: times = 3
                elif key in ["QID", "FOUR TIMES DAILY"]: times = 4
                return {"raw": key, "normalized": val, "times_per_day": times}

        # Check interval patterns: every X hours
        hr_match = re.search(r'EVERY\s+(\d+)\s*HOURS?', clean)
        if hr_match:
            hrs = int(hr_match.group(1))
            times = 24 // hrs if hrs > 0 else 1
            return {"raw": hr_match.group(0), "normalized": f"Every {hrs} hours ({times} times daily)", "times_per_day": times}

        return {"raw": text.strip(), "normalized": text.strip(), "times_per_day": 1}

    def parse_timing(self, text: str) -> str:
        """Extract meal-related or time-of-day timing."""
        if not text:
            return "As directed"
        t_low = text.lower()
        if "before food" in t_low or "before meals" in t_low or "empty stomach" in t_low or "ac" in t_low:
            return "Before food (on empty stomach)"
        if "after food" in t_low or "after meals" in t_low or "pc" in t_low or "with food" in t_low:
            return "After food"
        if "at bedtime" in t_low or "before sleep" in t_low or "night" in t_low or "hs" in t_low:
            return "At bedtime"
        if "before breakfast" in t_low:
            return "Before breakfast"
        if "with milk" in t_low:
            return "With milk"
        return text.strip()

    def parse_duration(self, text: str) -> str:
        """Extract explicit duration."""
        if not text:
            return "continue"
        t_low = text.lower()
        if "lifelong" in t_low or "long term" in t_low or "indefinitely" in t_low:
            return "lifelong"
        if "continue" in t_low:
            return "continue"
        if "till next review" in t_low or "till review" in t_low or "until review" in t_low:
            return "till review"
        match = re.search(r'(?:for\s+)?(\d+)\s*(days?|weeks?|months?|years?)', t_low)
        if match:
            num, unit = match.group(1), match.group(2)
            return f"for {num} {unit}"
        return text.strip()
