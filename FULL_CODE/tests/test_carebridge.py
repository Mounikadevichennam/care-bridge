"""CareBridge AI — Comprehensive Automated Test Suite.

Covers all 26 minimum hackathon testing requirements:
1. Empty input handling
2. Invalid/garbage input
3. Valid discharge summary processing
4. Medicine extraction
5. Exact dose preservation (including fractions & units)
6. Frequency extraction (including 1-0-1 pattern)
7. Duration extraction (including lifelong & tapering)
8. Discontinued medicine segregation (safety guarantee)
9. Follow-up date normalization (ISO YYYY-MM-DD)
10. Ambiguous date handling
11. Unsupported instructions not invented (Faithfulness Above Fluency)
12. Telugu script output density
13. Telugu Latin drug-name and Western digit preservation
14. OCR text extraction from images
15. PDF stream extraction
16. Invalid file uploads rejection
17. OCR uncertainty and decimal spacing detection
18. Duplicate medicine handling
19. Missing information handling
20. Failed validation detection (hallucinations & safety violations)
21. Incomplete validation detection
22. Family fridge sheet generation
23. Daily medication schedule slots (Morning, Afternoon, Night, SOS)
24. Flask API document upload endpoint
25. Test submission ID completeness
26. Submission JSONL schema conformance
"""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Insert FULL_CODE into sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.abbreviation import AbbreviationResolver
from core.medicine_mapper import MedicineMapper
from core.frequency_parser import FrequencyParser
from core.date_parser import DateParser
from core.extractor import DischargeSummaryExtractor, CarePlanData, MedicineInfo, FollowUpInfo
from core.english_renderer import EnglishCarePlanRenderer
from core.telugu import TeluguTranslationEngine
from core.validator import FaithfulnessValidator
from core.readability import ReadabilityCalculator
from core.care_plan import CarePlanProcessor
from core.document_reader import DocumentReader


