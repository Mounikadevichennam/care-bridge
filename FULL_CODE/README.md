# CareBridge AI — Clearer Care After Discharge
## TalentAP Mega Hackathon 2026 | Problem Statement H2 (Healthcare)
### Clinical Discharge Summary to Patient-Understandable Care Plan

> **Core Motto:** *Faithfulness Above Fluency.*
> CareBridge AI converts complex hospital discharge summaries into grounded, simple, patient-understandable care plans in English and Telugu. It preserves prescribed medication names, exact dosages, frequencies, routes, durations, and follow-up dates without hallucination or unsupported inferences. Every patient care plan is strictly gated behind mandatory physician review and certified approval before patient distribution.

---

## 1. Verified Official Performance Benchmark

CareBridge AI was independently evaluated against the official H2 organizer evaluation schema across the complete 200 development summaries:

```text
==================================================================
 H2 Discharge Summary -> Care Plan : Official Faithfulness Scorer
==================================================================
 PRIMARY SCORE (0-1, higher is better) : 0.9346
 Summaries Scored / In Truth            : 200 / 200
------------------------------------------------------------------
 Mean Structured Before Penalty         : 0.9880
 Mean Structured After Penalty          : 0.9301
 Mean Text Faithfulness Score           : 0.9525
 Medicine Recall                        : 99.57% (0.9957)
 Dose Accuracy                          : 98.56% (0.9856)
 Frequency Accuracy                     : 97.44% (0.9744)
 Duration Accuracy                      : 96.79% (0.9679)
 Follow-up Date Recall                  : 100.00% (1.0000)
 Stop Medicine Recall                   : 100.00% (1.0000)
 English Text Coverage                  : 98.92% (0.9892)
 Telugu Translation Coverage            : 99.09% (0.9909)
------------------------------------------------------------------
 Total Dropped Medicines                : 3
 Total Altered Doses                    : 10
 Total Invented Medicines               : 0 (ZERO hallucinated medicines)
 Total Wrong Stops                      : 0 (ZERO incorrect discontinuations)
 Total Invented Follow-ups              : 0 (ZERO hallucinated dates)
 Summaries with Hard Penalties          : 13 / 200
 Translations Failing Script Check      : 0
 Readability Grade (Reported)           : 8.03 (Class 8 Patient Comprehension)
==================================================================
```

- **Zero Hallucination Tolerance:** 0 invented medicines, 0 wrong stops, and 0 invented follow-up dates.
- **Safety Guarantee:** Discontinued medicines are isolated into `stop_medicines` and never appear in active prescriptions or medication reminders.
- **Telugu Script Authenticity:** Authentic Telugu Unicode script with ~70% script density, strictly preserving drug names in Latin characters and dosages in Western digits.

---

## 2. Architecture & Clinical Workflow

```
[Hospital Discharge Summary / OCR Note]
                   │
                   ▼
       [CareBridge NLP Pipeline]
       - Grounded Entity Extraction
       - Abbreviation Glossary Resolution (257 entries)
       - Drug Reference Normalization (81 entries)
       - Frequency & Date Parsing (1-0-1, OD, BD, TDS)
       - Automated Faithfulness Validation
                   │
                   ▼
  [Database Ingestion: Status = PENDING]
   * Draft care plan strictly withheld from patient *
                   │
                   ▼
      [Doctor Clinical Portal Login]
  (Dr. Farah Siddiqui / Dr. Rajesh Patel)
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
[APPROVE CARE PLAN]    [REQUEST CHANGES]
- Identity stamped     - Mandatory clinician comments
- Cryptographic audit  - Status: CHANGES_REQUESTED
- Status: APPROVED     - Draft editable & versioned (v+1)
        │              - Status resets to PENDING
        ▼
[Patient Care Plan Released]
- Displays Attending Physician Sign-Off & License
- Interactive Daily Medication Schedule
- Smart Medication Reminders & Audio Alerts
- Direct A4 PDF Download (English & Telugu)
- Direct PNG Image Download (High-Res Graphic)
```

---

## 3. Key Capabilities & Features

### 🩺 1. Mandatory Physician Sign-Off & Role-Based Access Control
- **Clean Single-Entry Navigation:** Exactly one Doctor Portal entry in the top navigation bar.
- **Strict Server-Side Gating:** Endpoints `/api/case/<id>`, `/api/export/pdf/<id>`, and `/api/export/image/<id>` return HTTP 403 for unapproved (`PENDING` or `CHANGES_REQUESTED`) cases. Unapproved care plans are never leaked to unauthenticated users.
- **Certified Approval Stamp:** Displays the approving physician's name, license number, and UTC approval timestamp.
- **Audit Logging:** Every login, review, approval, and version update is immutably logged to SQLite `audit_log`.

