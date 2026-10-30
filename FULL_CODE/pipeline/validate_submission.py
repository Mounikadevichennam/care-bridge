"""Validate prediction JSONL schema, IDs, and integrity.

Usage:
    python FULL_CODE/pipeline/validate_submission.py --file submission/H2_predictions.jsonl --ids data/test_ids.csv
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

# Insert parent dir into sys.path to access core.dataset
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.dataset import get_ids_file

def validate(submission_file: Path, ids_file: Path):
    print("==================================================")
    print("CAREBRIDGE AI — SUBMISSION INTEGRITY VALIDATION")
    print("==================================================")
    print(f"File to validate: {submission_file}")
    print(f"Target IDs file:  {ids_file}")

    if not submission_file.exists():
        print(f"ERROR: Submission file does not exist: {submission_file}")
        sys.exit(1)

    expected_ids = set()
    with open(ids_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            expected_ids.add(row["summary_id"])

    print(f"Expected test count: {len(expected_ids)}")

    found_ids = []
    errors = []

    with open(submission_file, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                errors.append(f"Line {idx}: Empty line detected.")
                continue

            try:
                obj = json.loads(line_str)
            except Exception as e:
                errors.append(f"Line {idx}: Invalid JSON syntax: {e}")
                continue

            sid = obj.get("summary_id")
            if not sid:
                errors.append(f"Line {idx}: Missing summary_id")
            found_ids.append(sid)

            # Schema checks
            if "care_plan" not in obj:
                errors.append(f"Line {idx}: Missing 'care_plan' object")
            else:
                cp = obj["care_plan"]
                for req in ["medicines", "stop_medicines", "warning_signs", "diet", "activity", "follow_ups"]:
                    if req not in cp:
                        errors.append(f"Line {idx}: Missing '{req}' inside care_plan")

            if "plain_text_en" not in obj or not obj["plain_text_en"].strip():
                errors.append(f"Line {idx}: Empty or missing 'plain_text_en'")

            if "translation" not in obj or obj.get("translation", {}).get("language_code") != "te":
                errors.append(f"Line {idx}: Missing valid 'translation' with language_code 'te'")

            if "readability" not in obj or "score" not in obj.get("readability", {}):
                errors.append(f"Line {idx}: Missing valid 'readability' object")

    # Duplicate check
    seen = set()
    dupes = set()
    for sid in found_ids:
        if sid in seen:
            dupes.add(sid)
        seen.add(sid)

    if dupes:
        errors.append(f"Duplicate IDs in submission: {dupes}")

    # Coverage check
    missing = expected_ids - set(found_ids)
    if missing:
        errors.append(f"Missing expected IDs from submission: {missing}")

    if errors:
        print("VALIDATION FAILED WITH ERRORS:")
        for err in errors:
            print(f"  [X] {err}")
        sys.exit(1)
    else:
        print(f"ALL CHECKS PASSED: Exactly {len(found_ids)} valid, unique predictions formatted in UTF-8 JSONL.")
        print("Submission is officially ready for upload.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to submission JSONL file")
    parser.add_argument("--ids", default=None, help="Path to test_ids.csv (defaults to organizer dataset)")
    args = parser.parse_args()

    ids_path = Path(args.ids) if args.ids else get_ids_file("test")
    validate(Path(args.file), ids_path)

