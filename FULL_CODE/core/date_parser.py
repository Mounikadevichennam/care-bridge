"""Date parser for discharge summaries.

Supports explicit date formats (DD/MM/YYYY, YYYY-MM-DD, DD-Mon-YYYY, Month DD YYYY)
and relative dates ('after 2 weeks', 'in 1 month') computed against
a reference admission/discharge date.
"""

from __future__ import annotations

import datetime
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12
}

class DateParser:
    """Parses dates from clinical text into standardized ISO format."""

    def __init__(self, reference_date: Optional[datetime.date] = None):
        self.reference_date = reference_date or datetime.date(2026, 1, 15)

    def parse_date(self, text: str, ref_date: Optional[datetime.date] = None) -> Optional[str]:
        """Convert any date string into unambiguous YYYY-MM-DD."""
        if not text:
            return None
        text = text.strip()
        ref = ref_date or self.reference_date

        # 1. ISO format YYYY-MM-DD
        iso_match = re.search(r'\b(20\d\d)[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b', text)
        if iso_match:
            y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
            try:
                return datetime.date(y, m, d).isoformat()
            except ValueError:
                pass

        # 2. DD-Mon-YYYY or DD Mon YYYY (e.g., 04-Nov-2024, 11-Nov-2024, 15 Jan 2026)
        mon_dmy = re.search(r'\b(0?[1-9]|[12]\d|3[01])[-/\s]([A-Za-z]{3,})[-/\s](20\d\d)\b', text)
        if mon_dmy:
            d = int(mon_dmy.group(1))
            m_str = mon_dmy.group(2).lower()[:3]
            y = int(mon_dmy.group(3))
            if m_str in MONTH_MAP:
                try:
                    return datetime.date(y, MONTH_MAP[m_str], d).isoformat()
                except ValueError:
                    pass

        # 3. Mon-DD-YYYY or Month DD, YYYY (e.g., Nov 04 2024, January 15, 2026)
        mon_mdy = re.search(r'\b([A-Za-z]{3,})[-/\s](0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?[,\s]+(20\d\d)\b', text)
        if mon_mdy:
            m_str = mon_mdy.group(1).lower()[:3]
            d = int(mon_mdy.group(2))
            y = int(mon_mdy.group(3))
            if m_str in MONTH_MAP:
                try:
                    return datetime.date(y, MONTH_MAP[m_str], d).isoformat()
                except ValueError:
                    pass

        # 4. DD/MM/YYYY or DD-MM-YYYY (numeric month)
        dmy_match = re.search(r'\b(0?[1-9]|[12]\d|3[01])[-/.](0?[1-9]|1[0-2])[-/.](20\d\d)\b', text)
        if dmy_match:
            d, m, y = int(dmy_match.group(1)), int(dmy_match.group(2)), int(dmy_match.group(3))
            try:
                return datetime.date(y, m, d).isoformat()
            except ValueError:
                pass

        # 5. Relative dates: 'after 2 weeks', 'in 10 days', 'after 1 month'
        rel_days = re.search(r'(?:after|in|within)\s+(\d+)\s*days?', text, re.IGNORECASE)
        if rel_days:
            days = int(rel_days.group(1))
            return (ref + datetime.timedelta(days=days)).isoformat()

        rel_weeks = re.search(r'(?:after|in|within)\s+(\d+)\s*weeks?', text, re.IGNORECASE)
        if rel_weeks:
            weeks = int(rel_weeks.group(1))
            return (ref + datetime.timedelta(days=weeks * 7)).isoformat()

        rel_months = re.search(r'(?:after|in|within)\s+(\d+)\s*months?', text, re.IGNORECASE)
        if rel_months:
            months = int(rel_months.group(1))
            return (ref + datetime.timedelta(days=months * 30)).isoformat()

        return None
