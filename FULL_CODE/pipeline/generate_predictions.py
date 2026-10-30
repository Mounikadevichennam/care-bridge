"""Generate CareBridge AI Predictions for Submission and Evaluation.

Usage:
    python FULL_CODE/pipeline/generate_predictions.py --split dev
    python FULL_CODE/pipeline/generate_predictions.py --split test
"""

import argparse
import csv
import json
import logging
import re
import sys
from pathlib import Path

# Add FULL_CODE to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.care_plan import CarePlanProcessor
from core.dataset import (
    get_data_dir,
    get_ids_file,
    get_summaries_file,
    get_abbreviation_glossary_file,
    get_drug_reference_file,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def load_ids(ids_file: Path) -> list[str]:
    ids = []
    with open(ids_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ids.append(row["summary_id"])
    return ids

def load_summaries(summaries_file: Path) -> dict[str, str]:
    mapping = {}
    with open(summaries_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                mapping[item["summary_id"]] = item["text"]
    return mapping

def generate(split: str, dry_run: bool = False, output_path: str = None, data_dir_override: str = None):
    base_dir = Path(__file__).resolve().parent.parent
    root_dir = base_dir.parent

    # Canonical organizer data directory (single source of truth)
    if data_dir_override:
        data_dir = Path(data_dir_override)
    else:
        data_dir = get_data_dir()

    ids_file = data_dir / f"{split}_ids.csv"
    summaries_file = data_dir / "summaries.jsonl"

    if not ids_file.exists():
        logger.error(f"Missing ID file: {ids_file}")
        sys.exit(1)

    target_ids = load_ids(ids_file)
    summaries = load_summaries(summaries_file)

    logger.info(f"Loaded {len(target_ids)} target IDs for split: {split}")

    processor = CarePlanProcessor(
        abbreviation_path=str(data_dir / "abbreviation_glossary.csv") if (data_dir / "abbreviation_glossary.csv").exists() else None,
        drug_reference_path=str(data_dir / "drug_reference.csv") if (data_dir / "drug_reference.csv").exists() else None
    )

    predictions = []
    for sid in target_ids:
        text = summaries.get(sid, "")
        if not text:
            logger.warning(f"Summary text missing for ID: {sid}")
            text = "No summary provided."

        res = processor.process(sid, text)

        # Standard submission schema
        pred_obj = {
            "summary_id": sid,
            "care_plan": {
                "medicines": [
                    {
                        "name": m.get("name", ""),
                        "dose": m.get("dose", ""),
                        "frequency": m.get("frequency", ""),
                        "timing": m.get("timing", ""),
                        "duration": m.get("duration", ""),
                        "how_to_take_plain": m.get("how_to_take_plain", "")
                    }
                    for m in res.get("medicines", [])
                ],
                "stop_medicines": [
                    s["name"] if isinstance(s, dict) and "name" in s else str(s)
                    for s in res.get("stop_medicines", [])
                ],
                "warning_signs": res.get("warning_signs", []),
                "diet": res.get("diet", []),
                "activity": res.get("activity", []),
                "follow_ups": [
                    {
                        "date": fu.get("date", ""),
                        "with_whom": fu.get("with_whom", ""),
                        "purpose": fu.get("purpose", "")
                    }
                    for fu in res.get("follow_ups", [])
                    if fu.get("date") and re.match(r'^\d{4}-\d{2}-\d{2}$', str(fu.get("date")))
                ]
            },
            "plain_text_en": res.get("english_plan", ""),
            "translation": {
                "language_code": "te",
                "text": res.get("telugu_plan", "")
            },
            "readability": {
                "metric": "flesch_kincaid_grade",
                "score": res.get("readability", {}).get("score", 6.0)
            }
        }
        predictions.append(pred_obj)

    # Determine destination
    if output_path:
        out_file = Path(output_path)
    elif split == "dev":
        out_file = base_dir / "evaluation" / "dev_predictions.jsonl"
    else:
        out_file = root_dir / "submission" / "H2_predictions.jsonl"

    if dry_run:
        out_file = base_dir / "evaluation" / f"{split}_predictions_dryrun.jsonl"

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        for p in predictions:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    logger.info(f"Successfully wrote {len(predictions)} predictions to: {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--data-dir", type=str, default=None, help="Path to organizer data directory")
    args = parser.parse_args()

    generate(args.split, args.dry_run, args.output, args.data_dir)

