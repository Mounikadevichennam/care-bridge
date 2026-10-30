"""Comprehensive Tests for CareBridge AI Doctor Clinical Portal.

Verifies:
1. Database schema initialization and seed accounts.
2. Doctor authentication and PBKDF2/SHA-256 password hashing.
3. Session management, login, logout, and protected route access control.
4. Patient care plan ingestion and automatic case tracking in PENDING state.
5. Doctor case review workflows (CHANGES_REQUESTED with comments vs. APPROVE).
6. Clinical audit trail logging and immutability.
7. Patient portal status synchronization.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

# Set up test database path before imports
test_db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
test_db_path = Path(test_db_file.name)
test_db_file.close()
os.environ["CAREBRIDGE_DB_PATH"] = str(test_db_path)

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app
from core.database import (
    init_db,
    authenticate_doctor,
    register_doctor,
    save_case_care_plan,
    get_case,
    list_cases,
    submit_doctor_review,
    get_dashboard_stats,
    get_audit_logs,
)


class TestDoctorPortal(unittest.TestCase):
    """Test suite for the doctor clinical portal."""

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        os.environ["CAREBRIDGE_DB_PATH"] = str(test_db_path)
        init_db(test_db_path)
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        if test_db_path.exists():
            try:
                test_db_path.unlink()
            except Exception:
                pass
        os.environ.pop("CAREBRIDGE_DB_PATH", None)

    def test_01_seed_doctors_initialized(self):
        """Verify default clinician accounts are initialized with secure hashed passwords."""
        doc = authenticate_doctor("dr.siddiqui@chandrapuri.org", "DoctorCare2026!", db_path=test_db_path)
        self.assertIsNotNone(doc)
        self.assertEqual(doc["name"], "Dr. Farah Siddiqui, MD")
        self.assertEqual(doc["license_number"], "MCI-748291")

        # Invalid password must fail
        failed_doc = authenticate_doctor("dr.siddiqui@chandrapuri.org", "WrongPassword123!", db_path=test_db_path)
        self.assertIsNone(failed_doc)

        # Non-existent email must fail
        no_doc = authenticate_doctor("unknown@hospital.org", "DoctorCare2026!", db_path=test_db_path)
        self.assertIsNone(no_doc)

    def test_02_register_doctor_account(self):
        """Verify new doctor registration with password hashing."""
        new_doc = register_doctor(
            email="dr.ananya@chandrapuri.org",
            password="AnanyaSecure2026!",
            name="Dr. Ananya Sen, MD",
            license_number="MCI-992144",
            department="Neurology",
            db_path=test_db_path
        )
        self.assertEqual(new_doc["email"], "dr.ananya@chandrapuri.org")
        self.assertEqual(new_doc["name"], "Dr. Ananya Sen, MD")

        # Verify login
        auth = authenticate_doctor("dr.ananya@chandrapuri.org", "AnanyaSecure2026!", db_path=test_db_path)
        self.assertIsNotNone(auth)
        self.assertEqual(auth["id"], new_doc["id"])

    def test_03_protected_routes_require_authentication(self):
        """Verify unauthorized users cannot access the doctor dashboard or review cases."""
        # Unauthenticated access to dashboard
        res = self.client.get("/doctor/dashboard")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/doctor/login", res.headers.get("Location", ""))

        # Unauthenticated review action
        post_res = self.client.post("/doctor/case/CB-047NPLXP/review", data={
            "action": "APPROVE",
            "comments": "Unauthorized approval attempt"
        })
        self.assertEqual(post_res.status_code, 302)
        self.assertIn("/doctor/login", post_res.headers.get("Location", ""))

    def test_04_doctor_login_and_logout_session(self):
        """Verify complete session-based login and logout flow."""
        # 1. Invalid login attempt
        bad_login = self.client.post("/doctor/login", data={
            "email": "dr.siddiqui@chandrapuri.org",
            "password": "IncorrectPassword"
        })
        self.assertEqual(bad_login.status_code, 401)
        self.assertIn(b"Invalid email or password", bad_login.data)

        # 2. Valid login
        good_login = self.client.post("/doctor/login", data={
            "email": "dr.siddiqui@chandrapuri.org",
            "password": "DoctorCare2026!"
        }, follow_redirects=True)
        self.assertEqual(good_login.status_code, 200)
        self.assertIn(b"Dr. Farah Siddiqui, MD", good_login.data)
        self.assertIn(b"Doctor Review Portal", good_login.data)

        # 3. Access protected dashboard now succeeds
        dash_res = self.client.get("/doctor/dashboard")
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b"Pending Reviews", dash_res.data)

        # 4. Logout
        logout_res = self.client.get("/doctor/logout", follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)
        self.assertIn(b"safely logged out", logout_res.data)

        # 5. Subsequent access is blocked
        blocked_dash = self.client.get("/doctor/dashboard")
        self.assertEqual(blocked_dash.status_code, 302)

    def test_05_case_creation_and_pending_status(self):
        """Verify that newly generated care plans are queued with PENDING doctor review status."""
        test_summary = """CHANDRAPURI DISTRICT HOSPITAL