### 🔔 2. Persistent Patient Notification History & Case Activity Log
- **Chronological Case Audit Trail:** Real-time, SQLite-persisted activity log tracking every milestone from submission through physician approval.
- **Persistent Across Refreshes:** Survives popup closures, page refreshes, and browser restarts.
- **Event Lifecycle Tracking:**
  - `PLAN_SUBMITTED`: Notifies patient that care plan is waiting for attending physician sign-off.
  - `PLAN_APPROVED`: Discloses certifying doctor name, license number, UTC approval timestamp, approved version, and direct link to view the unlocked care plan.
  - `CHANGES_REQUESTED`: Details specific clinical feedback and instructions for resubmission.
  - `PLAN_RESUBMITTED`: Logs submission of corrected versions (v2, v3) resetting status to pending.
- **Bilingual Support:** Complete Telugu translation for all notification headers, status badges, and action prompts.

### 🛡️ 3. Clear Status Separation (Doctor Review vs. Technical Grounding)
- **Zero Ambiguity:** Strict architectural separation between **Doctor Review Workflow** (`PENDING`, `APPROVED`, `CHANGES_REQUESTED`) and **Technical Grounding Validation** (`PASS`, `FAIL`, `NEEDS_REVIEW`).
- **Eliminated False "Needs Review" Badges:** Approved care plans visibly display `APPROVED BY Dr. [Name]`. If non-blocking technical flags exist, they are displayed as `FLAGGED — ACKNOWLEDGED BY PHYSICIAN` rather than confusing the patient with a primary `NEEDS REVIEW` banner.

### ⏰ 4. Medication Reminders & Timers
- **Approved Medicines Only:** Generated strictly from approved active prescriptions. Discontinued medications are permanently blocked from reminders.
- **Multiple Daily Slots:** Supports morning, afternoon, evening, night, and SOS dosing.
- **Clinical Safety Guard:** Flags `"Timing not specified in prescription — please confirm with doctor"` if exact hour is ungrounded.
- **Interactive Controls:** Toggle audio alarms, set custom times, mark doses as taken, and store preferences locally.

### 🌐 5. Complete English & Telugu Translation
- **Zero-Gap Bilingual Toggle:** Section headers, medication instructions, safety warnings, empty states, and caregiver notes switch dynamically between English and authentic Telugu.
- **Medical Identifier Preservation:** Preserves Latin drug names, exact dosages, and Western calendar dates for safety.

### 📥 6. Direct PDF & PNG Downloads (No Print Dialog)
- **Direct Binary File Downloads:** Uses `Content-Disposition: attachment` headers to trigger direct browser file saves. Never launches `window.print()` or browser print dialogs.
- **Telugu Font Rendering:** Employs Nirmala / Unicode fonts for crisp Indic typography on Windows.

---

## 4. Setup & Running the Application Locally

### Prerequisites
- Python 3.10+ (Verified on Python 3.13 on Windows)
- Modern web browser (Chrome, Edge, Firefox)

### Step 1: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Environment Configuration (Optional)
Copy `.env.example` to `.env` if custom paths are needed:
```powershell
Copy-Item .env.example .env
```

### Step 3: Start the Web Application
```powershell
cd FULL_CODE
python app.py
```

Open your browser at:
👉 **`http://127.0.0.1:5000`**

---

## 5. Safe Demo Clinician Credentials

For testing and demonstration, pre-seeded accounts are initialized with PBKDF2/SHA-256 password hashing:

| Doctor Name | Department | Email ID | Password |
| :--- | :--- | :--- | :--- |
| **Dr. Farah Siddiqui, MD** | General Medicine Unit II | `dr.siddiqui@chandrapuri.org` | `DoctorCare2026!` |
| **Dr. Rajesh Patel, MBBS, MD** | Cardiology & Critical Care | `dr.patel@chandrapuri.org` | `DoctorCare2026!` |

---

## 6. Running the Test Suites

Execute the comprehensive 87-test automated suite (including patient notifications, status separation, doctor portal, and reminders):

```powershell
python -m unittest discover -s FULL_CODE/tests -p "test_*.py"
```

To run only the patient notification history scenarios:
```powershell
python -m unittest FULL_CODE/tests/test_patient_notifications.py
```

To run the official hackathon evaluator:
```powershell
python evaluate.py --predictions FULL_CODE/evaluation/dev_predictions.jsonl
```

To validate the test submission file:
```powershell
python evaluate.py --validate-submission submission/H2_predictions.jsonl
```

---

## 7. Submission Package Integrity
- **Submission File:** `submission/H2_predictions.jsonl` (300 test predictions, 100% schema compliant).
- **Core Engine:** Located in `FULL_CODE/` (pure Python, Flask, SQLite, ReportLab, Pillow).
- **Faithfulness:** Verified benchmark score of **0.9346** with **zero invented medicines**.
