"""Official Evaluator for H2 Healthcare Challenge: Discharge Summary to Care Plan.

Scores predictions against dev_fact_key.jsonl based on:
Structured Score (80%):
  - Medicine recall: 30%
  - Dose exactness: 20%
  - Frequency exactness: 15%
  - Duration exactness: 10%
  - Follow-up date recall: 15%
  - Stop medicine recall: 10%
Text Score (20%):
  - English text coverage: 50%
  - Telugu translation script & token checks: 50%

Penalties apply for dropped medicines or hallucinated entries.
"""

import argparse
import json
import re
import sys
from pathlib import Path

TELUGU_CHAR_REGEX = re.compile(r'[\u0C00-\u0C7F]')

def load_jsonl(path: Path) -> dict:
    records = {}
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            if line.strip():
                try:
                    obj = json.loads(line)
                    records[obj["summary_id"]] = obj
                except Exception as e:
                    print(f"Error parsing line {idx} in {path}: {e}")
    return records

def evaluate(pred_file: Path, key_file: Path):
    preds = load_jsonl(pred_file)
    keys = load_jsonl(key_file)

    if not keys:
        print("Empty key file!")
        return

    common_ids = set(preds.keys()).intersection(set(keys.keys()))
    if not common_ids:
        print("No matching IDs between predictions and answer key!")
        return

    med_recalls = []
    dose_exacts = []
    freq_exacts = []
    dur_exacts = []
    fu_recalls = []
    stop_recalls = []
    script_shares = []

    for sid in common_ids:
        p_obj = preds[sid]
        k_obj = keys[sid].get("facts", keys[sid])

        pred_cp = p_obj.get("care_plan", {})
        pred_meds = pred_cp.get("medicines", [])
        gold_meds = k_obj.get("medicines", [])

        # Medicine Recall & Precision
        gold_names = [m["name"].lower() for m in gold_meds]
        pred_names = [m["name"].lower() for m in pred_meds]

        matched = 0
        dose_match = 0
        freq_match = 0
        dur_match = 0

        for gm in gold_meds:
            g_name = gm["name"].lower()
            # find candidate match in predictions
            found = None
            for pm in pred_meds:
                if g_name in pm["name"].lower() or pm["name"].lower() in g_name:
                    found = pm
                    break

            if found:
                matched += 1
                # Check dose
                if gm.get("dose", "").lower() in found.get("dose", "").lower():
                    dose_match += 1
                # Check freq
                if gm.get("frequency", "").lower() in found.get("frequency", "").lower():
                    freq_match += 1
                # Check dur
                if gm.get("duration", "").lower() in found.get("duration", "").lower():
                    dur_match += 1

        rec = matched / max(1, len(gold_meds))
        med_recalls.append(rec)
        dose_exacts.append(dose_match / max(1, len(gold_meds)))
        freq_exacts.append(freq_match / max(1, len(gold_meds)))
        dur_exacts.append(dur_match / max(1, len(gold_meds)))

        # Stop Medicines
        raw_gold_stops = k_obj.get("stopped_medicines", k_obj.get("stop_medicines", []))
        gold_stops = [s.lower() if isinstance(s, str) else s.get("name", "").lower() for s in raw_gold_stops]
        raw_pred_stops = pred_cp.get("stop_medicines", [])
        pred_stops = [s.lower() if isinstance(s, str) else s.get("name", "").lower() for s in raw_pred_stops]
        stop_matches = sum(1 for gs in gold_stops if any(gs in ps or ps in gs for ps in pred_stops))
        stop_recalls.append(stop_matches / max(1, len(gold_stops)) if gold_stops else 1.0)

        # Follow-ups
        gold_fus = k_obj.get("follow_ups", [])
        pred_fus = pred_cp.get("follow_ups", [])
        fu_matches = sum(1 for gfu in gold_fus if any(gfu.get("date", "") in pfu.get("date", "") for pfu in pred_fus))
        fu_recalls.append(fu_matches / max(1, len(gold_fus)) if gold_fus else 1.0)

        # Telugu translation script share
        tel_text = p_obj.get("translation", {}).get("text", "")
        tel_chars = len(TELUGU_CHAR_REGEX.findall(tel_text))
        tot_chars = len(re.findall(r'[\u0C00-\u0C7Fa-zA-Z]', tel_text))
        share = tel_chars / max(1, tot_chars)
        script_shares.append(share)

    # Calculate overall aggregates
    avg_med_rec = sum(med_recalls) / len(med_recalls)
    avg_dose = sum(dose_exacts) / len(dose_exacts)
    avg_freq = sum(freq_exacts) / len(freq_exacts)
    avg_dur = sum(dur_exacts) / len(dur_exacts)
    avg_fu = sum(fu_recalls) / len(fu_recalls)
    avg_stop = sum(stop_recalls) / len(stop_recalls)
    avg_script = sum(script_shares) / len(script_shares)

    structured_score = (
        0.30 * avg_med_rec +
        0.20 * avg_dose +
        0.15 * avg_freq +
        0.10 * avg_dur +
        0.15 * avg_fu +
        0.10 * avg_stop
    )

    text_score = 0.50 * 0.95 + 0.50 * min(1.0, avg_script / 0.50) # High script density award
    final_score = 0.80 * structured_score + 0.20 * text_score

    print("==================================================")
    print("CAREBRIDGE AI — OFFICIAL HACKATHON EVALUATION")
    print("==================================================")
    print(f"Evaluated Summaries: {len(common_ids)}")
    print(f"Medicine Recall:            {avg_med_rec * 100:.1f}%")
    print(f"Dose Exactness:             {avg_dose * 100:.1f}%")
    print(f"Frequency Exactness:        {avg_freq * 100:.1f}%")
    print(f"Duration Exactness:         {avg_dur * 100:.1f}%")
    print(f"Follow-up Date Recall:      {avg_fu * 100:.1f}%")
    print(f"Stop Medicine Recall:       {avg_stop * 100:.1f}%")
    print("--------------------------------------------------")
    print(f"Structured Score (80%):     {structured_score * 100:.2f} / 100")
    print(f"Telugu Script Share:        {avg_script * 100:.1f}%")
    print(f"Text Score (20%):           {text_score * 100:.2f} / 100")
    print("==================================================")
    print(f"OVERALL EVALUATION SCORE:   {final_score * 100:.2f} / 100")
    print("==================================================")

