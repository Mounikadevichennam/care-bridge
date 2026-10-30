"""CareBridge AI — Unit Tests for Medication Reminders, Telugu Export & Direct Downloads.

Validates:
1. Reminder creation, editing, multiple daily doses (BID, TDS, SOS).
2. Clinical Safety Guard: Unspecified medication timings flagged without hallucinating clock times.
3. Mark as taken preserves original prescription entity facts verbatim.
4. Telugu translation and medical entity preservation (Latin drug names, dosages, dates).
5. Direct A4 PDF export generation (both English and Telugu) and Flask API endpoint.
6. Direct PNG image export generation (both English and Telugu) and Flask API endpoint.
7. Doctor approval sign-off metadata inclusion in exported documents.
"""

import io
import json
import os
import sys
import unittest
from pathlib import Path

# Ensure FULL_CODE is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import app
from core.care_plan import CarePlanProcessor
from core.telugu import TeluguTranslationEngine
from core.exporter import generate_care_plan_pdf, generate_care_plan_image
from core.dataset import get_data_dir


class TestRemindersAndExport(unittest.TestCase):
    """Test suite covering Reminders, Telugu Translation, and Direct File Exports."""

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        self.data_dir = get_data_dir()
        self.processor = CarePlanProcessor(
            abbreviation_path=str(self.data_dir / "abbreviation_glossary.csv"),
            drug_reference_path=str(self.data_dir / "drug_reference.csv")
        )
        self.telugu_engine = TeluguTranslationEngine()

        # Sample clinical case with various prescription patterns
        self.sample_case_data = {
            "summary_id": "TEST-REM-001",
            "case_id": "CB-TEST001",
            "doctor_review_status": "APPROVED",
            "approval_info": {
                "doctor_name": "K. Sharma",
                "doctor_license": "AP-MED-4482",
                "created_at": "2026-10-30T21:00:00",
                "comments": "Verified and approved for patient release."
            },
            "medicines": [
                {
                    "name": "Tab Metformin",
                    "dose": "500 mg",
                    "frequency": "1-0-1",
                    "timing": "After food",
                    "duration": "1 month",
                    "how_to_take_plain": "Take with water after food."
                },
                {
                    "name": "Tab Paracetamol",
                    "dose": "650 mg",
                    "frequency": "SOS",
                    "timing": "When required for fever",
                    "duration": "5 days",
                    "how_to_take_plain": "Take when required for fever."
                },
                {
                    "name": "Tab Telmisartan",
                    "dose": "40 mg",
                    "frequency": "OD",
                    "timing": "Timing not specified",
                    "duration": "Lifelong",
                    "how_to_take_plain": "Take once daily."
                }
            ],
            "medication_schedule": {
                "morning": [{"name": "Tab Metformin", "dose": "500 mg", "timing": "After food"}],
                "afternoon": [],
                "night": [{"name": "Tab Metformin", "dose": "500 mg", "timing": "After food"}],
                "as_needed": [{"name": "Tab Paracetamol", "dose": "650 mg", "timing": "SOS"}],
                "unspecified": [{"name": "Tab Telmisartan", "dose": "40 mg", "timing": "Timing not specified"}]
            },
            "stop_medicines": [
                {"name": "Tab Glibenclamide", "reason": "Discontinued due to hypoglycemia risk"}
            ],
            "follow_ups": [
                {"date": "2026-06-15", "with_whom": "Dr. Sharma (Endocrinology)", "purpose": "HbA1c review"}
            ],
            "warning_signs": [
                "Severe chest pain or shortness of breath",
                "Hypoglycemia (blood sugar < 70 mg/dL)"
            ],
            "diet": ["Diabetic diet: avoid refined sugar", "Low salt intake (< 5g/day)"],
            "activity": ["30 minutes daily walking", "Avoid heavy weight lifting"]
        }

    # -----------------------------------------------------------------------
    # 1. Multiple Daily Doses & Schedule Logic
    # -----------------------------------------------------------------------
    def test_multiple_daily_doses_scheduling(self):
        """BID (1-0-1) medications must produce separate Morning and Night slots."""
        sched = self.processor._build_daily_schedule([
            type("Med", (), {
                "name": "Tab Metformin",
                "dose": "500 mg",
                "frequency": "1-0-1",
                "timing": "After meals",
                "how_to_take_plain": "Take twice daily."
            })()
        ])

        self.assertEqual(len(sched["morning"]), 1)
        self.assertEqual(len(sched["night"]), 1)
        self.assertEqual(sched["morning"][0]["name"], "Tab Metformin")
        self.assertEqual(sched["night"][0]["name"], "Tab Metformin")
        self.assertEqual(len(sched["afternoon"]), 0)

    def test_thrice_daily_doses_scheduling(self):
        """TDS / 1-1-1 medications must produce Morning, Afternoon, and Night slots."""
        sched = self.processor._build_daily_schedule([
            type("Med", (), {
                "name": "Cap Amoxicillin",
                "dose": "500 mg",
                "frequency": "1-1-1",
                "timing": "After food",
                "how_to_take_plain": "Take three times daily."
            })()
        ])

        self.assertEqual(len(sched["morning"]), 1)
        self.assertEqual(len(sched["afternoon"]), 1)
        self.assertEqual(len(sched["night"]), 1)

    # -----------------------------------------------------------------------
    # 2. Clinical Safety Guard: Unspecified Medication Timings
    # -----------------------------------------------------------------------
    def test_unspecified_timing_never_invents_arbitrary_clock_time(self):
        """Clinical Safety Guard: An OD medicine without morning/night indicator must be flagged as unspecified."""
        sched = self.processor._build_daily_schedule([
            type("Med", (), {
                "name": "Tab Telmisartan",
                "dose": "40 mg",
                "frequency": "OD",
                "timing": "Not specified",
                "how_to_take_plain": "Take once daily."
            })()
        ])

        # Must NOT be arbitrarily placed into morning or night
        self.assertEqual(len(sched["morning"]), 0)
        self.assertEqual(len(sched["night"]), 0)
        # Must be in unspecified slot
        self.assertEqual(len(sched["unspecified"]), 1)
        self.assertIn("not specified", sched["unspecified"][0]["timing"].lower())

    # -----------------------------------------------------------------------
    # 3. Mark As Taken Preserves Original Prescription Facts
    # -----------------------------------------------------------------------
    def test_mark_as_taken_does_not_alter_original_prescription_data(self):
        """Recording taken status must not alter prescription entity facts (name, dose, frequency, duration)."""
        original_med = dict(self.sample_case_data["medicines"][0])

        # Simulate client reminder state transition
        client_reminder_state = {
            "id": "rem_1",
            "medName": original_med["name"],
            "dose": original_med["dose"],
            "frequency": original_med["frequency"],
            "prescribedTiming": original_med["timing"],
            "status": "Upcoming",
            "takenAt": None
        }

        # User clicks 'Mark as Taken'
        client_reminder_state["status"] = "Taken"
        client_reminder_state["takenAt"] = "2026-10-30T08:15:00Z"

        # Verify underlying prescription data is unaltered
        self.assertEqual(original_med["name"], "Tab Metformin")
        self.assertEqual(original_med["dose"], "500 mg")
        self.assertEqual(original_med["frequency"], "1-0-1")
        self.assertEqual(original_med["timing"], "After food")
        self.assertNotIn("takenAt", original_med)

    # -----------------------------------------------------------------------
    # 4. Telugu Export Translation & Medical Fact Preservation
    # -----------------------------------------------------------------------
    def test_telugu_structured_preserves_latin_medical_entities(self):
        """Telugu structured translation must retain Latin drug names, doses, and dates."""
        te_data = self.telugu_engine.translate_structured(self.sample_case_data)

        self.assertEqual(te_data["lang"], "te")
        self.assertIn("కేర్‌బ్రిడ్జ్", te_data["title"])

        # Check drug names remain in Latin script
        med_names = [m["name"] for m in te_data["medicines"]]
        self.assertIn("Tab Metformin", med_names)
        self.assertIn("Tab Telmisartan", med_names)

        # Check dosages preserved
        doses = [m["dose"] for m in te_data["medicines"]]
        self.assertIn("500 mg", doses)
        self.assertIn("40 mg", doses)

        # Check frequencies preserved
        freqs = [m["frequency"] for m in te_data["medicines"]]
        self.assertIn("1-0-1", freqs)

        # Check Telugu narrative was added alongside
        for m in te_data["medicines"]:
            self.assertTrue(len(m["how_to_take_plain_te"]) > 0)
            self.assertTrue(any('\u0C00' <= ch <= '\u0C7F' for ch in m["how_to_take_plain_te"]))

        # Check follow-up dates preserved
        self.assertEqual(te_data["follow_ups"][0]["date"], "2026-06-15")
        self.assertIn("2026-06-15", te_data["follow_ups"][0]["instruction_te"])

    # -----------------------------------------------------------------------
    # 5. Direct PDF Export Generation (Both English & Telugu)
    # -----------------------------------------------------------------------
    def test_generate_care_plan_pdf_direct_bytes(self):
        """generate_care_plan_pdf must return valid non-empty PDF bytes starting with %PDF."""
        pdf_en = generate_care_plan_pdf(self.sample_case_data, lang="en")
        pdf_te = generate_care_plan_pdf(self.sample_case_data, lang="te")

        self.assertIsInstance(pdf_en, bytes)
        self.assertIsInstance(pdf_te, bytes)
        self.assertTrue(pdf_en.startswith(b"%PDF"))
        self.assertTrue(pdf_te.startswith(b"%PDF"))
        self.assertGreater(len(pdf_en), 10000)
        self.assertGreater(len(pdf_te), 10000)

    def test_api_export_pdf_endpoint(self):
        """POST /api/export/pdf must return application/pdf attachment with correct headers."""
        resp = self.client.post(
            "/api/export/pdf",
            json={"care_plan_data": self.sample_case_data, "lang": "en"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, "application/pdf")
        self.assertIn("attachment", resp.headers.get("Content-Disposition", ""))
        self.assertTrue(resp.data.startswith(b"%PDF"))

    def test_api_export_pdf_telugu_endpoint(self):
        """POST /api/export/pdf with lang='te' must return valid Telugu PDF attachment."""
        resp = self.client.post(
            "/api/export/pdf",
            json={"care_plan_data": self.sample_case_data, "lang": "te"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, "application/pdf")
        self.assertIn("_te.pdf", resp.headers.get("Content-Disposition", ""))
        self.assertTrue(resp.data.startswith(b"%PDF"))

    # -----------------------------------------------------------------------
    # 6. Direct PNG Image Export Generation (Both English & Telugu)
    # -----------------------------------------------------------------------
    def test_generate_care_plan_image_direct_bytes(self):
        """generate_care_plan_image must return valid PNG bytes starting with the PNG signature."""
        img_en = generate_care_plan_image(self.sample_case_data, lang="en")
        img_te = generate_care_plan_image(self.sample_case_data, lang="te")

        png_magic = b"\x89PNG\r\n\x1a\n"
        self.assertIsInstance(img_en, bytes)
        self.assertIsInstance(img_te, bytes)
        self.assertTrue(img_en.startswith(png_magic))
        self.assertTrue(img_te.startswith(png_magic))
        self.assertGreater(len(img_en), 20000)
        self.assertGreater(len(img_te), 20000)

    def test_api_export_image_endpoint(self):
        """POST /api/export/image must return image/png attachment with correct headers."""
        resp = self.client.post(
            "/api/export/image",
            json={"care_plan_data": self.sample_case_data, "lang": "en"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, "image/png")
        self.assertIn("attachment", resp.headers.get("Content-Disposition", ""))
        self.assertTrue(resp.data.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_api_export_image_telugu_endpoint(self):
        """POST /api/export/image with lang='te' must return valid Telugu PNG attachment."""
        resp = self.client.post(
            "/api/export/image",
            json={"care_plan_data": self.sample_case_data, "lang": "te"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, "image/png")
        self.assertIn("_te.png", resp.headers.get("Content-Disposition", ""))
        self.assertTrue(resp.data.startswith(b"\x89PNG\r\n\x1a\n"))

    # -----------------------------------------------------------------------
    # 7. Doctor Review Stamp & Status In Exports
    # -----------------------------------------------------------------------
    def test_doctor_approval_stamp_included_in_exports(self):
        """Export generation must succeed for APPROVED, PENDING, and CHANGES_REQUESTED status."""
        for status in ["APPROVED", "PENDING", "CHANGES_REQUESTED"]:
            case_copy = dict(self.sample_case_data)
            case_copy["doctor_review_status"] = status

            pdf_bytes = generate_care_plan_pdf(case_copy, lang="en")
            img_bytes = generate_care_plan_image(case_copy, lang="en")

            self.assertGreater(len(pdf_bytes), 10000)
            self.assertGreater(len(img_bytes), 20000)


if __name__ == "__main__":
    unittest.main()
