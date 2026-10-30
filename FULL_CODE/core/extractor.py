"""Clinical Information Extraction Engine for Discharge Summaries.

Extracts medicines, dosages, frequencies, timings, durations,
stop-medicines, follow-up appointments, warning signs, diet, and activity
guidelines using rule-based parsing with source tracing.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from core.abbreviation import AbbreviationResolver
from core.medicine_mapper import MedicineMapper
from core.frequency_parser import FrequencyParser
from core.date_parser import DateParser

logger = logging.getLogger(__name__)

@dataclass
class MedicineInfo:
    name: str
    dose: str
    frequency: str
    timing: str
    duration: str
    how_to_take_plain: str
    source_text: str = ""

@dataclass
class FollowUpInfo:
    date: str
    with_whom: str
    purpose: str
    source_text: str = ""

@dataclass
class CarePlanData:
    summary_id: str
    medicines: List[MedicineInfo] = field(default_factory=list)
    stop_medicines: List[Dict[str, str]] = field(default_factory=list)
    warning_signs: List[str] = field(default_factory=list)
    diet: List[str] = field(default_factory=list)
    activity: List[str] = field(default_factory=list)
    follow_ups: List[FollowUpInfo] = field(default_factory=list)
    diagnoses: List[str] = field(default_factory=list)
    extraction_warnings: List[str] = field(default_factory=list)

class DischargeSummaryExtractor:
    """Extracts structured clinical facts from clinical discharge notes."""

    def __init__(
        self,
        abbreviation_resolver: Optional[AbbreviationResolver] = None,
        medicine_mapper: Optional[MedicineMapper] = None
    ):
        self.abbrev = abbreviation_resolver or AbbreviationResolver()
        self.med_mapper = medicine_mapper or MedicineMapper()
        self.freq_parser = FrequencyParser()
        self.date_parser = DateParser()

    def extract(self, text: str, summary_id: str = "DOC-001") -> CarePlanData:
        """Execute extraction pipeline on discharge summary text."""
        data = CarePlanData(summary_id=summary_id)
        if not text or not text.strip():
            data.extraction_warnings.append("Empty discharge summary provided.")
            return data

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # Section boundaries
        current_section = "GENERAL"
        section_lines: Dict[str, List[str]] = {
            "DIAGNOSIS": [],
            "MEDICATIONS": [],
            "STOP_MEDICATIONS": [],
            "WARNING_SIGNS": [],
            "DIET": [],
            "ACTIVITY": [],
            "FOLLOW_UP": [],
            "GENERAL": []
        }

        for line in lines:
            upper = line.upper().strip()
            if any(k in upper for k in ["FINAL DIAGNOSIS", "DIAGNOSIS:", "DIAGNOSIS -", "DIAGNOSES"]):
                current_section = "DIAGNOSIS"
            elif any(k in upper for k in ["STOP MEDICINES", "STOP MEDICATIONS", "MEDICINES TO STOP", "DISCONTINUED MEDICATIONS", "DISCONTINUE:", "STOP:"]):
                current_section = "STOP_MEDICATIONS"
            elif any(k in upper for k in [
                "ADV ON DISCHARGE", "TREATMENT ADVISED ON DISCHARGE", "MEDICATIONS AT DISCHARGE",
                "DISCHARGE MEDICATIONS", "MEDICATIONS ON DISCHARGE", "DISCHARGE MEDICINE",
                "RX ON DISCHARGE", "ADVICE ON DISCHARGE", "MEDICINE:", "RX:", "DISCHARGE RX", "PRESCRIPTION:"
            ]):
                current_section = "MEDICATIONS"
            elif any(k in upper for k in [
                "WARNING SIGNS", "RED FLAGS", "EMERGENCY SIGNS", "WHEN TO RETURN",
                "DANGER SIGNS", "REPORT IMMEDIATELY", "RETURN TO EMERGENCY", "COME BACK TO THE HOSPITAL"
            ]):
                current_section = "WARNING_SIGNS"
            elif any(k in upper for k in ["DIET ADVICE", "DIETARY ADVICE", "DIET INSTRUCTIONS", "DIET:"]):
                current_section = "DIET"
            elif any(k in upper for k in ["PHYSICAL ACTIVITY", "ACTIVITY RESTRICTIONS", "EXERCISE:", "ACTIVITY:"]):
                current_section = "ACTIVITY"
            elif any(k in upper for k in ["FOLLOW UP", "FOLLOW-UP", "REVIEW APPOINTMENT", "NEXT VISIT", "OPD REVIEW", "F/U"]):
                current_section = "FOLLOW_UP"
            elif any(k in upper for k in ["INSTRUCTIONS -", "WOUND CARE:", "OTHERS:", "GENERAL:"]):
                current_section = "GENERAL"
            elif any(k in upper for k in ["PREPARED BY:", "VERIFIED BY:", "SIGNATURE:"]):
                current_section = "GENERAL"
            else:
                section_lines[current_section].append(line)

        # If no explicit medications section was found, check all lines for medication patterns
        if not section_lines["MEDICATIONS"]:
            for line in lines:
                if any(kw in line.upper() for kw in ["TAB", "CAP", "INJ", "SYR", "MG", "MCG", "ML", "OD", "BD", "TDS", "QID", "HS"]):
                    section_lines["MEDICATIONS"].append(line)

        # 1. Parse Stop Medications first (so we isolate them)
        stop_names = self._parse_stop_medications(section_lines["STOP_MEDICATIONS"], text, data)

        # 2. Parse Active Medications
        self._parse_active_medications(section_lines["MEDICATIONS"], stop_names, data)

        # 3. Parse Warning Signs
        self._parse_bullet_list(section_lines["WARNING_SIGNS"], data.warning_signs, text, ["chest pain", "breathlessness", "fever", "bleeding", "dizziness"])

        # 4. Parse Diet Instructions
        self._parse_bullet_list(section_lines["DIET"], data.diet, text, ["salt", "sugar", "fluid", "oil", "protein", "fiber", "spicy"])

        # 5. Parse Activity Instructions
        self._parse_bullet_list(section_lines["ACTIVITY"], data.activity, text, ["bed rest", "walking", "lifting", "driving", "climbing", "physiotherapy"])

        # 6. Parse Follow-up Appointments
        self._parse_follow_ups(section_lines["FOLLOW_UP"], text, data)

        return data

    def _parse_stop_medications(self, lines: List[str], full_text: str, data: CarePlanData) -> set:
        stop_names = set()
        ignore_words = {"THE", "THIS", "ANY", "ALL", "MEDICATIONS", "MEDICINES", "AND", "TAB", "CAP", "INJ", "DRUG", "DRUGS", "NONE", "NIL", "STOP", "DISCONTINUE", "HOLD"}

        candidates = list(lines)
        for ln in full_text.splitlines():
            if re.search(r'^\s*[\d\.\-\*•]*\s*(?:STOP|DISCONTINUE|HOLD|D/C)\b', ln, re.IGNORECASE):
                if ln not in candidates:
                    candidates.append(ln)

        for line in candidates:
            clean = re.sub(r'^[\s\d\.\-\*•]*\b(?:STOP|DISCONTINUE|HOLD|D/C)\b\s*(?:Tab\.?|Cap\.?|Inj\.?)?\s*', '', line, flags=re.IGNORECASE).strip()
            if not clean:
                continue

            dname_m = re.match(r'([A-Za-z0-9\-]+)', clean)
            if dname_m:
                dname = dname_m.group(1).strip()
                if dname.upper() not in ignore_words and len(dname) > 2:
                    stop_names.add(dname.upper())

                    reason = "Discontinued on discharge"
                    reason_m = re.search(r'\((.*?)\)', clean)
                    if reason_m:
                        reason = reason_m.group(1).strip()
                    elif "-" in clean:
                        reason = clean.split("-", 1)[1].strip()

                    data.stop_medicines.append({
                        "name": dname,
                        "reason": reason,
                        "source_text": line
                    })
        return stop_names

    def _parse_active_medications(self, lines: List[str], stop_names: set, data: CarePlanData):
        dose_regex = re.compile(
            r'(\b\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?\s*(?:mg|mcg|microgram|g|ml|iu|units?|puffs?)\b|½\s*(?:tab|tablet)|half\s+tablet)',
            re.IGNORECASE
        )
        freq_regex = re.compile(
            r'(\b(?:OD|BD|BID|TDS|TID|QID|HS|QHS|SOS|PRN|STAT|once daily|twice daily|thrice daily|four times daily|[01½\d]\s*-\s*[01½\d]\s*-\s*[01½\d](?:\s*-\s*[01½\d])?)\b)',
            re.IGNORECASE
        )
        duration_regex = re.compile(
            r'((?:for\s+)?\d+\s*(?:days?|weeks?|months?|years?)|lifelong|till next review|continue)',
            re.IGNORECASE
        )
        timing_regex = re.compile(
            r'((?:before|after)\s+(?:food|meals|breakfast|lunch|dinner)|at bedtime|on empty stomach|with food|with meals|morning and night|morning and evening)',
            re.IGNORECASE
        )

        for line in lines:
            line_clean = re.sub(r'^\s*[\d\.\-\*•\)]+\s*', '', line).strip()
            if not line_clean or len(line_clean) < 3:
                continue

            # Skip header or noise lines
            if re.search(r'^\s*[\d\.\-\*•]*\s*(?:STOP|DISCONTINUE|HOLD|D/C)\b', line_clean, re.IGNORECASE) or "STOP MEDICINES" in line_clean.upper():
                continue

            # Extract dose
            dose = ""
            dose_m = dose_regex.search(line_clean)
            if dose_m:
                dose = dose_m.group(1).strip()

            # Extract frequency
            freq_raw = ""
            freq_m = freq_regex.search(line_clean)
            if freq_m:
                freq_raw = freq_m.group(1).strip()

            # Extract timing
            timing = ""
            timing_m = timing_regex.search(line_clean)
            if timing_m:
                timing = timing_m.group(1).strip()

            # Extract duration
            duration = ""
            dur_m = duration_regex.search(line_clean)
            if dur_m:
                duration = dur_m.group(1).strip()

            # Extract Medicine Name: strip prefix Tab/Cap/Inj/Syr
            name_candidate = line_clean
            name_candidate = re.sub(r'^(?:Tab(?:let)?|Cap(?:sule)?|Inj(?:ection)?|Syr(?:up)?|Oint(?:ment)?|Neb(?:ulizer)?|Gel|Cream|MDI|DPI|Drops?)\.?\s*', '', name_candidate, flags=re.IGNORECASE)

            # Find boundary where dose/strength begins
            cut_pos = len(name_candidate)
            if dose and dose in name_candidate:
                cut_pos = min(cut_pos, name_candidate.find(dose))
            if freq_raw and freq_raw in name_candidate:
                cut_pos = min(cut_pos, name_candidate.find(freq_raw))
            if "-" in name_candidate[:cut_pos]:
                cut_pos = min(cut_pos, name_candidate.find("-"))

            name = name_candidate[:cut_pos].strip(" -:,")
            name = re.sub(r'\s{2,}', ' ', name).strip()

            if not name or len(name) < 2:
                continue

            # Filter out any stopped medications
            if name.upper() in stop_names:
                continue

            parsed_freq = self.freq_parser.parse_frequency(freq_raw)
            norm_timing = self.freq_parser.parse_timing(timing)
            norm_duration = self.freq_parser.parse_duration(duration)

            how_to = f"Take {dose or 'prescribed dose'} {parsed_freq['normalized'].lower()}"
            if norm_timing and norm_timing != "As directed":
                how_to += f", {norm_timing.lower()}"
            if norm_duration and norm_duration != "As advised by doctor":
                how_to += f" ({norm_duration.lower()})"

            data.medicines.append(MedicineInfo(
                name=name,
                dose=dose if dose else "As specified on prescription",
                frequency=freq_raw if freq_raw else "As advised",
                timing=norm_timing,
                duration=norm_duration,
                how_to_take_plain=how_to,
                source_text=line
            ))

    def _parse_bullet_list(self, lines: List[str], target_list: List[str], full_text: str, fallback_keywords: List[str]):
        if lines:
            for l in lines:
                cleaned = re.sub(r'^\s*[\d\.\-\*•\)]+\s*', '', l).strip()
                if cleaned and len(cleaned) > 3 and not cleaned.upper().startswith("NOTE:"):
                    target_list.append(cleaned)
        else:
            for kw in fallback_keywords:
                matches = re.findall(rf'([^.\n]*\b{re.escape(kw)}\b[^.\n]*)', full_text, re.IGNORECASE)
                for m in matches:
                    clean_m = m.strip()
                    if clean_m and clean_m not in target_list and len(clean_m) > 10:
                        target_list.append(clean_m)
                        if len(target_list) >= 4:
                            break

    def _parse_follow_ups(self, lines: List[str], full_text: str, data: CarePlanData):
        sources = list(lines)
        if not sources:
            fu_matches = re.findall(r'([^.\n]*(?:follow[- ]?up|review in|review after|next visit)[^.\n]*)', full_text, re.IGNORECASE)
            sources.extend(fu_matches)

        seen_dates = set()
        for line in sources:
            clean = re.sub(r'^\s*[\d\.\-\*•\)]+\s*', '', line).strip()
            if not clean:
                continue

            iso_date = self.date_parser.parse_date(clean)
            # Only record valid ISO YYYY-MM-DD dates as required by official H2 schema
            if not iso_date or not re.match(r'^\d{4}-\d{2}-\d{2}$', iso_date):
                continue

            if iso_date in seen_dates:
                continue
            seen_dates.add(iso_date)

            # Doctor or Department extraction
            doc_m = re.search(r'(?:with|consult|by)\s+(Dr\.?\s+[A-Za-z\s]+?)(?:\s+(?:on|at|in|for)|\s*$|,)', clean, re.IGNORECASE)
            dept_m = re.search(r'(?:in|at|-)\s+([A-Za-z\s]+(?:OPD|Clinic|Department|Hospital|Center))', clean, re.IGNORECASE)

            with_whom = ""
            if doc_m:
                with_whom = doc_m.group(1).strip()
            elif dept_m:
                with_whom = dept_m.group(1).strip()
            else:
                with_whom = "Attending Physician / OPD"

            # Purpose
            purpose = "Post-discharge clinical review and medication assessment"
            if "suture" in clean.lower():
                purpose = "Suture removal and wound check"
            elif "ecg" in clean.lower() or "echo" in clean.lower():
                purpose = "Cardiac evaluation and repeat testing"
            elif "retinopathy" in clean.lower():
                purpose = "Diabetic retinopathy evaluation"
            elif "sugar" in clean.lower() or "hba1c" in clean.lower() or "fbs" in clean.lower():
                purpose = "Glycemic control and diabetic review"
            elif "x-ray" in clean.lower() or "xray" in clean.lower():
                purpose = "Follow-up X-ray and clinical review"

            data.follow_ups.append(FollowUpInfo(
                date=iso_date,
                with_whom=with_whom,
                purpose=purpose,
                source_text=clean
            ))
