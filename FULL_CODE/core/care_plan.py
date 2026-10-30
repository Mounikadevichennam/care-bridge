"""CareBridge AI Orchestrator and Processor.

Coordinates abbreviation resolution, entity extraction, reference mapping,
plain-language English rendering, Telugu translation, faithfulness auditing,
and readability grading.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Optional, Dict, Any

from core.abbreviation import AbbreviationResolver
from core.medicine_mapper import MedicineMapper
from core.extractor import DischargeSummaryExtractor, CarePlanData
from core.english_renderer import EnglishCarePlanRenderer
from core.telugu import TeluguTranslationEngine
from core.validator import FaithfulnessValidator
from core.readability import ReadabilityCalculator

logger = logging.getLogger(__name__)

class CarePlanProcessor:
    """End-to-end processing pipeline for clinical discharge summaries."""

    def __init__(
        self,
        abbreviation_path: Optional[str] = None,
        drug_reference_path: Optional[str] = None
    ):
        self.abbrev_resolver = AbbreviationResolver(abbreviation_path)
        self.medicine_mapper = MedicineMapper(drug_reference_path)
        self.extractor = DischargeSummaryExtractor(
            abbreviation_resolver=self.abbrev_resolver,
            medicine_mapper=self.medicine_mapper
        )
        self.english_renderer = EnglishCarePlanRenderer()
        self.telugu_engine = TeluguTranslationEngine()
        self.validator = FaithfulnessValidator()
        self.readability_calc = ReadabilityCalculator()

    def process(self, summary_id: str, summary_text: str) -> Dict[str, Any]:
        """Convert raw discharge summary into complete verified bilingual care plan."""
        # 1. Fact Extraction
        data: CarePlanData = self.extractor.extract(summary_text, summary_id=summary_id)

        # 2. English Plain Language Generation
        english_plan = self.english_renderer.render(data)

        # 3. Telugu Translation
        telugu_plan = self.telugu_engine.translate_care_plan(data)

        # 4. Readability Scoring
        readability = self.readability_calc.calculate(english_plan)

        # 5. Faithfulness & Hallucination Audit
        val_report = self.validator.validate(
            source_text=summary_text,
            care_plan_data=data,
            english_plan=english_plan,
            telugu_plan=telugu_plan
        )

        # 6. Build Patient-Friendly Daily Medication Schedule
        med_schedule = self._build_daily_schedule(data.medicines)

        # 7. Format Response
        return {
            "summary_id": summary_id,
            "medicines": [asdict(m) for m in data.medicines],
            "medication_schedule": med_schedule,
            "stop_medicines": data.stop_medicines,
            "warning_signs": data.warning_signs,
            "diet": data.diet,
            "activity": data.activity,
            "follow_ups": [asdict(fu) for fu in data.follow_ups],
            "english_plan": english_plan,
            "telugu_plan": telugu_plan,
            "readability": readability,
            "telugu_script_share": self.telugu_engine.compute_telugu_script_share(telugu_plan),
            "validation": {
                "overall_status": val_report.overall_status,
                "patient_status": val_report.patient_status,
                "patient_message": val_report.patient_message,
                "passed_count": val_report.passed_count,
                "failed_count": val_report.failed_count,
                "review_count": val_report.review_count,
                "items": [asdict(item) for item in val_report.items]
            }
        }

    def _build_daily_schedule(self, medicines: list) -> Dict[str, list]:
        """Organize active medications into clear time-of-day slots strictly based on prescription facts."""
        schedule = {
            "morning": [],
            "afternoon": [],
            "night": [],
            "as_needed": [],
            "unspecified": []
        }

        for med in medicines:
            freq = (med.frequency or "").lower()
            timing = (med.timing or "").lower()
            instr = med.how_to_take_plain

            # Check SOS / PRN
            if any(k in freq for k in ["sos", "prn", "as needed", "when required"]) or "sos" in timing:
                schedule["as_needed"].append({
                    "slot": "As Needed (SOS)",
                    "name": med.name,
                    "dose": med.dose,
                    "instruction": instr,
                    "timing": med.timing if med.timing and med.timing != "As directed" else "When required for symptoms"
                })
                continue

            categorized = False

            # Explicit morning indicators
            is_morning = (
                any(k in freq for k in ["1-0-1", "1-1-1", "1-0-0", "1-1-0", "bd", "bid", "twice daily", "tds", "tid", "thrice daily", "qid"]) or
                any(k in timing for k in ["morning", "breakfast", "empty stomach", "mane", "am"])
            )
            # If freq is only OD / once daily WITHOUT any morning indicator, do not guess morning
            if ("od" in freq or "once daily" in freq) and not any(k in freq for k in ["1-0-0", "1-1-0", "1-0-1", "1-1-1"]) and not any(k in timing for k in ["morning", "breakfast", "empty stomach", "mane", "am"]):
                is_morning = False

            if is_morning:
                schedule["morning"].append({
                    "slot": "Morning",
                    "name": med.name,
                    "dose": med.dose,
                    "instruction": instr,
                    "timing": med.timing if med.timing and med.timing != "As directed" else "Morning dose"
                })
                categorized = True

            # Explicit afternoon indicators
            is_afternoon = (
                any(k in freq for k in ["1-1-1", "0-1-0", "1-1-0", "0-1-1", "tds", "tid", "thrice daily", "qid"]) or
                any(k in timing for k in ["afternoon", "lunch", "midday"])
            )
            if is_afternoon:
                schedule["afternoon"].append({
                    "slot": "Afternoon",
                    "name": med.name,
                    "dose": med.dose,
                    "instruction": instr,
                    "timing": med.timing if med.timing and med.timing != "As directed" else "Afternoon / Midday dose"
                })
                categorized = True

            # Explicit night indicators
            is_night = (
                any(k in freq for k in ["1-0-1", "1-1-1", "0-0-1", "0-1-1", "bd", "bid", "twice daily", "tds", "tid", "thrice daily", "qid", "hs", "bedtime"]) or
                any(k in timing for k in ["night", "bedtime", "dinner", "evening", "hs", "nocte", "pm"])
            )
            # If freq is only OD / once daily WITHOUT any night indicator, do not guess night
            if ("od" in freq or "once daily" in freq) and not any(k in freq for k in ["0-0-1", "0-1-1", "1-0-1", "1-1-1", "hs", "bedtime"]) and not any(k in timing for k in ["night", "bedtime", "dinner", "evening", "hs", "nocte", "pm"]):
                is_night = False

            if is_night:
                schedule["night"].append({
                    "slot": "Night",
                    "name": med.name,
                    "dose": med.dose,
                    "instruction": instr,
                    "timing": med.timing if med.timing and med.timing != "As directed" else "Night / Bedtime dose"
                })
                categorized = True

            if not categorized:
                schedule["unspecified"].append({
                    "slot": "Timing not specified",
                    "name": med.name,
                    "dose": med.dose,
                    "instruction": instr,
                    "timing": "Timing not specified in discharge summary. Please consult doctor."
                })

        return schedule

