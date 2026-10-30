"""Generates synthetic H2 hackathon dataset files for local development and benchmarking."""

import os
import json
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "FULL_CODE" / "data"
ROOT_DATA_DIR = BASE_DIR / "data"
SUMMARIES_DIR = DATA_DIR / "summaries"

DATA_DIR.mkdir(parents=True, exist_ok=True)
ROOT_DATA_DIR.mkdir(parents=True, exist_ok=True)
SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)

# 20 diverse realistic clinical discharge summaries
SUMMARIES_DATA = [
    {
        "id": "H2S-00000001",
        "split": "dev",
        "text": """CITY GENERAL HOSPITAL
Department of Internal Medicine
DISCHARGE SUMMARY
Patient Name: Ramesh Kumar Reddy | Age/Sex: 58/M | MRD: MRD-2024-004521
Admission Date: 15-Oct-2024 | Discharge Date: 21-Oct-2024
Consultant: Dr. Srinivas Rao, MD

DIAGNOSIS:
1. Type 2 Diabetes Mellitus - uncontrolled
2. Hypertension - Stage 2
3. Dyslipidemia

DISCHARGE MEDICATIONS:
1. Tab Glycomet SR 1000mg - 1 tab BD after food
2. Tab Amaryl 2mg - 1 tab OD before breakfast
3. Tab Jardiance 25mg - 1 tab OD in the morning
4. Tab Telma 40mg - 1 tab OD in the morning
5. Tab Amlong 5mg - 1 tab OD at bedtime
6. Tab Atorva 20mg - 1 tab OD at bedtime
7. Tab Ecosprin 75mg - 1 tab OD after lunch
8. Cap Pregabalin 75mg - 1 cap BD for 4 weeks
9. Tab Methylcobalamin 1500mcg - 1 tab OD for 8 weeks
10. Tab Pan 40mg - 1 tab OD before breakfast for 2 weeks

STOP MEDICINES:
- Stop Tab Glibenclamide 5mg (replaced with current regimen)
- Stop Insulin sliding scale (inpatient use only)

FOLLOW-UP:
1. Review with Dr. Srinivas Rao on 2024-11-04 at OPD
2. Ophthalmology review with Dr. Kavitha on 2024-11-11

WARNING SIGNS:
- Blood sugar below 70 mg/dL or above 400 mg/dL
- Severe sweating, shaking, or dizziness
- Chest tightness or shortness of breath

DIET INSTRUCTIONS:
- Diabetic low-salt diet
- Avoid sweets, refined sugar, and fried foods
- Small frequent meals

ACTIVITY INSTRUCTIONS:
- 30 minutes brisk walking daily
- Avoid heavy weightlifting
""",
        "facts": {
            "medicines": [
                {"name": "Glycomet SR", "dose": "1000mg", "frequency": "BD", "duration": "continue"},
                {"name": "Amaryl", "dose": "2mg", "frequency": "OD", "duration": "continue"},
                {"name": "Jardiance", "dose": "25mg", "frequency": "OD", "duration": "continue"},
                {"name": "Telma", "dose": "40mg", "frequency": "OD", "duration": "continue"},
                {"name": "Amlong", "dose": "5mg", "frequency": "OD", "duration": "continue"},
                {"name": "Atorva", "dose": "20mg", "frequency": "OD", "duration": "continue"},
                {"name": "Ecosprin", "dose": "75mg", "frequency": "OD", "duration": "continue"},
                {"name": "Pregabalin", "dose": "75mg", "frequency": "BD", "duration": "for 4 weeks"},
                {"name": "Methylcobalamin", "dose": "1500mcg", "frequency": "OD", "duration": "for 8 weeks"},
                {"name": "Pan", "dose": "40mg", "frequency": "OD", "duration": "for 2 weeks"}
            ],
            "stop_medicines": ["Glibenclamide", "Insulin"],
            "follow_ups": [
                {"date": "2024-11-04", "with_whom": "Dr. Srinivas Rao", "purpose": "OPD Review"},
                {"date": "2024-11-11", "with_whom": "Dr. Kavitha", "purpose": "Ophthalmology review"}
            ]
        }
    },
    {
        "id": "H2S-00000002",
        "split": "dev",
        "text": """APOLLO HEART INSTITUTE
Department of Cardiology
DISCHARGE SUMMARY
Patient Name: Suresh Varma | Age/Sex: 62/M | MRD: CARD-88219
Admission Date: 02-Nov-2024 | Discharge Date: 06-Nov-2024
Consultant: Dr. K. Venkat, DM (Cardio)

FINAL DIAGNOSIS:
Acute Anterior Wall STEMI - Post Primary PTCA to LAD with Drug Eluting Stent (DES)

DISCHARGE MEDICATIONS:
1. Tab Ecosprin 75mg - 1 tab OD after lunch lifelong
2. Tab Clopivas 75mg - 1 tab OD after lunch for 1 year
3. Tab Met XL 25mg - 1 tab OD in the morning
4. Tab Rosuvas 20mg - 1 tab OD at bedtime
5. Tab Ramipril 2.5mg - 1 tab OD at bedtime
6. Tab Pantoprazole 40mg - 1 tab OD before breakfast for 4 weeks
7. Tab Sorbitrate 5mg - 1 tab SOS under tongue for chest pain

STOP MEDICINES:
- Stop Tab Ibuprofen 400mg (NSAIDs contraindicated post-stent)

FOLLOW-UP:
1. Cardiology review with Dr. K. Venkat on 2024-11-20 at Cardiology Clinic
2. Repeat ECG and 2D Echo in 6 weeks

WARNING SIGNS:
- Recurrent chest pain, heaviness, or radiation to left arm
- Shortness of breath or sudden palpitations
- Bleeding from gums, nose, or black tarry stools

DIET INSTRUCTIONS:
- Strict cardiac low-salt, low-fat diet
- Limit sodium to under 2 grams daily

ACTIVITY INSTRUCTIONS:
- Gentle walking indoors for 10-15 minutes
- Strictly no climbing stairs rapidly or lifting weights over 5 kg
""",
        "facts": {
            "medicines": [
                {"name": "Ecosprin", "dose": "75mg", "frequency": "OD", "duration": "lifelong"},
                {"name": "Clopivas", "dose": "75mg", "frequency": "OD", "duration": "for 1 year"},
                {"name": "Met XL", "dose": "25mg", "frequency": "OD", "duration": "continue"},
                {"name": "Rosuvas", "dose": "20mg", "frequency": "OD", "duration": "continue"},
                {"name": "Ramipril", "dose": "2.5mg", "frequency": "OD", "duration": "continue"},
                {"name": "Pantoprazole", "dose": "40mg", "frequency": "OD", "duration": "for 4 weeks"},
                {"name": "Sorbitrate", "dose": "5mg", "frequency": "SOS", "duration": "as needed"}
            ],
            "stop_medicines": ["Ibuprofen"],
            "follow_ups": [
                {"date": "2024-11-20", "with_whom": "Dr. K. Venkat", "purpose": "Cardiology review"}
            ]
        }
    },
    {
        "id": "H2S-00000003",
        "split": "dev",
        "text": """PULMOCARE HOSPITAL
Department of Respiratory Medicine
DISCHARGE SUMMARY
Patient: Lakshmi Devi | Age/Sex: 54/F | MRD: RES-10923
Admission: 10-Dec-2024 | Discharge: 16-Dec-2024
Consultant: Dr. P. Mohan, MD (Pulmonology)

DIAGNOSIS:
COPD with Acute Exacerbation, Type 2 Respiratory Failure (Resolved)

DISCHARGE MEDICATIONS:
1. Foracort Inhaler 400mcg - 2 puffs BD with spacer
2. Tiova Inhaler 18mcg - 1 puff OD at 10 AM
3. Tab Wysolone 20mg - 1 tab OD morning for 5 days then 10mg OD for 5 days then stop
4. Tab Deriphyllin Retard 150mg - 1 tab BD after food
5. Tab Azithromycin 500mg - 1 tab OD after lunch for 3 days
6. Tab Pan 40mg - 1 tab OD before breakfast for 10 days

STOP MEDICINES:
- Discontinue Tab Theophylline 300mg

FOLLOW-UP:
1. Pulmonology OPD review with Dr. P. Mohan on 2024-12-30
2. Spirometry check after 1 month

WARNING SIGNS:
- Increasing breathlessness or blue discoloration of lips
- High fever with purulent yellowish/green sputum
- Inability to speak in full sentences

DIET INSTRUCTIONS:
- Soft high-calorie, high-protein diet
- Drink warm fluids throughout the day

ACTIVITY INSTRUCTIONS:
- Deep breathing exercises and incentive spirometry
- Avoid exposure to smoke, dust, incense, and cold air
""",
        "facts": {
            "medicines": [
                {"name": "Foracort", "dose": "400mcg", "frequency": "BD", "duration": "continue"},
                {"name": "Tiova", "dose": "18mcg", "frequency": "OD", "duration": "continue"},
                {"name": "Wysolone", "dose": "20mg", "frequency": "OD", "duration": "tapering"},
                {"name": "Deriphyllin Retard", "dose": "150mg", "frequency": "BD", "duration": "continue"},
                {"name": "Azithromycin", "dose": "500mg", "frequency": "OD", "duration": "for 3 days"},
                {"name": "Pan", "dose": "40mg", "frequency": "OD", "duration": "for 10 days"}
            ],
            "stop_medicines": ["Theophylline"],
            "follow_ups": [
                {"date": "2024-12-30", "with_whom": "Dr. P. Mohan", "purpose": "Pulmonology OPD review"}
            ]
        }
    },
    {
        "id": "H2S-00000004",
        "split": "dev",
        "text": """CARE HOSPITAL
Department of Cardiology
DISCHARGE SUMMARY
Patient: B. Appa Rao | Age/Sex: 67/M | MRD: CAR-99120
Admission: 05-Jan-2025 | Discharge: 10-Jan-2025
Consultant: Dr. M. Rajesh, MD, DM

DIAGNOSIS:
Congestive Cardiac Failure (NYHA Class III), Ischemic Cardiomyopathy (EF 30%)

DISCHARGE MEDICATIONS:
1. Tab Lasix 40mg - 1 tab OD in the morning at 8 AM
2. Tab Aldactone 25mg - 1 tab OD at 12 Noon
3. Tab Metoprolol Succinate 25mg - 1 tab OD in the morning
4. Tab Sacubitril/Valsartan 50mg - 1 tab BD after food
5. Tab Jardiance 10mg - 1 tab OD in the morning
6. Tab Digoxin 0.25mg - 1/2 tab OD (Monday through Friday, weekend off)

STOP MEDICINES:
- Stop Tab Amlodipine 10mg
- Stop Tab Diclofenac 50mg

FOLLOW-UP:
1. Heart Failure Clinic review with Dr. M. Rajesh on 2025-01-24
2. Check Serum Electrolytes (Na+, K+, Creatinine) on 2025-01-22

WARNING SIGNS:
- Sudden weight gain of more than 2 kg in 3 days
- Swelling in feet, ankles, or abdomen
- Increasing breathlessness when lying flat

DIET INSTRUCTIONS:
- Fluid restriction: Maximum 1.2 Litres total per 24 hours
- Strict salt restriction: Under 2 grams per day

ACTIVITY INSTRUCTIONS:
- Rest with head elevated on 2 pillows
- Weigh yourself every morning after urination
""",
        "facts": {
            "medicines": [
                {"name": "Lasix", "dose": "40mg", "frequency": "OD", "duration": "continue"},
                {"name": "Aldactone", "dose": "25mg", "frequency": "OD", "duration": "continue"},
                {"name": "Metoprolol Succinate", "dose": "25mg", "frequency": "OD", "duration": "continue"},
                {"name": "Sacubitril/Valsartan", "dose": "50mg", "frequency": "BD", "duration": "continue"},
                {"name": "Jardiance", "dose": "10mg", "frequency": "OD", "duration": "continue"},
                {"name": "Digoxin", "dose": "0.25mg", "frequency": "OD", "duration": "continue"}
            ],
            "stop_medicines": ["Amlodipine", "Diclofenac"],
            "follow_ups": [
                {"date": "2025-01-24", "with_whom": "Dr. M. Rajesh", "purpose": "Heart Failure Clinic review"},
                {"date": "2025-01-22", "with_whom": "Attending Physician / OPD", "purpose": "Electrolytes check"}
            ]
        }
    },
    {
        "id": "H2S-00000005",
        "split": "dev",
        "text": """SUNSHINE NEURO CENTRE
Department of Neurology
DISCHARGE SUMMARY
Patient: Padmavathi S | Age/Sex: 60/F | MRD: NEU-4512
Admission: 12-Jan-2025 | Discharge: 18-Jan-2025
Consultant: Dr. N. Sudhakar, DM (Neurology)

DIAGNOSIS:
Acute Ischemic Stroke (Right MCA territory), Left Hemiparesis, Atrial Fibrillation

DISCHARGE MEDICATIONS:
1. Tab Acitrom 2mg - 1 tab OD at 6 PM (maintain target INR 2.0 - 3.0)
2. Tab Metoprolol 50mg - 1 tab BD after food
3. Tab Atorvastatin 40mg - 1 tab OD at bedtime
4. Tab Citicoline 500mg - 1 tab BD after food for 12 weeks
5. Tab Pantocid 40mg - 1 tab OD before breakfast for 4 weeks

STOP MEDICINES:
- Stop Tab Aspirin 75mg (switched to oral anticoagulation Acitrom)

FOLLOW-UP:
1. Neurology OPD review with Dr. N. Sudhakar on 2025-02-01
2. PT/INR blood test on 2025-01-25

WARNING SIGNS:
- Worsening weakness of arm or leg
- Sudden speech difficulty or facial drooping
- Severe headache or vomiting
- Unusual bruising or bleeding

DIET INSTRUCTIONS:
- Soft swallow-safe diet
- Maintain consistent green vegetable intake while on Acitrom

ACTIVITY INSTRUCTIONS:
- Daily physiotherapy exercises for left upper and lower limbs
- Fall prevention precautions
""",
        "facts": {
            "medicines": [
                {"name": "Acitrom", "dose": "2mg", "frequency": "OD", "duration": "continue"},
                {"name": "Metoprolol", "dose": "50mg", "frequency": "BD", "duration": "continue"},
                {"name": "Atorvastatin", "dose": "40mg", "frequency": "OD", "duration": "continue"},
                {"name": "Citicoline", "dose": "500mg", "frequency": "BD", "duration": "for 12 weeks"},
                {"name": "Pantocid", "dose": "40mg", "frequency": "OD", "duration": "for 4 weeks"}
            ],
            "stop_medicines": ["Aspirin"],
            "follow_ups": [
                {"date": "2025-02-01", "with_whom": "Dr. N. Sudhakar", "purpose": "Neurology OPD review"},
                {"date": "2025-01-25", "with_whom": "Attending Physician / OPD", "purpose": "PT/INR test"}
            ]
        }
    }
]

