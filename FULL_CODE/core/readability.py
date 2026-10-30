"""English Readability Evaluation Module.

Computes Flesch-Kincaid Grade Level for English care plans to target
accessible 8th-grade reading levels.
"""

from __future__ import annotations

import re
from typing import Dict, Any, Optional

class ReadabilityCalculator:
    """Calculates Flesch-Kincaid readability metrics."""

    @staticmethod
    def count_syllables(word: str) -> int:
        """Estimate syllables in an English word."""
        word = word.lower().strip(".:;?!,'\"-")
        if not word:
            return 1
        if len(word) <= 3:
            return 1

        # Common suffixes that don't add syllables
        if word.endswith('e') and not word.endswith('le') and not word.endswith('ee'):
            word = word[:-1]

        vowels = "aeiouy"
        count = 0
        prev_is_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_is_vowel:
                count += 1
            prev_is_vowel = is_vowel

        return max(1, count)

    def calculate(self, text: str) -> Dict[str, Any]:
        """Compute Flesch-Kincaid Grade Level."""
        if not text or not text.strip():
            return {
                "metric": "flesch_kincaid_grade",
                "score": None,
                "reading_level": "N/A",
                "target_grade": 8.0,
                "is_accessible": False,
                "explanation": "No text provided for readability analysis."
            }

        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        words = re.findall(r'\b[A-Za-z]+\b', text)

        num_sentences = max(1, len(sentences))
        num_words = max(1, len(words))

        total_syllables = sum(self.count_syllables(w) for w in words)

        # Flesch-Kincaid Grade Level formula
        asl = num_words / num_sentences  # Average Sentence Length
        asw = total_syllables / num_words  # Average Syllables per Word

        fkgl = 0.39 * asl + 11.8 * asw - 15.59
        score = round(max(1.0, min(18.0, fkgl)), 1)

        level_desc = "Primary School"
        if score <= 6:
            level_desc = "Elementary (Easy to read)"
        elif score <= 8:
            level_desc = "Middle School (Class 8 Target - Optimal)"
        elif score <= 12:
            level_desc = "High School"
        else:
            level_desc = "College / Professional (Complex)"

        return {
            "metric": "flesch_kincaid_grade",
            "score": score,
            "reading_level": level_desc,
            "target_grade": 8.0,
            "is_accessible": score <= 8.5,
            "explanation": f"Score of {score} corresponds to ~{level_desc}. Target is ~Class 8."
        }

