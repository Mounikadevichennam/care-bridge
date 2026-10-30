"""Dataset resolver and validation module for CareBridge AI.

Provides the single source of truth for loading organizer data files across
all CareBridge AI modules: app, pipelines, tests, and packaging tools.
"""

import csv
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Primary organizer dataset path as specified in hackathon problem pack
DEFAULT_ORGANIZER_DATA_DIR = Path(
    r"C:\Users\Mounika\Downloads\phase-20261024125258-H2_Discharge_Summary_to_Care_Plan_v1_0\H2_Discharge_Summary_to_Care_Plan\data"
)

# Allow environment override if needed for deployment/CI
ORGANIZER_DATA_DIR = Path(os.environ.get("CAREBRIDGE_DATA_DIR", str(DEFAULT_ORGANIZER_DATA_DIR)))


def get_data_dir() -> Path:
    """Return the canonical organizer data directory."""
    if ORGANIZER_DATA_DIR.exists():
        return ORGANIZER_DATA_DIR
    # Fallback check if default path exists
    if DEFAULT_ORGANIZER_DATA_DIR.exists():
        return DEFAULT_ORGANIZER_DATA_DIR
    # Relative path fallback (e.g. if run inside organizer folder)
    local_data = Path(__file__).resolve().parent.parent.parent / "data"
    if (local_data / "summaries.jsonl").exists():
        return local_data
    raise FileNotFoundError(
        f"Original organizer data directory not found at: {ORGANIZER_DATA_DIR}. "
        "Please ensure the organizer dataset is in the verified path or set CAREBRIDGE_DATA_DIR."
    )


def get_summaries_file() -> Path:
    """Path to summaries.jsonl (2,000 discharge summaries)."""
    p = get_data_dir() / "summaries.jsonl"
    if not p.exists():
        raise FileNotFoundError(f"Missing summaries.jsonl at {p}")
    return p


def get_ids_file(split: str) -> Path:
    """Path to dev_ids.csv (200 IDs) or test_ids.csv (300 IDs)."""
    p = get_data_dir() / f"{split}_ids.csv"
    if not p.exists():
        raise FileNotFoundError(f"Missing {split}_ids.csv at {p}")
    return p


def get_dev_fact_key_file() -> Path:
    """Path to dev_fact_key.jsonl (200 gold answers for development)."""
    p = get_data_dir() / "dev_fact_key.jsonl"
    if not p.exists():
        raise FileNotFoundError(f"Missing dev_fact_key.jsonl at {p}")
    return p


def get_abbreviation_glossary_file() -> Path:
    """Path to abbreviation_glossary.csv (257 clinical abbreviations)."""
    p = get_data_dir() / "abbreviation_glossary.csv"
    if not p.exists():
        raise FileNotFoundError(f"Missing abbreviation_glossary.csv at {p}")
    return p


def get_drug_reference_file() -> Path:
    """Path to drug_reference.csv (81 Indian brand-to-generic mappings)."""
    p = get_data_dir() / "drug_reference.csv"
    if not p.exists():
        raise FileNotFoundError(f"Missing drug_reference.csv at {p}")
    return p


def get_splits_file() -> Path:
    """Path to splits.csv."""
    p = get_data_dir() / "splits.csv"
    if not p.exists():
        raise FileNotFoundError(f"Missing splits.csv at {p}")
    return p


def get_summaries_dir() -> Path:
    """Path to summaries/ directory with individual txt summaries."""
    p = get_data_dir() / "summaries"
    return p


def get_gold_examples_dir() -> Path:
    """Path to gold_examples/ directory."""
    p = get_data_dir() / "gold_examples"
    return p


def verify_dataset() -> dict[str, Any]:
    """Verify integrity and exact record counts of the organizer dataset."""
    data_dir = get_data_dir()
    report: dict[str, Any] = {
        "data_dir": str(data_dir),
        "status": "valid",
        "counts": {},
        "errors": []
    }

    # 1. Summaries count
    try:
        sum_file = get_summaries_file()
        with open(sum_file, "r", encoding="utf-8") as f:
            n_summaries = sum(1 for line in f if line.strip())
        report["counts"]["summaries"] = n_summaries
        if n_summaries != 2000:
            report["errors"].append(f"Expected 2000 summaries, found {n_summaries}")
    except Exception as e:
        report["errors"].append(f"Error checking summaries.jsonl: {e}")

    # 2. Dev IDs count
    try:
        dev_file = get_ids_file("dev")
        with open(dev_file, "r", encoding="utf-8") as f:
            dev_ids = [row["summary_id"] for row in csv.DictReader(f)]
        report["counts"]["dev_ids"] = len(dev_ids)
        if len(dev_ids) != 200:
            report["errors"].append(f"Expected 200 dev IDs, found {len(dev_ids)}")
    except Exception as e:
        report["errors"].append(f"Error checking dev_ids.csv: {e}")

    # 3. Test IDs count
    try:
        test_file = get_ids_file("test")
        with open(test_file, "r", encoding="utf-8") as f:
            test_ids = [row["summary_id"] for row in csv.DictReader(f)]
        report["counts"]["test_ids"] = len(test_ids)
        if len(test_ids) != 300:
            report["errors"].append(f"Expected 300 test IDs, found {len(test_ids)}")
    except Exception as e:
        report["errors"].append(f"Error checking test_ids.csv: {e}")

    # 4. Dev fact keys count
    try:
        fact_file = get_dev_fact_key_file()
        with open(fact_file, "r", encoding="utf-8") as f:
            n_facts = sum(1 for line in f if line.strip())
        report["counts"]["dev_fact_keys"] = n_facts
        if n_facts != 200:
            report["errors"].append(f"Expected 200 dev fact keys, found {n_facts}")
    except Exception as e:
        report["errors"].append(f"Error checking dev_fact_key.jsonl: {e}")

    # 5. Abbreviation glossary count
    try:
        abbr_file = get_abbreviation_glossary_file()
        with open(abbr_file, "r", encoding="utf-8") as f:
            abbrs = list(csv.DictReader(f))
        report["counts"]["glossary_entries"] = len(abbrs)
        if len(abbrs) != 257:
            report["errors"].append(f"Expected 257 glossary entries, found {len(abbrs)}")
    except Exception as e:
        report["errors"].append(f"Error checking abbreviation_glossary.csv: {e}")

    # 6. Drug reference count
    try:
        drug_file = get_drug_reference_file()
        with open(drug_file, "r", encoding="utf-8") as f:
            drugs = list(csv.DictReader(f))
        report["counts"]["drug_reference_entries"] = len(drugs)
        if len(drugs) != 81:
            report["errors"].append(f"Expected 81 drug reference entries, found {len(drugs)}")
    except Exception as e:
        report["errors"].append(f"Error checking drug_reference.csv: {e}")

    if report["errors"]:
        report["status"] = "invalid"

    return report


if __name__ == "__main__":
    rep = verify_dataset()
    print(json.dumps(rep, indent=2))