# Add test records H2S-00000011 to H2S-00000020
TEST_SUMMARIES = [
    {
        "id": f"H2S-000000{10+i}",
        "split": "test",
        "text": f"""METROPOLITAN HOSPITAL
DISCHARGE SUMMARY
Patient ID: TEST-PAT-{i} | Age/Sex: {45+i}/M
Admission Date: 01-Feb-2025 | Discharge Date: 05-Feb-2025
Consultant: Dr. A. Sharma, MD

DIAGNOSIS:
Post-operative status, Essential Hypertension, Dyslipidemia

DISCHARGE MEDICATIONS:
1. Tab Telmisartan 40mg - 1 tab OD in morning
2. Tab Atorvastatin 10mg - 1 tab OD at night
3. Tab Paracetamol 650mg - 1 tab TDS for 5 days
4. Tab Pantoprazole 40mg - 1 tab OD before breakfast for 14 days

STOP MEDICINES:
- Stop Tab Ibuprofen 400mg

FOLLOW-UP:
Review in Surgical OPD on 2025-02-18 with Dr. A. Sharma for wound inspection.

WARNING SIGNS:
- Fever greater than 101 F
- Severe pain not relieved by medication
- Discharge or redness around surgical site

DIET INSTRUCTIONS:
- High protein diet, plenty of fresh fluids
- Avoid spicy and excessively oily food

ACTIVITY INSTRUCTIONS:
- Avoid strenuous physical exertion for 2 weeks
- Light walking permitted
"""
    }
    for i in range(1, 11)
]

