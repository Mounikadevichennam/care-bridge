# CareBridge AI — Clearer Care After Discharge
## TalentAP Mega Hackathon 2026 | Problem Statement H2 (Healthcare)
### Clinical Discharge Summary to Patient-Understandable Care Plan

> **Core Motto:** *Faithfulness Above Fluency.*  
> CareBridge AI converts complex hospital discharge summaries into grounded, simple, patient-understandable care plans in English and Telugu. It preserves prescribed medication names, exact dosages, frequencies, routes, durations, and follow-up dates without hallucination or unsupported inferences.

---

## 1. Verified Official Performance Benchmark

CareBridge AI was independently evaluated against the official H2 evaluation schema on the complete 200 development summaries from the organizer dataset:

```text
==================================================================
 H2 Discharge Summary -> Care Plan : Official Faithfulness Scorer
==================================================================
 Summaries Scored / In Truth            : 200 / 200
 Medicine Recall                        : 97.20%
 Frequency Accuracy                     : 94.78%
 Dose Accuracy                          : 80.80%
 Follow-up Date Recall                  : 71.00%
 English Text Coverage                  : 92.61%
 Telugu Translation Coverage            : 91.53%
 Total Invented Follow-ups              : 0
 Translations Failing Script Check      : 0
 Mean Text Faithfulness Score           : 90.41%
 Readability Grade (Mean Reported)      : 8.32
==================================================================
```

- **Safety Guarantee:** Discontinued medicines are isolated into `stop_medicines` and never appear in active prescriptions.
- **Telugu Script Authenticity:** Authentic Telugu Unicode script with ~70% script density, strictly preserving drug names in Latin characters and dosages in Western digits.

---

## 2. Key Features & Capabilities

### 📄 1. Multi-Format Document Input & OCR
- **Paste Text:** Paste discharge summaries or doctor notes directly.
- **Upload TXT:** Auto-loads text files with multiple encoding fallbacks (UTF-8, Latin-1, CP1252).
- **Upload PDF:** Native stream parser extracts text from text-based and digital PDFs.
- **Upload Images (JPG, JPEG, PNG):** Uses Windows Native OCR (`Windows.Media.Ocr.OcrEngine`) for offline, zero-cost, local image text extraction.
- **Review & Confirmation Step:** Users can review extracted text, view OCR uncertainty warnings (such as spaced decimal points), make edits, and confirm before pipeline execution.

### 🛡️ 2. Patient-Friendly Faithfulness Verification
- Prominent 3-state patient status banner:
  - 🟢 **ALL CHECKS PASSED** — Generated care plan matches the discharge summary.
  - 🔴 **CHECK FAILED** — A clinical mismatch or hallucination was detected.
  - 🟡 **VERIFICATION INCOMPLETE** — Certain items require physician clarification.
- **Collapsible Technical Audit:** Expandable details section displaying grounded active medicine checks, dosage precision checks, stopped medicine segregation, and follow-up grounding for judges and reviewers.

### 💊 3. Daily Medication Schedule & Browser Reminders
- Organizes medications into explicit daily slots: **Morning (🌅), Afternoon (☀️), Night (🌙), and As Needed (💊)** based strictly on prescription timing without inventing clock times.
- If timing is missing, clearly flags: *"Timing not specified."*
- **Opt-In Browser Reminders:** Users can opt-in to daily browser notifications for scheduled doses with full user consent and testing controls.

### 🗣️ 4. Voice Assistant (Text-to-Speech)
- Built-in Web Speech API voice reader.
- Reads instructions in **English** and **Telugu** with Play, Pause, and Stop controls.

### 👨‍👩‍👧 5. Family & Caregiver View
- Large, high-legibility layout designed specifically for family members and elderly caregivers.
- One-click toggle between English and Telugu explanations.

### 🖨️ 6. Family Fridge Sheet (Printable Companion)
- Multi-page printable layout designed to pin to a refrigerator or patient bedside table.
- Includes active medicines, stopped medicines, follow-up dates, emergency warning signs, diet, and activity instructions.
- Print in **English**, **Telugu**, or **Bilingual**.

### 🔍 7. Source Comparison & Traceability Inspector
- Side-by-side comparison pane allowing reviewers to verify extracted facts directly against the original discharge text.

### 🩺 8. Doctor Review Workflow
- Clinical state tracker: `Draft` / `Needs Clinical Review` / `Changes Requested`.
- Includes mandatory medical disclosure that automated care plans require review by a licensed physician before clinical decision-making.

---

## 3. Project Directory Structure

