"""CareBridge AI — Hackathon Submission Packaging Utility.

Packages the submission according to the official hackathon structure:
    <teamID>_H2.zip
    ├── README.md
    ├── submission/
    │   └── H2_predictions.jsonl
    └── FULL_CODE/
        ├── app.py
        ├── requirements.txt
        ├── core/
        ├── pipeline/
        ├── templates/
        ├── static/
        ├── tests/
        └── data/

Usage:
    python tools/package_submission.py --team-id YOUR_TEAM_ID
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def package(team_id: str):
    base_dir = Path(__file__).resolve().parent.parent
    sub_file = base_dir / "submission" / "H2_predictions.jsonl"
    readme_file = base_dir / "README.md"
    full_code_dir = base_dir / "FULL_CODE"

    print("==================================================")
    print("CAREBRIDGE AI — SUBMISSION PACKAGER")
    print(f"Team ID: {team_id}")
    print("==================================================")

    # 1. Verify submission file exists
    if not sub_file.exists():
        print(f"ERROR: {sub_file} does not exist! Run generate_predictions.py first.")
        sys.exit(1)

    # 2. Run submission validation
    val_script = full_code_dir / "pipeline" / "validate_submission.py"
    # Point directly to canonical organizer dataset test IDs
    if str(full_code_dir) not in sys.path:
        sys.path.insert(0, str(full_code_dir))
    from core.dataset import get_ids_file
    ids_file = get_ids_file("test")
    print("Step 1: Running submission validation...")
    val_cmd = [sys.executable, str(val_script), "--file", str(sub_file), "--ids", str(ids_file)]
    res = subprocess.run(val_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("Validation FAILED:")
        print(res.stdout)
        print(res.stderr)
        sys.exit(1)
    print("Validation PASSED.")

    # 3. Run unit tests
    print("Step 2: Executing automated test suite...")
    test_cmd = [sys.executable, "-m", "unittest", "FULL_CODE/tests/test_carebridge.py"]
    res_test = subprocess.run(test_cmd, capture_output=True, text=True, cwd=str(base_dir))
    if res_test.returncode != 0:
        print("Unit tests FAILED:")
        print(res_test.stderr or res_test.stdout)
        sys.exit(1)
    print("All unit tests PASSED.")

    # 4. Create ZIP package
    zip_name = f"{team_id}_H2.zip"
    zip_path = base_dir / zip_name

    # Exclusions
    excluded_dirs = {".venv", "venv", "env", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", "temp", "tmp"}
    excluded_extensions = {".pyc", ".pyo", ".pyd", ".log", ".tmp"}

    print(f"Step 3: Creating submission package: {zip_name} ...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Include root README.md
        if readme_file.exists():
            zf.write(readme_file, arcname="README.md")

        # Include submission/H2_predictions.jsonl
        zf.write(sub_file, arcname="submission/H2_predictions.jsonl")

        # Include evaluate.py
        eval_script = base_dir / "evaluate.py"
        if eval_script.exists():
            zf.write(eval_script, arcname="evaluate.py")

        # Include FULL_CODE/
        for root, dirs, files in os.walk(full_code_dir):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in excluded_extensions:
                    continue
                file_full = Path(root) / file
                rel_path = file_full.relative_to(base_dir)
                zf.write(file_full, arcname=str(rel_path).replace("\\", "/"))

    print(f"SUCCESS: Package created successfully at: {zip_path}")
    print(f"Size: {zip_path.stat().st_size / 1024:.1f} KB")
    print("==================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package submission ZIP")
    parser.add_argument("--team-id", default="TEAM_PLACEHOLDER", help="Official team ID")
    args = parser.parse_args()

    package(args.team_id)