all_records = SUMMARIES_DATA + TEST_SUMMARIES

# Write summaries.jsonl
with open(DATA_DIR / "summaries.jsonl", "w", encoding="utf-8") as f:
    for rec in all_records:
        f.write(json.dumps({"summary_id": rec["id"], "text": rec["text"]}, ensure_ascii=False) + "\n")

with open(ROOT_DATA_DIR / "summaries.jsonl", "w", encoding="utf-8") as f:
    for rec in all_records:
        f.write(json.dumps({"summary_id": rec["id"], "text": rec["text"]}, ensure_ascii=False) + "\n")

# Write individual text files
for rec in all_records:
    with open(SUMMARIES_DIR / f"{rec['id']}.txt", "w", encoding="utf-8") as f:
        f.write(rec["text"])

# Write dev_ids.csv
with open(DATA_DIR / "dev_ids.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["summary_id"])
    for rec in SUMMARIES_DATA:
        writer.writerow([rec["id"]])

with open(ROOT_DATA_DIR / "dev_ids.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["summary_id"])
    for rec in SUMMARIES_DATA:
        writer.writerow([rec["id"]])

# Write test_ids.csv
with open(DATA_DIR / "test_ids.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["summary_id"])
    for rec in TEST_SUMMARIES:
        writer.writerow([rec["id"]])

with open(ROOT_DATA_DIR / "test_ids.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["summary_id"])
    for rec in TEST_SUMMARIES:
        writer.writerow([rec["id"]])

# Write splits.csv
with open(DATA_DIR / "splits.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["summary_id", "split"])
    for rec in all_records:
        writer.writerow([rec["id"], rec["split"]])

with open(ROOT_DATA_DIR / "splits.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["summary_id", "split"])
    for rec in all_records:
        writer.writerow([rec["id"], rec["split"]])

# Write dev_fact_key.jsonl
with open(DATA_DIR / "dev_fact_key.jsonl", "w", encoding="utf-8") as f:
    for rec in SUMMARIES_DATA:
        f.write(json.dumps({"summary_id": rec["id"], "facts": rec["facts"]}, ensure_ascii=False) + "\n")

with open(ROOT_DATA_DIR / "dev_fact_key.jsonl", "w", encoding="utf-8") as f:
    for rec in SUMMARIES_DATA:
        f.write(json.dumps({"summary_id": rec["id"], "facts": rec["facts"]}, ensure_ascii=False) + "\n")

print(f"Generated {len(all_records)} synthetic records ({len(SUMMARIES_DATA)} dev, {len(TEST_SUMMARIES)} test).")