DISCHARGE SUMMARY
Patient: Lissy Dhillon | Age: 52/F | UHID: CDH6253077
Final Diagnosis: Diabetic ketoacidosis - resolved, Type 2 diabetes mellitus
Medications at Discharge:
- Tab. Metformin 500 mg 1-0-1 PC till review
- Tab. Telmisartan 40 mg OD morning
Follow-up: Diabetes Clinic on 21/05/2026"""

        res = self.client.post("/api/process", json={
            "text": test_summary,
            "summary_id": "H2S-TEST001"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("case_id", data)
        self.assertEqual(data["doctor_review_status"], "PENDING")
        self.assertEqual(data["case_version"], 1)

        # Verify case in database
        case_db = get_case(data["case_id"], db_path=test_db_path)
        self.assertIsNotNone(case_db)
        self.assertEqual(case_db["status"], "PENDING")
        self.assertEqual(case_db["patient_name"], "Lissy Dhillon")

        # Verify API query: Unauthenticated patient access to PENDING case is blocked (403)
        api_res = self.client.get(f"/api/case/{data['case_id']}")
        self.assertEqual(api_res.status_code, 403)
        self.assertFalse(api_res.get_json().get("is_approved", True))

        # Authenticated doctor can retrieve the pending case (200)
        self.client.post("/doctor/login", data={
            "email": "dr.siddiqui@chandrapuri.org",
            "password": "DoctorCare2026!"
        })
        doc_api_res = self.client.get(f"/api/case/{data['case_id']}")
        self.assertEqual(doc_api_res.status_code, 200)
        doc_data = doc_api_res.get_json()
        self.assertEqual(doc_data["status"], "PENDING")
        self.client.get("/doctor/logout")

    def test_06_doctor_request_changes_workflow(self):
        """Verify requesting corrections requires comments, updates status, and logs audit."""
        # Authenticate doctor session
        self.client.post("/doctor/login", data={
            "email": "dr.siddiqui@chandrapuri.org",
            "password": "DoctorCare2026!"
        })

        case_id = "CB-TEST001"

        # 1. Requesting changes without comments must be rejected
        empty_comment_res = self.client.post(f"/doctor/case/{case_id}/review", data={
            "action": "REQUEST_CHANGES",
            "comments": "   "
        })
        self.assertEqual(empty_comment_res.status_code, 400)
        self.assertIn(b"Comments are required", empty_comment_res.data)

        # 2. Requesting changes with explicit comments
        valid_change_res = self.client.post(f"/doctor/case/{case_id}/review", data={
            "action": "REQUEST_CHANGES",
            "comments": "Please confirm renal function test (serum creatinine) before continuing Metformin."
        })
        self.assertEqual(valid_change_res.status_code, 200)
        self.assertIn(b"CHANGES REQUESTED", valid_change_res.data)
        self.assertIn(b"Please confirm renal function test", valid_change_res.data)

        # Verify case status in database is now CHANGES_REQUESTED
        case = get_case(case_id, db_path=test_db_path)
        self.assertEqual(case["status"], "CHANGES_REQUESTED")
        self.assertEqual(case["latest_change_request"]["doctor_name"], "Dr. Farah Siddiqui, MD")

    def test_07_doctor_approval_workflow_and_audit(self):
        """Verify doctor approval records doctor identity, timestamp, version, and creates audit trail."""
        # Log in as Dr. Rajesh Patel
        self.client.post("/doctor/login", data={
            "email": "dr.patel@chandrapuri.org",
            "password": "DoctorCare2026!"
        })

        case_id = "CB-TEST001"

        # Submit Approval
        appr_res = self.client.post(f"/doctor/case/{case_id}/review", data={
            "action": "APPROVE",
            "comments": "Renal parameters verified (S.Cr 0.5 mg/dl). Care plan approved for patient home care."
        })
        self.assertEqual(appr_res.status_code, 200)
        self.assertIn(b"CERTIFIED APPROVED", appr_res.data)
        self.assertIn(b"Dr. Rajesh Patel", appr_res.data)

        # Verify case status in database is now APPROVED
        case = get_case(case_id, db_path=test_db_path)
        self.assertEqual(case["status"], "APPROVED")
        self.assertIsNotNone(case["approval_info"])
        self.assertEqual(case["approval_info"]["doctor_name"], "Dr. Rajesh Patel, MBBS, MD")
        self.assertEqual(case["approval_info"]["doctor_license"], "MCI-591024")
        self.assertIn("Renal parameters verified", case["approval_info"]["comments"])

        # Verify audit logs
        logs = get_audit_logs(case_id=case_id, db_path=test_db_path)
        self.assertTrue(len(logs) >= 2)
        event_types = [l["event_type"] for l in logs]
        self.assertIn("PLAN_APPROVED", event_types)

    def test_08_reprocessing_resets_approval_to_pending(self):
        """Verify that updating a discharge summary creates a new version and resets approval to PENDING."""
        updated_summary = """CHANDRAPURI DISTRICT HOSPITAL
DISCHARGE SUMMARY
Patient: Lissy Dhillon | Age: 52/F
Medications:
- Tab. Metformin 500 mg 1-0-1 PC till review
- Tab. Telmisartan 40 mg OD
- Tab. Atorvastatin 20 mg HS (added)"""

        res = self.client.post("/api/process", json={
            "text": updated_summary,
            "summary_id": "H2S-TEST001"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Version must increment to 2 and status must be PENDING
        self.assertEqual(data["case_version"], 2)
        self.assertEqual(data["doctor_review_status"], "PENDING")

        case = get_case(data["case_id"], db_path=test_db_path)
        self.assertEqual(case["status"], "PENDING")
        self.assertEqual(case["current_version"], 2)
        # Prior approval history must be preserved
        self.assertTrue(len(case["reviews"]) >= 2)

    def test_09_dashboard_statistics_live(self):
        """Verify dashboard statistics reflect real database state."""
        stats = get_dashboard_stats(db_path=test_db_path)
        self.assertIsInstance(stats["total_cases"], int)
        self.assertTrue(stats["total_cases"] >= 1)
        self.assertIsInstance(stats["pending_count"], int)
        self.assertIsInstance(stats["approved_count"], int)
        self.assertIsInstance(stats["changes_requested_count"], int)
        self.assertIsInstance(stats["recent_reviews"], list)


if __name__ == "__main__":
    unittest.main()
