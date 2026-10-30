"""Medical abbreviation detection and expansion module.

Provides the :class:`AbbreviationResolver` which loads a CSV glossary of
medical abbreviations and can detect, look-up, and expand them inside
free-text clinical narratives.
"""

import csv
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AbbreviationResolver:
    """Resolves medical abbreviations using the supplied glossary.

    Parameters
    ----------
    glossary_path : str, optional
        Path to a CSV file with columns ``abbreviation`` and ``full_form``.
        If provided the glossary is loaded immediately.
    """

    def __init__(self, glossary_path: Optional[str] = None) -> None:
        self._glossary: dict[str, str] = {}
        self._plain_language: dict[str, str] = {}
        self._category: dict[str, str] = {}
        self._details: dict[str, dict[str, str]] = {}
        # Common English words that should *never* be treated as abbreviations
        # even if they happen to appear in uppercase in a document.
        self._common_words: set[str] = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "or", "and", "not", "no", "but", "if", "so", "as", "it",
            "he", "she", "we", "they", "me", "him", "her", "us", "them",
            "my", "his", "its", "our", "your", "their", "this", "that",
            "all", "each", "every", "both", "few", "more", "most", "other",
            "some", "such", "than", "too", "very", "just", "also", "now",
            "up", "out", "day", "days", "week", "weeks", "month", "months",
            "year", "years", "time", "date", "after", "before", "during",
            "then", "there", "here", "only", "well", "back", "see",
            "new", "old", "good", "bad", "high", "low", "long", "short",
            "full", "left", "right", "one", "two", "three", "four", "five",
            "six", "seven", "eight", "nine", "ten", "per", "via", "yes",
            "get", "got", "set", "put", "let", "go", "came", "come",
            "take", "took", "taken", "give", "gave", "given", "make",
            "made", "say", "said", "told", "tell", "know", "knew",
            "about", "above", "below", "between", "under", "over",
            "through", "into", "again", "once", "twice", "still",
            "own", "same", "any", "much", "many", "off", "down",
            "keep", "while", "until", "without", "along", "within",
            "since", "like", "near", "need", "use", "used",
        }

        # Inline fallback glossary – the most common medical abbreviations
        # seen in Indian discharge summaries.
        self._builtin_glossary: dict[str, str] = {
            "OD": "once daily",
            "BD": "twice daily",
            "BID": "twice daily",
            "TDS": "three times a day",
            "TID": "three times a day",
            "QID": "four times a day",
            "HS": "at bedtime",
            "SOS": "as needed",
            "PRN": "as needed",
            "AC": "before food",
            "PC": "after food",
            "PO": "by mouth",
            "IV": "intravenous",
            "IM": "intramuscular",
            "SC": "subcutaneous",
            "S/C": "subcutaneous",
            "INH": "inhalation",
            "NEB": "nebulisation",
            "STAT": "immediately",
            "Tab": "Tablet",
            "Cap": "Capsule",
            "Syr": "Syrup",
            "Inj": "Injection",
            "Oint": "Ointment",
            "MDI": "Metered-Dose Inhaler",
            "DPI": "Dry Powder Inhaler",
            "IU": "International Units",
            "mcg": "micrograms",
            "mg": "milligrams",
            "mL": "millilitres",
            "g": "grams",
            "BP": "blood pressure",
            "HR": "heart rate",
            "RR": "respiratory rate",
            "SpO2": "oxygen saturation",
            "T2DM": "Type 2 Diabetes Mellitus",
            "DM": "Diabetes Mellitus",
            "HTN": "Hypertension",
            "CAD": "Coronary Artery Disease",
            "CABG": "Coronary Artery Bypass Graft",
            "MI": "Myocardial Infarction",
            "CHF": "Congestive Heart Failure",
            "CCF": "Congestive Cardiac Failure",
            "AF": "Atrial Fibrillation",
            "DVT": "Deep Vein Thrombosis",
            "PE": "Pulmonary Embolism",
            "COPD": "Chronic Obstructive Pulmonary Disease",
            "CKD": "Chronic Kidney Disease",
            "AKI": "Acute Kidney Injury",
            "UTI": "Urinary Tract Infection",
            "LRTI": "Lower Respiratory Tract Infection",
            "URTI": "Upper Respiratory Tract Infection",
            "GERD": "Gastroesophageal Reflux Disease",
            "GI": "Gastrointestinal",
            "CVA": "Cerebrovascular Accident",
            "TIA": "Transient Ischaemic Attack",
            "IHD": "Ischaemic Heart Disease",
            "ECG": "Electrocardiogram",
            "ECHO": "Echocardiography",
            "CT": "Computed Tomography",
            "MRI": "Magnetic Resonance Imaging",
            "USG": "Ultrasonography",
            "CBC": "Complete Blood Count",
            "LFT": "Liver Function Test",
            "RFT": "Renal Function Test",
            "TFT": "Thyroid Function Test",
            "HbA1c": "Glycated Haemoglobin",
            "FBS": "Fasting Blood Sugar",
            "PPBS": "Post-Prandial Blood Sugar",
            "GRBS": "Glucometer Random Blood Sugar",
            "RBS": "Random Blood Sugar",
            "ICU": "Intensive Care Unit",
            "OPD": "Outpatient Department",
            "ER": "Emergency Room",
            "A&E": "Accident & Emergency",
            "DOA": "Date of Admission",
            "DOD": "Date of Discharge",
            "D/C": "Discharge",
            "Rx": "Prescription",
            "Dx": "Diagnosis",
            "Hx": "History",
            "Sx": "Symptoms",
            "Tx": "Treatment",
            "Fx": "Fracture",
            "SOB": "Shortness of Breath",
            "CP": "Chest Pain",
            "LOC": "Loss of Consciousness",
            "GCS": "Glasgow Coma Scale",
            "NKA": "No Known Allergies",
            "NKDA": "No Known Drug Allergies",
            "WNL": "Within Normal Limits",
            "NAD": "No Active Distress",
            "OHA": "Oral Hypoglycaemic Agent",
            "NSAID": "Non-Steroidal Anti-Inflammatory Drug",
            "PPI": "Proton Pump Inhibitor",
            "ACE": "Angiotensin-Converting Enzyme",
            "ARB": "Angiotensin Receptor Blocker",
            "CCB": "Calcium Channel Blocker",
            "BB": "Beta Blocker",
            "INR": "International Normalised Ratio",
            "PT": "Prothrombin Time",
            "APTT": "Activated Partial Thromboplastin Time",
            "ABG": "Arterial Blood Gas",
            "BNP": "Brain Natriuretic Peptide",
            "CRP": "C-Reactive Protein",
            "ESR": "Erythrocyte Sedimentation Rate",
            "EMG": "Electromyography",
            "EEG": "Electroencephalogram",
            "LVEF": "Left Ventricular Ejection Fraction",
            "EF": "Ejection Fraction",
            "PTCA": "Percutaneous Transluminal Coronary Angioplasty",
            "PCI": "Percutaneous Coronary Intervention",
            "LSCS": "Lower Segment Caesarean Section",
            "ICH": "Intracerebral Haemorrhage",
            "SAH": "Subarachnoid Haemorrhage",
            "ACS": "Acute Coronary Syndrome",
            "STEMI": "ST-Elevation Myocardial Infarction",
            "NSTEMI": "Non-ST-Elevation Myocardial Infarction",
        }
        # Merge built-in glossary (lowercase keys)
        for abbr, full in self._builtin_glossary.items():
            self._glossary[abbr.upper()] = full

        if glossary_path:
            self.load_glossary(glossary_path)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_glossary(self, path: str) -> None:
        """Load abbreviation → full-form mappings from a CSV file.

        Expected columns (case-insensitive header matching):
        ``abbreviation`` and ``full_form``.  Extra columns are ignored.

        Parameters
        ----------
        path : str
            Filesystem path to the CSV glossary.
        """
        file_path = Path(path)
        if not file_path.exists():
            logger.warning("Glossary file not found: %s – using built-in glossary only.", path)
            return

        rows_loaded = 0
        for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                with open(file_path, encoding=encoding, newline="") as fh:
                    reader = csv.DictReader(fh)
                    if reader.fieldnames is None:
                        logger.warning("Empty CSV file: %s", path)
                        return

                    # Normalise header names
                    col_map: dict[str, str] = {}
                    for fn in reader.fieldnames:
                        lower = fn.strip().lower().replace(" ", "_")
                        col_map[lower] = fn

                    abbr_col = col_map.get("abbreviation") or col_map.get("abbr") or col_map.get("abbrev")
                    full_col = (
                        col_map.get("expansion")
                        or col_map.get("full_form")
                        or col_map.get("fullform")
                        or col_map.get("meaning")
                        or col_map.get("definition")
                    )
                    plain_col = col_map.get("plain_language") or col_map.get("plain") or col_map.get("plain_language_expansion")
                    cat_col = col_map.get("category") or col_map.get("type")

                    if not abbr_col or not full_col:
                        logger.warning(
                            "CSV %s lacks expected columns. Found: %s",
                            path, reader.fieldnames,
                        )
                        return

                    for row in reader:
                        abbr = (row.get(abbr_col) or "").strip()
                        full = (row.get(full_col) or "").strip()
                        plain = (row.get(plain_col) or "").strip() if plain_col else ""
                        cat = (row.get(cat_col) or "").strip() if cat_col else ""
                        if abbr and full:
                            key = abbr.upper()
                            self._glossary[key] = full
                            if plain:
                                self._plain_language[key] = plain
                            if cat:
                                self._category[key] = cat
                            self._details[key] = {
                                "expansion": full,
                                "plain_language": plain,
                                "category": cat
                            }
                            rows_loaded += 1

                logger.info("Loaded %d abbreviation mappings from %s", rows_loaded, path)
                return  # success – stop trying encodings
            except UnicodeDecodeError:
                continue
            except Exception:
                logger.exception("Error reading glossary %s", path)
                return

        logger.warning("Could not decode glossary file %s with any supported encoding.", path)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def lookup(self, abbreviation: str) -> Optional[str]:
        """Return the expanded form for *abbreviation*, or ``None``.

        Lookup is case-insensitive.
        """
        if not abbreviation:
            return None
        return self._glossary.get(abbreviation.upper())

    def get_plain_language(self, abbreviation: str) -> Optional[str]:
        """Return the plain-language explanation for *abbreviation*, or ``None``."""
        if not abbreviation:
            return None
        return self._plain_language.get(abbreviation.upper())

    def get_category(self, abbreviation: str) -> Optional[str]:
        """Return the category for *abbreviation*, or ``None``."""
        if not abbreviation:
            return None
        return self._category.get(abbreviation.upper())

    def get_details(self, abbreviation: str) -> Optional[dict[str, str]]:
        """Return detailed info dict for *abbreviation*, or ``None``."""
        if not abbreviation:
            return None
        return self._details.get(abbreviation.upper())

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect_abbreviations(self, text: str) -> list[dict]:
        """Detect all potential abbreviations in *text*.

        Returns a list of dicts, each containing:
        - ``abbreviation`` – the token as found in text
        - ``expansion`` – the known expansion or ``None``
        - ``position`` – character offset in *text*
        - ``is_known`` – ``True`` if expansion is available

        Common English words are excluded even if they appear in
        uppercase.
        """
        results: list[dict] = []
        seen: set[str] = set()

        # Pattern: uppercase tokens of 2-10 chars, or mixed-case tokens
        # that match the glossary (e.g. HbA1c, SpO2).
        token_pattern = re.compile(
            r"\b([A-Z][A-Za-z0-9/]{0,9})\b"
            r"|"
            r"\b([A-Za-z]{1,3}(?:/[A-Za-z]{1,3}))\b"
        )

        for match in token_pattern.finditer(text):
            token = match.group(0)
            if token.lower() in self._common_words:
                continue
            # Skip pure numbers
            if token.isdigit():
                continue
            # Skip single lowercase letters
            if len(token) == 1 and token.islower():
                continue
            # Skip tokens that look like regular mixed-case words (e.g. "Patient")
            if len(token) > 3 and token[0].isupper() and token[1:].islower():
                # Only treat as abbreviation if it's explicitly in glossary
                if token.upper() not in self._glossary:
                    continue

            key = token.upper()
            expansion = self._glossary.get(key)
            is_known = expansion is not None

            # For short all-caps tokens not in glossary, flag as unknown
            # but only if they really look like abbreviations (2+ uppercase chars)
            if not is_known and not (len(token) >= 2 and token.isupper()):
                continue

            dup_key = f"{key}:{match.start()}"
            if dup_key in seen:
                continue
            seen.add(dup_key)

            results.append({
                "abbreviation": token,
                "expansion": expansion,
                "position": match.start(),
                "is_known": is_known,
            })

        return results

    # ------------------------------------------------------------------
    # Expansion
    # ------------------------------------------------------------------

    def expand_in_text(self, text: str) -> str:
        """Replace known abbreviations with ``abbreviation (full form)``
        on the **first** occurrence only.

        Common English words are never expanded.  Unknown abbreviations
        are left as-is.
        """
        detections = self.detect_abbreviations(text)
        if not detections:
            return text

        # Only expand known abbreviations; first occurrence per abbreviation
        expanded_set: set[str] = set()
        # Sort by position descending so replacements don't shift offsets
        detections_sorted = sorted(
            [d for d in detections if d["is_known"]],
            key=lambda d: d["position"],
            reverse=True,
        )

        result = text
        for det in detections_sorted:
            abbr = det["abbreviation"]
            key = abbr.upper()
            if key in expanded_set:
                continue
            expanded_set.add(key)

            pos = det["position"]
            end = pos + len(abbr)
            replacement = f"{abbr} ({det['expansion']})"
            result = result[:pos] + replacement + result[end:]

        return result

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @property
    def glossary_size(self) -> int:
        """Number of abbreviation mappings loaded."""
        return len(self._glossary)

    def add_mapping(self, abbreviation: str, full_form: str) -> None:
        """Add or update a single abbreviation mapping at runtime."""
        self._glossary[abbreviation.upper()] = full_form

    def __repr__(self) -> str:
        return f"<AbbreviationResolver glossary_size={self.glossary_size}>"