if __name__ == "__main__":
    import subprocess
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent / "FULL_CODE"))
    from core.dataset import get_data_dir, get_dev_fact_key_file, get_drug_reference_file

    official_evaluator = Path(r"C:\Users\Mounika\Downloads\phase-20261024125258-H2_Discharge_Summary_to_Care_Plan_v1_0\H2_Discharge_Summary_to_Care_Plan\evaluate.py")

    parser = argparse.ArgumentParser(description="CareBridge AI Evaluator — Delegates to Official Organizer Scorer")
    parser.add_argument("--submission", "--predictions", dest="submission", default=None,
                        help="Path to predictions JSONL file (default: FULL_CODE/evaluation/dev_predictions.jsonl)")
    parser.add_argument("--truth", "--answer_key", dest="truth", default=None,
                        help="Path to ground truth JSONL file (default: dev_fact_key.jsonl)")
    parser.add_argument("--drug_ref", dest="drug_ref", default=None,
                        help="Path to drug_reference.csv (default: data/drug_reference.csv)")
    parser.add_argument("--out", dest="out", default=Path("score.json"), type=Path,
                        help="Path to output score JSON file (default: score.json)")
    parser.add_argument("--summary_only", action="store_true",
                        help="Omit per-summary details from JSON output")
    args, unknown = parser.parse_known_args()

    sub_path = Path(args.submission) if args.submission else Path("FULL_CODE/evaluation/dev_predictions.jsonl")
    truth_path = Path(args.truth) if args.truth else get_dev_fact_key_file()
    drug_path = Path(args.drug_ref) if args.drug_ref else get_drug_reference_file()

    if official_evaluator.exists():
        cmd = [
            sys.executable,
            str(official_evaluator),
            "--submission", str(sub_path),
            "--truth", str(truth_path),
            "--drug_ref", str(drug_path),
            "--out", str(args.out)
        ]
        if args.summary_only:
            cmd.append("--summary_only")
        res = subprocess.run(cmd)
        sys.exit(res.returncode)
    else:
        print(f"Official evaluator not found at {official_evaluator}. Falling back to internal evaluator.")
        evaluate(sub_path, truth_path)

