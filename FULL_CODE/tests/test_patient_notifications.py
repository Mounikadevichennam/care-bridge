"""Tests for Patient Notification History, Status Separation, and Version Consistency.

Covers Part 3, Part 4, Part 5, Part 6, Part 8, and Part 11 requirements.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from app import app
from core.database import (
    init_db,
    save_case_care_plan,
    submit_doctor_review,
    get_case,
    get_patient_notifications,
    get_patient_notification_by_id,
    mark_patient_notification_read,
    get_db,
)


class TestPatientNotificationHistory(unittest.TestCase):
    """Test suite for patient notification history, persistence, and workflow."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_path = Path(self.temp_db.name)
        init_db(self.db_path)

        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        os.environ['CAREBRIDGE_DB_PATH'] = str(self.db_path)
        self.client = app.test_client()

    def tearDown(self):
        try:
            if self.db_path.exists():
                self.db_path.unlink()
        except Exception:
            pass

    def test_plan_submitted_notification_created(self):
        """Scenario 1: Initial case submission creates a persistent PLAN_SUBMITTED notification."""
        care_plan = {
            "english_plan": "Take Metformin 500mg daily",
            "telugu_plan": "రోజూ మెట్‌ఫార్మిన్ తీసుకోండి",
            "medicines": [{"name": "Metformin", "dose": "500 mg", "frequency": "1-0-1"}],
            "validation": {"overall_status": "PASS"}
        }
        res = save_case_care_plan(
            summary_id="H2S-DEMO01",
            original_text="Patient: John Doe\nDiagnosis: T2DM\nTab Metformin 500 mg BD",
            care_plan_result=care_plan,
            case_id="CB-DEMO01",
            patient_session_id="PAT-SESSION-001",
            db_path=self.db_path
        )
        self.assertEqual(res["status"], "PENDING")
        self.assertEqual(res["version"], 1)

        notifs = get_patient_notifications(
            patient_session_id="PAT-SESSION-001",
            db_path=self.db_path
        )
        self.assertEqual(len(notifs), 1)
        n = notifs[0]
        self.assertEqual(n["event_type"], "PLAN_SUBMITTED")
        self.assertEqual(n["case_id"], "CB-DEMO01")
        self.assertEqual(n["case_version"], 1)
        self.assertEqual(n["status_badge"], "PENDING DOCTOR REVIEW")
        self.assertIn("Care Plan Sent to Doctor", n["title"])
        self.assertIn("వైద్యుడి సమీక్షకు", n["title_te"])

    def test_approval_creates_plan_approved_notification(self):
        """Scenario 2: Doctor approval creates a PLAN_APPROVED notification with doctor info."""
        care_plan = {
            "english_plan": "Take Metformin 500mg daily",
            "telugu_plan": "మెట్‌ఫార్మిన్ తీసుకోండి",
            "medicines": [{"name": "Metformin", "dose": "500 mg", "frequency": "1-0-1"}],
            "validation": {"overall_status": "PASS"}
        }
        save_case_care_plan(
            summary_id="H2S-DEMO02",
            original_text="Patient: Jane Doe\nDiagnosis: T2DM\nTab Metformin 500 mg BD",
            care_plan_result=care_plan,
            case_id="CB-DEMO02",
            patient_session_id="PAT-SESSION-002",
            db_path=self.db_path
        )

        # Doctor approves version 1
        rev = submit_doctor_review(
            case_id="CB-DEMO02",
            doctor_id=1,
            action="APPROVE",
            comments="Verified against clinical chart. All instructions safe.",
            db_path=self.db_path
        )
        self.assertEqual(rev["status"], "APPROVED")

        # Fetch notifications for patient
        notifs = get_patient_notifications(
            patient_session_id="PAT-SESSION-002",
            db_path=self.db_path
        )
        # BOTH notifications must exist in history!
        self.assertEqual(len(notifs), 2)

        approved_notif = next(n for n in notifs if n["event_type"] == "PLAN_APPROVED")
        submitted_notif = next(n for n in notifs if n["event_type"] == "PLAN_SUBMITTED")

        self.assertIsNotNone(approved_notif)
        self.assertIsNotNone(submitted_notif)
        self.assertEqual(approved_notif["status_badge"], "APPROVED")
        self.assertIn("Dr. Farah Siddiqui", approved_notif["doctor_name"])
        self.assertEqual(approved_notif["doctor_license"], "MCI-748291")
        self.assertEqual(approved_notif["case_version"], 1)
        self.assertIn("/?case_id=CB-DEMO02", approved_notif["action_url"])

    def test_changes_requested_and_resubmission_flow(self):
        """Scenario 3: Changes requested followed by resubmission creates complete audit trail."""
        care_plan = {
            "english_plan": "Take Metformin",
            "telugu_plan": "మెట్‌ఫార్మిన్",
            "medicines": [{"name": "Metformin", "dose": "500 mg"}],
            "validation": {"overall_status": "PASS"}
        }
        save_case_care_plan(
            summary_id="H2S-DEMO03",
            original_text="Patient: Bob\nDiagnosis: HTN\nTab Metformin 500 mg",
            care_plan_result=care_plan,
            case_id="CB-DEMO03",
            patient_session_id="PAT-SESSION-003",
            db_path=self.db_path
        )

        # Doctor requests changes
        submit_doctor_review(
            case_id="CB-DEMO03",
            doctor_id=1,
            action="REQUEST_CHANGES",
            comments="Clarify exact timing relative to food consumption.",
            db_path=self.db_path
        )

        case = get_case("CB-DEMO03", db_path=self.db_path)
        self.assertEqual(case["status"], "CHANGES_REQUESTED")

        # Resubmit with corrected text (generates version 2)
        revised_care_plan = {
            "english_plan": "Take Metformin 500 mg after meals",
            "telugu_plan": "భోజనం తర్వాత మెట్‌ఫార్మిన్ తీసుకోండి",
            "medicines": [{"name": "Metformin", "dose": "500 mg", "timing": "after meals"}],
            "validation": {"overall_status": "PASS"}
        }
        res_v2 = save_case_care_plan(
            summary_id="H2S-DEMO03",
            original_text="Patient: Bob\nDiagnosis: HTN\nTab Metformin 500 mg after meals",
            care_plan_result=revised_care_plan,
            case_id="CB-DEMO03",
            patient_session_id="PAT-SESSION-003",
            db_path=self.db_path
        )
        self.assertEqual(res_v2["version"], 2)
        self.assertEqual(res_v2["status"], "PENDING")

        # Notification history must now contain:
        # 1. PLAN_SUBMITTED (v1)
        # 2. CHANGES_REQUESTED (v1)
        # 3. PLAN_RESUBMITTED (v2)
        notifs = get_patient_notifications(
            patient_session_id="PAT-SESSION-003",
            db_path=self.db_path
        )
        self.assertEqual(len(notifs), 3)
        event_types = [n["event_type"] for n in notifs]
        self.assertIn("PLAN_SUBMITTED", event_types)
        self.assertIn("CHANGES_REQUESTED", event_types)
        self.assertIn("PLAN_RESUBMITTED", event_types)

        v2_notif = next(n for n in notifs if n["event_type"] == "PLAN_RESUBMITTED")
        self.assertEqual(v2_notif["case_version"], 2)
        self.assertEqual(v2_notif["status_badge"], "PENDING DOCTOR REVIEW")

    def test_idempotent_approval_prevents_duplicate_records(self):
        """Scenario 4: Re-submitting approval does not create duplicate reviews or notifications."""
        care_plan = {
            "english_plan": "Plan text",
            "telugu_plan": "ప్లాన్ టెక్స్ట్",
            "medicines": [{"name": "Aspirin", "dose": "75 mg"}],
            "validation": {"overall_status": "PASS"}
        }
        save_case_care_plan(
            summary_id="H2S-DEMO04",
            original_text="Patient: Mary\nTab Aspirin 75 mg",
            care_plan_result=care_plan,
            case_id="CB-DEMO04",
            patient_session_id="PAT-SESSION-004",
            db_path=self.db_path
        )

        # First approval
        submit_doctor_review(
            case_id="CB-DEMO04",
            doctor_id=1,
            action="APPROVE",
            comments="First approval",
            db_path=self.db_path
        )

        # Immediate duplicate approval attempt
        submit_doctor_review(
            case_id="CB-DEMO04",
            doctor_id=1,
            action="APPROVE",
            comments="Duplicate click",
            db_path=self.db_path
        )

        notifs = get_patient_notifications(
            patient_session_id="PAT-SESSION-004",
            db_path=self.db_path
        )
        approved_notifs = [n for n in notifs if n["event_type"] == "PLAN_APPROVED"]
        self.assertEqual(len(approved_notifs), 1, "Duplicate approval notification was improperly created!")

    def test_patient_isolation_and_case_lookup(self):
        """Scenario 5: Patient sessions are isolated but can lookup by known case IDs."""
        care_plan = {
            "english_plan": "Test",
            "telugu_plan": "టెస్ట్",
            "medicines": [],
            "validation": {"overall_status": "PASS"}
        }
        save_case_care_plan(
            summary_id="H2S-P1",
            original_text="Patient A",
            care_plan_result=care_plan,
            case_id="CB-P1",
            patient_session_id="SESSION-PAT-A",
            db_path=self.db_path
        )
        save_case_care_plan(
            summary_id="H2S-P2",
            original_text="Patient B",
            care_plan_result=care_plan,
            case_id="CB-P2",
            patient_session_id="SESSION-PAT-B",
            db_path=self.db_path
        )

        # Patient A should only see Patient A's notifications
        notifs_a = get_patient_notifications(
            patient_session_id="SESSION-PAT-A",
            db_path=self.db_path
        )
        self.assertEqual(len(notifs_a), 1)
        self.assertEqual(notifs_a[0]["case_id"], "CB-P1")

        # Patient B passing case_ids=['CB-P2'] sees CB-P2
        notifs_b = get_patient_notifications(
            patient_session_id="SESSION-PAT-B",
            case_ids=["CB-P2"],
            db_path=self.db_path
        )
        self.assertEqual(len(notifs_b), 1)
        self.assertEqual(notifs_b[0]["case_id"], "CB-P2")

    def test_notification_api_endpoints(self):
        """Scenario 6: Test Flask API endpoints for notifications."""
        with self.client.session_transaction() as sess:
            sess['patient_session_id'] = 'API-TEST-PAT'

        care_plan = {
            "english_plan": "API Plan",
            "telugu_plan": "ఏపీఐ ప్లాన్",
            "medicines": [],
            "validation": {"overall_status": "PASS"}
        }
        save_case_care_plan(
            summary_id="H2S-API",
            original_text="Patient API Test",
            care_plan_result=care_plan,
            case_id="CB-API",
            patient_session_id="API-TEST-PAT",
            db_path=self.db_path
        )

        # GET /api/patient/notifications
        resp = self.client.get('/api/patient/notifications')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['notifications']), 1)
        notif_id = data['notifications'][0]['notification_id']

        # GET /api/patient/notifications/<id>
        resp_single = self.client.get(f'/api/patient/notifications/{notif_id}')
        self.assertEqual(resp_single.status_code, 200)
        self.assertEqual(resp_single.get_json()['notification_id'], notif_id)

        # POST /api/patient/notifications/<id>/read
        resp_read = self.client.post(f'/api/patient/notifications/{notif_id}/read')
        self.assertEqual(resp_read.status_code, 200)
        self.assertTrue(resp_read.get_json()['success'])

        # Verify read_at is now set
        notif_updated = get_patient_notification_by_id(notif_id, db_path=self.db_path)
        self.assertIsNotNone(notif_updated['read_at'])

    def test_status_separation_approved_with_technical_flag(self):
        """Scenario 7: Approved plan with non-blocking technical flag maintains clean separation."""
        # Care plan with NEEDS_REVIEW validation flag
        care_plan = {
            "english_plan": "Take Metformin 500mg daily",
            "telugu_plan": "మెట్‌ఫార్మిన్ తీసుకోండి",
            "medicines": [{"name": "Metformin", "dose": "500 mg"}],
            "validation": {
                "overall_status": "NEEDS_REVIEW",
                "patient_status": "FLAGGED",
                "patient_message": "Instruction timing unspecified in source."
            }
        }
        save_case_care_plan(
            summary_id="H2S-FLAG01",
            original_text="Patient: Charlie\nTab Metformin 500 mg",
            care_plan_result=care_plan,
            case_id="CB-FLAG01",
            patient_session_id="PAT-SESSION-FLAG",
            db_path=self.db_path
        )

        # Doctor approves despite technical flag
        rev = submit_doctor_review(
            case_id="CB-FLAG01",
            doctor_id=1,
            action="APPROVE",
            comments="I have examined the timing and confirmed patient should take with breakfast.",
            db_path=self.db_path
        )

        case = get_case("CB-FLAG01", db_path=self.db_path)
        # Doctor Review Status must be APPROVED
        self.assertEqual(case["status"], "APPROVED")
        # Technical Validation Status remains NEEDS_REVIEW (not silently altered to PASS)
        self.assertEqual(case["care_plan_version"]["validation_status"], "NEEDS_REVIEW")


if __name__ == "__main__":
    unittest.main()