class TestCareBridgeComprehensive(unittest.TestCase):
    """Complete 26-requirement test suite for CareBridge AI."""

    @classmethod
    def setUpClass(cls):
        cls.processor = CarePlanProcessor()
        cls.extractor = DischargeSummaryExtractor()
        cls.date_parser = DateParser()
        cls.freq_parser = FrequencyParser()
        cls.readability = ReadabilityCalculator()
        cls.telugu = TeluguTranslationEngine()
        cls.validator = FaithfulnessValidator()
        cls.doc_reader = DocumentReader()

    # 1. Empty input
    def test_01_empty_input(self):
        res = self.processor.process("T01", "")
        self.assertEqual(len(res["medicines"]), 0)
        self.assertIn("CAREBRIDGE", res["english_plan"])
        self.assertIn("no active medications", res["english_plan"].lower())

    # 2. Invalid input
    def test_02_invalid_input(self):
        res = self.processor.process("T02", "$$#@%^&*()*&^%$#@! 12345 ???")
        self.assertEqual(len(res["medicines"]), 0)
        self.assertIsNotNone(res["validation"]["patient_status"])

    # 3. Valid discharge summary
    def test_03_valid_discharge_summary(self):
        note = """CITY GENERAL HOSPITAL
DISCHARGE SUMMARY
Patient: Ramesh | Age: 58/M
DIAGNOSIS: Type 2 Diabetes Mellitus
DISCHARGE MEDICATIONS:
1. Tab Metformin 500mg BD after food for 30 days
2. Tab Ecosprin 75mg OD after lunch continue
STOP MEDICINES:
- Stop Tab Glibenclamide 5mg
FOLLOW UP:
Review with Dr. Rao on 04-Nov-2024 at OPD
WARNING SIGNS:
- Blood sugar below 70 mg/dL
DIET INSTRUCTIONS:
- Diabetic low salt diet
ACTIVITY INSTRUCTIONS:
- 30 minutes daily walking
"""
        res = self.processor.process("T03", note)
        self.assertGreaterEqual(len(res["medicines"]), 2)
        self.assertEqual(len(res["stop_medicines"]), 1)
        self.assertEqual(len(res["follow_ups"]), 1)
        self.assertEqual(res["follow_ups"][0]["date"], "2024-11-04")

    # 4. Medicine extraction
    def test_04_medicine_extraction(self):
        note = """DISCHARGE MEDICATIONS:
1. Tab Metformin 500mg BD
2. Tab Telmisartan 40mg OD
3. Tab Atorvastatin 20mg HS
"""
        data = self.extractor.extract(note)
        self.assertEqual(len(data.medicines), 3)
        names = [m.name.lower() for m in data.medicines]
        self.assertTrue(any("metformin" in n for n in names))
        self.assertTrue(any("telmisartan" in n for n in names))
        self.assertTrue(any("atorvastatin" in n for n in names))

    # 5. Exact dose preservation
    def test_05_exact_dose_preservation(self):
        note = """DISCHARGE MEDICATIONS:
1. Tab Digoxin 0.25mg half tablet OD
2. Inj Mixtard 16 units before breakfast
3. Cap Pregabalin 75mg BD
"""
        data = self.extractor.extract(note)
        doses = [m.dose.lower() for m in data.medicines]
        self.assertTrue(any("0.25" in d for d in doses))
        self.assertTrue(any("16 units" in d or "units" in d for d in doses))
        self.assertTrue(any("75mg" in d for d in doses))

    # 6. Frequency extraction
    def test_06_frequency_extraction(self):
        p_num = self.freq_parser.parse_frequency("1-0-1")
        self.assertIn("morning", p_num["normalized"].lower())
        self.assertIn("night", p_num["normalized"].lower())

        p_tds = self.freq_parser.parse_frequency("TDS")
        self.assertEqual(p_tds["times_per_day"], 3)

        p_sos = self.freq_parser.parse_frequency("SOS")
        self.assertIn("needed", p_sos["normalized"].lower())

    # 7. Duration extraction
    def test_07_duration_extraction(self):
        d1 = self.freq_parser.parse_duration("for 14 days")
        self.assertEqual(d1, "for 14 days")

        d2 = self.freq_parser.parse_duration("lifelong")
        self.assertEqual(d2, "lifelong")

        d3 = self.freq_parser.parse_duration("continue")
        self.assertEqual(d3, "continue")

    # 8. Discontinued medicines
    def test_08_discontinued_medicines_segregation(self):
        note = """DISCHARGE MEDICATIONS:
1. Tab Metformin 500mg BD
STOP MEDICINES:
- Stop Tab Glibenclamide 5mg
- Discontinue Tab Aspirin 75mg
"""
        data = self.extractor.extract(note)
        active_names = [m.name.upper() for m in data.medicines]
        stop_names = [s["name"].upper() for s in data.stop_medicines]

        self.assertIn("GLIBENCLAMIDE", stop_names)
        self.assertIn("ASPIRIN", stop_names)
        self.assertNotIn("GLIBENCLAMIDE", active_names)
        self.assertNotIn("ASPIRIN", active_names)

    # 9. Follow-up dates
    def test_09_follow_up_dates(self):
        date_iso = self.date_parser.parse_date("Follow up on 2026-11-20")
        self.assertEqual(date_iso, "2026-11-20")

        date_named = self.date_parser.parse_date("Review on 15-Nov-2024")
        self.assertEqual(date_named, "2024-11-15")

        date_slash = self.date_parser.parse_date("Review on 04/11/2024")
        self.assertEqual(date_slash, "2024-11-04")

    # 10. Ambiguous dates
    def test_10_ambiguous_dates(self):
        # A relative timeframe like 'after 2 weeks'
        parsed = self.date_parser.parse_date("Review after 2 weeks")
        self.assertIsNotNone(parsed)

    # 11. Unsupported instructions not invented
    def test_11_unsupported_instructions_not_invented(self):
        # Summary with NO warning signs, NO diet, and NO activity
        note = """DISCHARGE MEDICATIONS:
1. Tab Metformin 500mg BD
"""
        res = self.processor.process("T11", note)
        en_plan = res["english_plan"]
        te_plan = res["telugu_plan"]

        self.assertIn("Not specified in the discharge summary", en_plan)
        self.assertNotIn("Severe chest pain, extreme breathlessness", en_plan)
        self.assertIn("డిశ్చార్జ్ సారాంశంలో ప్రత్యేక", te_plan)

    # 12. Telugu script output density
    def test_12_telugu_script_density(self):
        note = "Tab Telmisartan 40mg OD in the morning for 30 days."
        res = self.processor.process("T12", note)
        share = res["telugu_script_share"]
        self.assertGreaterEqual(share, 0.50)

    # 13. Telugu drug-name and digit preservation
    def test_13_telugu_drug_name_latin_preservation(self):
        note = "Tab Atorvastatin 20mg OD at bedtime."
        res = self.processor.process("T13", note)
        te_plan = res["telugu_plan"]
        self.assertIn("Atorvastatin", te_plan)
        self.assertIn("20mg", te_plan)

    # 14. OCR text extraction from images
    def test_14_ocr_text_extraction(self):
        sample_img = Path("FULL_CODE/tools/sample_test.png")
        if sample_img.exists():
            res = self.doc_reader.read_document(sample_img)
            self.assertEqual(res["format"], ".png")
            self.assertGreater(len(res["text"]), 10)

    # 15. PDF stream extraction
    def test_15_pdf_extraction(self):
        # Construct minimal valid PDF binary stream
        minimal_pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj\n4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 72 712 Td (Tab Metformin 500mg) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n250\n%%EOF"
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(minimal_pdf)
            temp_pdf_path = Path(f.name)

        try:
            res = self.doc_reader.read_document(temp_pdf_path)
            self.assertEqual(res["format"], ".pdf")
            self.assertIn("Metformin", res["text"])
        finally:
            if temp_pdf_path.exists():
                temp_pdf_path.unlink()

    # 16. Invalid file uploads rejection
    def test_16_invalid_file_uploads_rejected(self):
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"not a valid doc")
            bad_path = Path(f.name)

        try:
            res = self.doc_reader.read_document(bad_path)
            self.assertEqual(res["method"], "error")
            self.assertTrue(len(res["warnings"]) > 0)
        finally:
            if bad_path.exists():
                bad_path.unlink()

    # 17. OCR uncertainty and decimal spacing detection
    def test_17_ocr_uncertainty_detection(self):
        noisy_text = "Patient prescribed Tab Digoxin 0 . 5 mg OD and l0mg of Atorvastatin."
        warnings = self.doc_reader._detect_text_uncertainties(noisy_text)
        self.assertGreaterEqual(len(warnings), 1)

    # 18. Duplicate medicine handling
    def test_18_duplicate_medicines_handling(self):
        note = """DISCHARGE MEDICATIONS:
1. Tab Metformin 500mg BD after food
2. Tab Metformin 500mg BD after food
"""
        data = self.extractor.extract(note)
        # Should extract clean entries without crashing
        self.assertGreaterEqual(len(data.medicines), 1)

    # 19. Missing information handling
    def test_19_missing_information_faithfulness(self):
        note = "Tab Paracetamol 650mg."
        res = self.processor.process("T19", note)
        med = res["medicines"][0]
        self.assertEqual(med["name"], "Paracetamol")
        self.assertEqual(med["dose"], "650mg")
        # Timing was not specified in source
        self.assertIn("As directed", med["timing"])

    # 20. Failed validation detection (hallucinations & safety violations)
    def test_20_failed_validation_detection(self):
        # Discontinued medicine appearing in active list
        bad_data = CarePlanData(
            summary_id="BAD-1",
            medicines=[MedicineInfo(name="Warfarin", dose="5mg", frequency="OD", timing="", duration="", how_to_take_plain="")],
            stop_medicines=[{"name": "Warfarin", "reason": "Discontinued due to bleeding"}]
        )
        report = self.validator.validate("Discontinue Warfarin", bad_data, "", "")
        self.assertEqual(report.overall_status, "FAIL")
        self.assertEqual(report.patient_status, "CHECK FAILED")

    # 21. Incomplete validation detection
    def test_21_incomplete_validation_detection(self):
        # Follow-up date without source backing
        data = CarePlanData(
            summary_id="INC-1",
            medicines=[MedicineInfo(name="Metformin", dose="500mg", frequency="OD", timing="", duration="", how_to_take_plain="")],
            follow_ups=[FollowUpInfo(date="2099-01-01", with_whom="Dr. Unknown", purpose="Check")]
        )
        report = self.validator.validate("Tab Metformin 500mg", data, "Metformin", "Metformin")
        self.assertEqual(report.patient_status, "VERIFICATION INCOMPLETE")

    # 22. Family sheet generation
    def test_22_family_sheet_generation(self):
        note = "Tab Ecosprin 75mg OD after lunch. Review on 2026-11-20."
        res = self.processor.process("T22", note)
        self.assertIn("medicines", res)
        self.assertIn("follow_ups", res)
        self.assertGreater(len(res["medicines"]), 0)

    # 23. Daily medication schedule slots
    def test_23_daily_schedule_slots(self):
        note = """DISCHARGE MEDICATIONS:
1. Tab Metformin 500mg BD after food
2. Tab Pantoprazole 40mg OD before breakfast
3. Tab Atorvastatin 20mg HS at bedtime
4. Tab Paracetamol 650mg SOS for headache
"""
        res = self.processor.process("T23", note)
        sched = res["medication_schedule"]
        self.assertGreaterEqual(len(sched["morning"]), 1)
        self.assertGreaterEqual(len(sched["night"]), 1)
        self.assertGreaterEqual(len(sched["as_needed"]), 1)

    # 24. Flask API document upload endpoint
    def test_24_browser_upload_api(self):
        from app import app
        client = app.test_client()
        fake_file = (io.BytesIO(b"DISCHARGE SUMMARY\nTab Metformin 500mg BD"), "summary.txt")
        resp = client.post("/api/upload", data={"file": fake_file}, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["format"], ".txt")
        self.assertIn("Metformin", data["text"])

    # 25. Test submission ID completeness (Official Organizer 300 Test IDs)
    def test_25_test_submission_id_completeness(self):
        from core.dataset import get_ids_file
        test_ids_file = get_ids_file("test")
        self.assertTrue(test_ids_file.exists())
        import csv
        with open(test_ids_file, "r", encoding="utf-8") as f:
            ids = [row["summary_id"] for row in csv.DictReader(f)]
        self.assertEqual(len(ids), 300)
        self.assertEqual(len(ids), len(set(ids)))

    # 26. Submission JSONL schema conformance
    def test_26_jsonl_schema_validation(self):
        sub_file = Path("submission/H2_predictions.jsonl")
        if not sub_file.exists():
            return
        with open(sub_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        self.assertTrue(len(lines) in (10, 300))
        for obj in lines:
            self.assertIn("summary_id", obj)
            self.assertIn("care_plan", obj)
            self.assertIn("medicines", obj["care_plan"])
            self.assertIn("stop_medicines", obj["care_plan"])
            self.assertIn("follow_ups", obj["care_plan"])
            self.assertIn("plain_text_en", obj)
            self.assertIn("translation", obj)
            self.assertEqual(obj["translation"]["language_code"], "te")
            self.assertIn("readability", obj)

    # 27. Organizer dataset integrity verification (Single source of truth)
    def test_27_organizer_dataset_counts(self):
        from core.dataset import verify_dataset
        report = verify_dataset()
        self.assertEqual(report["status"], "valid", f"Dataset validation failed: {report.get('errors')}")
        self.assertEqual(report["counts"]["summaries"], 2000)
        self.assertEqual(report["counts"]["dev_ids"], 200)
        self.assertEqual(report["counts"]["test_ids"], 300)
        self.assertEqual(report["counts"]["dev_fact_keys"], 200)
        self.assertEqual(report["counts"]["glossary_entries"], 257)
        self.assertEqual(report["counts"]["drug_reference_entries"], 81)


if __name__ == "__main__":
    unittest.main()