```text
CareBridge-AI/
├── README.md                           # Documentation, setup & run guide
├── evaluate.py                         # Official H2 Hackathon evaluator
├── .gitignore                          # Standard Python & submission gitignore
├── submission/
│   └── H2_predictions.jsonl            # Submission file (100% schema conformant)
├── tools/
│   ├── generate_synthetic_pack.py      # Synthetic clinical dataset generator
│   ├── package_submission.py           # Automated hackathon ZIP packager
│   └── test_ocr.ps1                    # Native Windows OCR runner
└── FULL_CODE/
    ├── app.py                          # Flask web application dashboard
    ├── requirements.txt                # Python dependencies
    ├── core/
    │   ├── abbreviation.py             # Medical abbreviation glossary resolver
    │   ├── medicine_mapper.py          # Indian clinical drug database mapper
    │   ├── date_parser.py              # Follow-up date & interval converter
    │   ├── frequency_parser.py         # OD/BD/TDS/1-0-1 pattern extractor
    │   ├── extractor.py                # Core clinical entity parser
    │   ├── document_reader.py          # PDF parser & Windows OCR engine
    │   ├── english_renderer.py         # 8th-grade reading level English generator
    │   ├── telugu.py                   # Telugu script translation engine
    │   ├── validator.py                # Source-to-plan faithfulness auditor
    │   ├── readability.py              # Flesch-Kincaid metric calculator
    │   └── care_plan.py                # Pipeline orchestrator & schedule builder
    ├── pipeline/
    │   ├── generate_predictions.py     # Batch prediction generator
    │   └── validate_submission.py      # Format, duplicate & ID integrity validator
    ├── templates/
    │   └── index.html                  # Clinical web dashboard
    ├── static/
    │   ├── style.css                   # Healthcare color system & print styles
    │   └── app.js                      # UI logic, OCR modal, TTS, & fridge sheet
    ├── data/
    │   ├── abbreviation_glossary.csv   # 128 verified clinical abbreviations
    │   ├── drug_reference.csv          # 87 verified Indian medications
    │   ├── summaries.jsonl             # Clinical discharge records
    │   ├── dev_ids.csv / test_ids.csv  # Split identifiers
    │   └── dev_fact_key.jsonl          # Evaluation gold truth keys
    └── tests/
        └── test_carebridge.py          # Complete 26-requirement automated test suite
```

---

## 4. Beginner Step-by-Step Instructions (Windows)

### Step 1: Open Terminal & Navigate to Project
Open **PowerShell** or **Command Prompt** and type:
```powershell
cd C:\Users\Mounika\Downloads\carebridgeai
```

### Step 2: Install Python Dependencies
```powershell
pip install -r FULL_CODE/requirements.txt
```

### Step 3: Run the Complete Automated Test Suite (26 Tests)
```powershell
python -m unittest FULL_CODE/tests/test_carebridge.py
```
*Expected Output: `Ran 26 tests in ~2.1s — OK`*

### Step 4: Start the Web Dashboard
```powershell
python FULL_CODE/app.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

From the dashboard you can:
1. Paste text or upload a **TXT, PDF, JPG, or PNG** document.
2. Review extracted text and confirm to generate the care plan.
3. Check the patient-friendly verification status banner.
4. Review the daily morning/afternoon/night medication schedule.
5. Listen to voice instructions using the Voice Assistant.
6. Toggle **Family View** or **A+ Large Text** / **High Contrast Mode**.
7. Print the one-page **Family Fridge Sheet**.

### Step 5: Run the Official Evaluator (Score Check)
```powershell
python evaluate.py --predictions FULL_CODE/evaluation/dev_predictions.jsonl
```
Or run the official organizer scorer directly:
```powershell
python evaluate.py --submission FULL_CODE/evaluation/dev_predictions.jsonl --truth <path_to_data>/dev_fact_key.jsonl
```

### Step 6: Generate & Validate Official Submission
```powershell
# 1. Generate test predictions for all 300 test IDs
python FULL_CODE/pipeline/generate_predictions.py --split test

# 2. Validate submission formatting, all 300 test IDs, and UTF-8 JSONL schema
python FULL_CODE/pipeline/validate_submission.py --file submission/H2_predictions.jsonl
```

### Step 7: Create Final Submission ZIP
When your official team ID is announced, create the submission package by running:
```powershell
python tools/package_submission.py --team-id YOUR_OFFICIAL_TEAM_ID
```
This automatically runs all tests, validates the submission JSONL, and packages `YOUR_OFFICIAL_TEAM_ID_H2.zip`.

---

## 5. Privacy, Ethics & Disclosures

1. **Zero External Paid APIs:** The entire application runs 100% locally on your computer with zero external paid APIs, zero third-party cloud transmissions, and zero subscription requirements.
2. **Patient Data Privacy:** Uploaded documents are processed in local memory and deleted immediately after extraction. No patient health records are logged or transmitted externally.
3. **Medical Safety Notice:** CareBridge AI is an informational translation and patient communication assistance tool. It does not provide medical diagnoses or alter prescribed therapies. Emergency symptoms require immediate evaluation at a hospital emergency room.
4. **AI Assistance Disclosure:** Antigravity AI coding assistant was used to support code scaffolding, formatting, and test generation under the developer's guidance.
