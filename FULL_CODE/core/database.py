"""CareBridge AI — SQLite Database and Audit Trail Engine.

Manages persistent storage for:
- Doctor credentials and authentication
- Patient cases and clinical discharge summary references
- Versioned bilingual care plans
- Doctor review workflow (Pending, Changes Requested, Approved)
- Immutable clinical audit trail
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)

# Default database location in FULL_CODE directory
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "carebridge.db"


def get_db_path() -> Path:
    """Return database file path from environment or default."""
    env_path = os.environ.get("CAREBRIDGE_DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


def _create_schema(conn: sqlite3.Connection) -> None:
    """Internal helper to create SQLite tables and seed clinician accounts."""
    cursor = conn.cursor()

    # 1. Doctors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            license_number TEXT NOT NULL,
            department TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
    """)

    # 2. Patient Cases table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            summary_id TEXT NOT NULL,
            patient_name TEXT,
            condition_summary TEXT,
            original_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            current_version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)

    # Index on status and summary_id
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_summary_id ON cases(summary_id);")

    # 3. Care Plan Versions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS care_plan_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            care_plan_json TEXT NOT NULL,
            english_plan TEXT NOT NULL,
            telugu_plan TEXT NOT NULL,
            readability_score REAL,
            validation_status TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
            UNIQUE (case_id, version)
        );
    """)

    # 4. Doctor Reviews table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            version_reviewed INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            doctor_name TEXT NOT NULL,
            doctor_license TEXT NOT NULL,
            action TEXT NOT NULL, -- 'APPROVE' or 'REQUEST_CHANGES'
            comments TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_case_id ON reviews(case_id);")

    # 5. Clinical Audit Log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT,
            event_type TEXT NOT NULL,
            user_id TEXT,
            user_name TEXT,
            details TEXT,
            ip_address TEXT,
            timestamp TEXT NOT NULL
        );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_case_id ON audit_log(case_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);")

    # Safe migration: ensure patient_session_id column exists on cases
    try:
        cursor.execute("ALTER TABLE cases ADD COLUMN patient_session_id TEXT;")
    except Exception:
        pass  # Column already exists

    # 6. Patient Notifications & Case Activity History table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notification_id TEXT UNIQUE NOT NULL,
            case_id TEXT NOT NULL,
            patient_session_id TEXT,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            title_te TEXT,
            message TEXT NOT NULL,
            message_te TEXT,
            case_version INTEGER NOT NULL DEFAULT 1,
            status_badge TEXT NOT NULL,
            status_badge_te TEXT,
            doctor_name TEXT,
            doctor_license TEXT,
            comments TEXT,
            action_url TEXT,
            created_at TEXT NOT NULL,
            read_at TEXT,
            metadata_json TEXT,
            FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
        );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notif_session ON patient_notifications(patient_session_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notif_case ON patient_notifications(case_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notif_created ON patient_notifications(created_at);")

    # Seed default clinician accounts if empty
    cursor.execute("SELECT COUNT(*) FROM doctors;")
    count = cursor.fetchone()[0]
    if count == 0:
        now_iso = datetime.now(timezone.utc).isoformat()
        default_doctors = [
            (
                "dr.siddiqui@chandrapuri.org",
                generate_password_hash("DoctorCare2026!"),
                "Dr. Farah Siddiqui, MD",
                "MCI-748291",
                "General Medicine Unit II",
                1,
                now_iso
            ),
            (
                "dr.patel@chandrapuri.org",
                generate_password_hash("DoctorCare2026!"),
                "Dr. Rajesh Patel, MBBS, MD",
                "MCI-591024",
                "Cardiology & Critical Care",
                1,
                now_iso
            )
        ]
        cursor.executemany("""
            INSERT INTO doctors (email, password_hash, name, license_number, department, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, default_doctors)
        logger.info("Initialized database with default clinician accounts.")


@contextmanager
def get_db(db_path: Optional[Path | str] = None):
    """Context manager for SQLite connection with row factory and WAL mode."""
    target_path = Path(db_path) if db_path else get_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target_path), timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except Exception:
        pass  # In-memory or restricted filesystems

    # Ensure schema exists on connection
    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cases';").fetchone()
    if not row:
        _create_schema(conn)

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[Path | str] = None) -> None:
    """Initialize database tables and seed default clinician accounts."""
    with get_db(db_path) as conn:
        _create_schema(conn)


# ---------------------------------------------------------------------------
# Doctor Authentication Methods
# ---------------------------------------------------------------------------

def authenticate_doctor(email: str, password: str, db_path: Optional[Path | str] = None) -> Optional[Dict[str, Any]]:
    """Verify doctor credentials and return doctor profile dict if valid."""
    clean_email = (email or "").strip().lower()
    if not clean_email or not password:
        return None

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, password_hash, name, license_number, department, is_active
            FROM doctors
            WHERE email = ?;
        """, (clean_email,))
        row = cursor.fetchone()
        if not row:
            return None

        if not row["is_active"]:
            logger.warning(f"Login attempted for inactive doctor account: {clean_email}")
            return None

        if check_password_hash(row["password_hash"], password):
            return {
                "id": row["id"],
                "email": row["email"],
                "name": row["name"],
                "license_number": row["license_number"],
                "department": row["department"]
            }
    return None


def get_doctor_by_id(doctor_id: int, db_path: Optional[Path | str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve doctor profile by ID."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, name, license_number, department, is_active, created_at
            FROM doctors WHERE id = ?;
        """, (doctor_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None


def register_doctor(
    email: str,
    password: str,
    name: str,
    license_number: str,
    department: str,
    db_path: Optional[Path | str] = None
) -> Dict[str, Any]:
    """Register a new doctor account with hashed password."""
    clean_email = email.strip().lower()
    now_iso = datetime.now(timezone.utc).isoformat()
    pwd_hash = generate_password_hash(password)

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO doctors (email, password_hash, name, license_number, department, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?);
        """, (clean_email, pwd_hash, name.strip(), license_number.strip(), department.strip(), now_iso))
        new_id = cursor.lastrowid

    return {
        "id": new_id,
        "email": clean_email,
        "name": name.strip(),
        "license_number": license_number.strip(),
        "department": department.strip()
    }


# ---------------------------------------------------------------------------
# Case & Care Plan Management Methods
# ---------------------------------------------------------------------------

def generate_case_id(summary_id: str) -> str:
    """Generate a clean clinical case ID from summary ID or timestamp."""
    clean_sid = re.sub(r'[^A-Za-z0-9]', '', summary_id or '')
    if clean_sid.upper().startswith("H2S"):
        return f"CB-{clean_sid[3:]}"
    elif clean_sid:
        return f"CB-{clean_sid[:10].upper()}"
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"CB-{now_str}"


def extract_patient_meta(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Attempt to extract patient name and brief condition from clinical text."""
    name = None
    condition = None

    # Name matching
    name_m = re.search(r'(?:Patient\s*(?:name)?|Pt|Name)\s*[:\-]\s*([A-Za-z\s\.\,\'\-]+?)(?:\||\n|Age|\/|UHID|$)', text, re.IGNORECASE)
    if name_m:
        cand = name_m.group(1).strip()
        if len(cand) > 2 and len(cand) < 50:
            name = cand

    # Condition / Diagnosis matching
    diag_m = re.search(r'(?:Final\s*Diagnosis|Diagnosis|Impression)\s*[:\-]\s*(.+?)(?:\n\n|\n[A-Z]|$)', text, re.IGNORECASE | re.DOTALL)
    if diag_m:
        cand_diag = " ".join(diag_m.group(1).strip().split())
        cand_diag = re.sub(r'[*•\-]', '', cand_diag).strip()
        condition = cand_diag[:120]

    return name, condition


def save_case_care_plan(
    summary_id: str,
    original_text: str,
    care_plan_result: Dict[str, Any],
    case_id: Optional[str] = None,
    patient_session_id: Optional[str] = None,
    db_path: Optional[Path | str] = None,
    ip_address: Optional[str] = None
) -> Dict[str, Any]:
    """Store or update a patient case and its versioned care plan."""
    now_iso = datetime.now(timezone.utc).isoformat()
    cid = case_id or generate_case_id(summary_id)
    pat_name, condition = extract_patient_meta(original_text)

    # Extract care plan fields
    english_plan = care_plan_result.get("english_plan", "")
    telugu_plan = care_plan_result.get("telugu_plan", "")
    readability = care_plan_result.get("readability", {})
    read_score = readability.get("score") if isinstance(readability, dict) else None
    val_status = care_plan_result.get("validation", {}).get("overall_status", "NEEDS_REVIEW")

    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # Check existing case
        cursor.execute("SELECT id, status, current_version, patient_session_id FROM cases WHERE id = ?;", (cid,))
        row = cursor.fetchone()

        if row:
            # Case exists: create next version
            new_version = row["current_version"] + 1
            # If previously APPROVED or CHANGES_REQUESTED, submitting a new plan returns it to PENDING for re-review
            new_status = "PENDING"
            effective_session = patient_session_id or row["patient_session_id"]

            cursor.execute("""
                UPDATE cases
                SET original_text = ?,
                    patient_name = COALESCE(?, patient_name),
                    condition_summary = COALESCE(?, condition_summary),
                    status = ?,
                    current_version = ?,
                    patient_session_id = COALESCE(?, patient_session_id),
                    updated_at = ?
                WHERE id = ?;
            """, (original_text, pat_name, condition, new_status, new_version, effective_session, now_iso, cid))

            # Store version
            cursor.execute("""
                INSERT INTO care_plan_versions (
                    case_id, version, care_plan_json, english_plan, telugu_plan,
                    readability_score, validation_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                cid, new_version, json.dumps(care_plan_result, ensure_ascii=False),
                english_plan, telugu_plan, read_score, val_status, now_iso
            ))

            # Log event within existing transaction
            _insert_audit_entry(
                cursor,
                event_type="CASE_UPDATED",
                case_id=cid,
                user_id="SYSTEM",
                user_name="SYSTEM",
                details=f"Generated care plan version {new_version}. Review status reset to PENDING.",
                ip_address=ip_address,
                timestamp=now_iso
            )

            # Insert PLAN_RESUBMITTED notification
            notif_id = f"NOTIF-{uuid.uuid4().hex[:12].upper()}"
            cursor.execute("""
                INSERT INTO patient_notifications (
                    notification_id, case_id, patient_session_id, event_type,
                    title, title_te, message, message_te, case_version,
                    status_badge, status_badge_te, action_url, created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                notif_id, cid, effective_session, "PLAN_RESUBMITTED",
                "Updated Care Plan Sent for Review",
                "నవీకరించిన కేర్ ప్లాన్ తాజా సమీక్షకు పంపబడింది",
                f"Your corrected care plan version v{new_version} has been submitted for a fresh physician review.",
                f"మీ సరిదిద్దబడిన కేర్ ప్లాన్ వెర్షన్ v{new_version} తాజా వైద్యుల సమీక్ష కోసం సమర్పించబడింది.",
                new_version,
                "PENDING DOCTOR REVIEW",
                "వైద్యుల సమీక్ష పెండింగ్‌లో ఉంది",
                f"/doctor/login?next=/doctor/case/{cid}",
                now_iso,
                json.dumps({"summary_id": summary_id, "patient_name": pat_name, "version": new_version})
            ))

            current_status = new_status
            version = new_version
        else:
            # Create new case
            version = 1
            current_status = "PENDING"
            effective_session = patient_session_id

            cursor.execute("""
                INSERT INTO cases (
                    id, summary_id, patient_name, condition_summary,
                    original_text, status, current_version, patient_session_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?);
            """, (cid, summary_id, pat_name, condition, original_text, current_status, effective_session, now_iso, now_iso))

            cursor.execute("""
                INSERT INTO care_plan_versions (
                    case_id, version, care_plan_json, english_plan, telugu_plan,
                    readability_score, validation_status, created_at
                ) VALUES (?, 1, ?, ?, ?, ?, ?, ?);
            """, (
                cid, json.dumps(care_plan_result, ensure_ascii=False),
                english_plan, telugu_plan, read_score, val_status, now_iso
            ))

            _insert_audit_entry(
                cursor,
                event_type="CASE_CREATED",
                case_id=cid,
                user_id="SYSTEM",
                user_name="SYSTEM",
                details="Initial discharge summary processed. Created with status PENDING review.",
                ip_address=ip_address,
                timestamp=now_iso
            )

            # Insert PLAN_SUBMITTED notification
            notif_id = f"NOTIF-{uuid.uuid4().hex[:12].upper()}"
            cursor.execute("""
                INSERT INTO patient_notifications (
                    notification_id, case_id, patient_session_id, event_type,
                    title, title_te, message, message_te, case_version,
                    status_badge, status_badge_te, action_url, created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                notif_id, cid, effective_session, "PLAN_SUBMITTED",
                "Care Plan Sent to Doctor",
                "వైద్యుడి సమీక్షకు కేర్ ప్లాన్ పంపబడింది",
                "Your discharge summary has been processed and your care plan has been sent to the Doctor Portal for clinical review.",
                "మీ డిశ్చార్జ్ సారాంశం ప్రాసెస్ చేయబడింది మరియు క్లినికల్ సమీక్ష కోసం డాక్టర్ పోర్టల్‌కు పంపబడింది.",
                1,
                "PENDING DOCTOR REVIEW",
                "వైద్యుల సమీక్ష పెండింగ్‌లో ఉంది",
                f"/doctor/login?next=/doctor/case/{cid}",
                now_iso,
                json.dumps({"summary_id": summary_id, "patient_name": pat_name, "version": 1})
            ))

    return {
        "case_id": cid,
        "summary_id": summary_id,
        "status": current_status,
        "version": version,
        "patient_name": pat_name,
        "condition_summary": condition,
        "patient_session_id": effective_session
    }


def get_case(case_id: str, version: Optional[int] = None, db_path: Optional[Path | str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve full case details, specified or latest care plan version, and review history."""
    try:
        with get_db(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, summary_id, patient_name, condition_summary, original_text,
                       status, current_version, created_at, updated_at
                FROM cases WHERE id = ?;
            """, (case_id,))
            case_row = cursor.fetchone()
            if not case_row:
                return None

            case_dict = dict(case_row)
            ver_num = version or case_dict["current_version"]

            # Retrieve care plan version
            cursor.execute("""
                SELECT id, version, care_plan_json, english_plan, telugu_plan,
                       readability_score, validation_status, created_at
                FROM care_plan_versions
                WHERE case_id = ? AND version = ?;
            """, (case_id, ver_num))
            ver_row = cursor.fetchone()

            if ver_row:
                case_dict["care_plan_version"] = dict(ver_row)
                try:
                    case_dict["care_plan_data"] = json.loads(ver_row["care_plan_json"])
                except Exception:
                    case_dict["care_plan_data"] = {}
            else:
                case_dict["care_plan_version"] = None
                case_dict["care_plan_data"] = None

            # Retrieve review history
            cursor.execute("""
                SELECT id, case_id, version_reviewed, doctor_id, doctor_name, doctor_license,
                       action, comments, created_at
                FROM reviews
                WHERE case_id = ?
                ORDER BY id DESC;
            """, (case_id,))
            reviews_list = []
            for r in cursor.fetchall():
                rd = dict(r)
                rd["timestamp"] = rd["created_at"]
                reviews_list.append(rd)
            case_dict["reviews"] = reviews_list

            # Latest approval record if approved
            latest_approval = None
            for rev in case_dict["reviews"]:
                if rev["action"] == "APPROVE":
                    latest_approval = rev
                    break
            case_dict["approval_info"] = latest_approval

            # Latest correction request if changes requested
            latest_change_req = None
            for rev in case_dict["reviews"]:
                if rev["action"] == "REQUEST_CHANGES":
                    latest_change_req = rev
                    break
            case_dict["latest_change_request"] = latest_change_req

        return case_dict
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            init_db(db_path)
            return None
        raise


def list_cases(
    status: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[Path | str] = None
) -> Tuple[List[Dict[str, Any]], int]:
    """List cases with optional status filter and text search."""
    conditions = []
    params: List[Any] = []

    if status and status.upper() != "ALL":
        conditions.append("c.status = ?")
        params.append(status.upper())

    if query and query.strip():
        term = f"%{query.strip()}%"
        conditions.append("(c.id LIKE ? OR c.summary_id LIKE ? OR c.patient_name LIKE ? OR c.condition_summary LIKE ?)")
        params.extend([term, term, term, term])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # Count total matching
        cursor.execute(f"SELECT COUNT(*) FROM cases c {where_clause};", params)
        total = cursor.fetchone()[0]

        # Fetch page with latest review info
        cursor.execute(f"""
            SELECT c.id, c.summary_id, c.patient_name, c.condition_summary,
                   c.status, c.current_version, c.created_at, c.updated_at,
                   v.validation_status, v.readability_score
            FROM cases c
            LEFT JOIN care_plan_versions v ON c.id = v.case_id AND c.current_version = v.version
            {where_clause}
            ORDER BY c.updated_at DESC
            LIMIT ? OFFSET ?;
        """, params + [limit, offset])

        rows = [dict(r) for r in cursor.fetchall()]

    return rows, total


def get_dashboard_stats(db_path: Optional[Path | str] = None) -> Dict[str, Any]:
    """Compute live dashboard statistics and recent activity."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM cases WHERE status = 'PENDING';")
        pending_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cases WHERE status = 'APPROVED';")
        approved_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cases WHERE status = 'CHANGES_REQUESTED';")
        changes_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cases;")
        total_cases = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM reviews;")
        total_reviews = cursor.fetchone()[0]

        # Recent review activity
        cursor.execute("""
            SELECT r.id, r.case_id, r.version_reviewed, r.doctor_name, r.action, r.comments, r.created_at,
                   c.patient_name, c.summary_id
            FROM reviews r
            LEFT JOIN cases c ON r.case_id = c.id
            ORDER BY r.id DESC
            LIMIT 8;
        """)
        recent_reviews = [dict(r) for r in cursor.fetchall()]

    return {
        "pending_count": pending_count,
        "approved_count": approved_count,
        "changes_requested_count": changes_count,
        "total_cases": total_cases,
        "total_reviews": total_reviews,
        "recent_reviews": recent_reviews
    }


# ---------------------------------------------------------------------------
# Doctor Review Workflow Actions
# ---------------------------------------------------------------------------

def submit_doctor_review(
    case_id: str,
    doctor_id: int,
    action: str,
    comments: Optional[str] = None,
    db_path: Optional[Path | str] = None,
    ip_address: Optional[str] = None
) -> Dict[str, Any]:
    """Execute a doctor review decision (APPROVE or REQUEST_CHANGES).

    Enforces:
    - Authenticated doctor profile lookup
    - Non-empty comments when requesting changes
    - Atomic case status transition
    - Immutable audit trail entry
    """
    clean_action = (action or "").strip().upper()
    if clean_action not in ("APPROVE", "REQUEST_CHANGES"):
        raise ValueError("Invalid review action. Must be 'APPROVE' or 'REQUEST_CHANGES'.")

    clean_comments = (comments or "").strip()
    if clean_action == "REQUEST_CHANGES" and not clean_comments:
        raise ValueError("Comments are required when requesting changes to a care plan.")

    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # Verify doctor exists
        cursor.execute("SELECT id, name, license_number, department FROM doctors WHERE id = ?;", (doctor_id,))
        doc_row = cursor.fetchone()
        if not doc_row:
            raise ValueError(f"Doctor with ID {doctor_id} not found.")

        doc_name = doc_row["name"]
        doc_license = doc_row["license_number"]

        # Verify case exists
        cursor.execute("SELECT id, current_version, status, patient_session_id FROM cases WHERE id = ?;", (case_id,))
        case_row = cursor.fetchone()
        if not case_row:
            raise ValueError(f"Case with ID {case_id} not found.")

        current_ver = case_row["current_version"]
        new_status = "APPROVED" if clean_action == "APPROVE" else "CHANGES_REQUESTED"
        pat_sess = case_row["patient_session_id"]

        # Prevent duplicate reviews for the same version and action
        cursor.execute("""
            SELECT id FROM reviews
            WHERE case_id = ? AND version_reviewed = ? AND action = ?;
        """, (case_id, current_ver, clean_action))
        existing_rev = cursor.fetchone()
        if existing_rev and case_row["status"] == new_status:
            logger.info(f"Duplicate review suppressed for case {case_id} v{current_ver} action={clean_action}")
            return {
                "review_id": existing_rev["id"],
                "case_id": case_id,
                "status": new_status,
                "version_reviewed": current_ver,
                "action": clean_action,
                "doctor_name": doc_name,
                "doctor_license": doc_license,
                "comments": clean_comments,
                "timestamp": now_iso
            }

        # Insert review record
        cursor.execute("""
            INSERT INTO reviews (
                case_id, version_reviewed, doctor_id, doctor_name, doctor_license,
                action, comments, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (case_id, current_ver, doctor_id, doc_name, doc_license, clean_action, clean_comments, now_iso))
        review_id = cursor.lastrowid

        # Update case status
        cursor.execute("""
            UPDATE cases
            SET status = ?, updated_at = ?
            WHERE id = ?;
        """, (new_status, now_iso, case_id))

        # Log audit entry
        event_name = "PLAN_APPROVED" if clean_action == "APPROVE" else "CHANGES_REQUESTED"
        audit_details = (
            f"Approved care plan version {current_ver} by {doc_name} ({doc_license})."
            if clean_action == "APPROVE"
            else f"Changes requested for version {current_ver} by {doc_name}: {clean_comments}"
        )

        cursor.execute("""
            INSERT INTO audit_log (case_id, event_type, user_id, user_name, details, ip_address, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (case_id, event_name, str(doctor_id), doc_name, audit_details, ip_address, now_iso))

        # Insert patient notification for physician decision
        notif_id = f"NOTIF-{uuid.uuid4().hex[:12].upper()}"
        if clean_action == "APPROVE":
            cursor.execute("""
                INSERT INTO patient_notifications (
                    notification_id, case_id, patient_session_id, event_type,
                    title, title_te, message, message_te, case_version,
                    status_badge, status_badge_te, doctor_name, doctor_license, comments,
                    action_url, created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                notif_id, case_id, pat_sess, "PLAN_APPROVED",
                "Your Care Plan Has Been Approved",
                "మీ కేర్ ప్లాన్ ఆమోదించబడింది",
                f"Your care plan has been reviewed and approved by {doc_name} ({doc_license}). You can now view your approved patient care plan.",
                f"మీ కేర్ ప్లాన్ {doc_name} ({doc_license}) గారిచే సమీక్షించబడి ఆమోదించబడింది. మీరు ఇప్పుడు మీ ఆమోదించబడిన కేర్ ప్లాన్‌ను చూడవచ్చు.",
                current_ver,
                "APPROVED",
                "ఆమోదించబడింది",
                doc_name,
                doc_license,
                clean_comments or "Clinically certified by attending physician.",
                f"/?case_id={case_id}",
                now_iso,
                json.dumps({"case_id": case_id, "version": current_ver, "doctor_name": doc_name, "doctor_license": doc_license})
            ))
        else:
            cursor.execute("""
                INSERT INTO patient_notifications (
                    notification_id, case_id, patient_session_id, event_type,
                    title, title_te, message, message_te, case_version,
                    status_badge, status_badge_te, doctor_name, doctor_license, comments,
                    action_url, created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                notif_id, case_id, pat_sess, "CHANGES_REQUESTED",
                "Doctor Requested Changes",
                "వైద్యుడు మార్పులను అభ్యర్థించారు",
                f"Doctor {doc_name} noted: \"{clean_comments}\". Your care plan requires corrections before release.",
                f"వైద్యులు {doc_name} సూచన: \"{clean_comments}\". విడుదల చేయడానికి ముందు మీ కేర్ ప్లాన్ దిద్దుబాట్లు అవసరం.",
                current_ver,
                "CHANGES REQUESTED",
                "మార్పులు అభ్యర్థించబడ్డాయి",
                doc_name,
                doc_license,
                clean_comments,
                f"/doctor/case/{case_id}",
                now_iso,
                json.dumps({"case_id": case_id, "version": current_ver, "doctor_name": doc_name, "comments": clean_comments})
            ))

    return {
        "review_id": review_id,
        "case_id": case_id,
        "status": new_status,
        "version_reviewed": current_ver,
        "action": clean_action,
        "doctor_name": doc_name,
        "doctor_license": doc_license,
        "comments": clean_comments,
        "timestamp": now_iso
    }


# ---------------------------------------------------------------------------
# Audit Trail Logging
# ---------------------------------------------------------------------------

def _insert_audit_entry(
    cursor: sqlite3.Cursor,
    event_type: str,
    case_id: Optional[str] = None,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    timestamp: Optional[str] = None
) -> None:
    """Internal helper to insert an audit log record into an active cursor."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO audit_log (case_id, event_type, user_id, user_name, details, ip_address, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (
        case_id,
        event_type,
        user_id or "SYSTEM",
        user_name or "SYSTEM",
        details or "",
        ip_address or "127.0.0.1",
        ts
    ))


def log_audit_event(
    event_type: str,
    case_id: Optional[str] = None,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    user_type: str = "DOCTOR",
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    db_path: Optional[Path | str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> None:
    """Record an immutable event in the clinical audit log."""
    now_iso = datetime.now(timezone.utc).isoformat()
    uid = user_id or user_type
    uname = user_name or user_type
    try:
        if conn is not None:
            _insert_audit_entry(
                conn.cursor(),
                event_type=event_type,
                case_id=case_id,
                user_id=uid,
                user_name=uname,
                details=details,
                ip_address=ip_address,
                timestamp=now_iso
            )
        else:
            with get_db(db_path) as new_conn:
                _insert_audit_entry(
                    new_conn.cursor(),
                    event_type=event_type,
                    case_id=case_id,
                    user_id=uid,
                    user_name=uname,
                    details=details,
                    ip_address=ip_address,
                    timestamp=now_iso
                )
    except Exception as e:
        logger.error(f"Failed to record audit event {event_type}: {e}", exc_info=True)


def get_audit_logs(
    case_id: Optional[str] = None,
    limit: int = 50,
    db_path: Optional[Path | str] = None
) -> List[Dict[str, Any]]:
    """Retrieve audit log entries for a case or globally."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        if case_id:
            cursor.execute("""
                SELECT id, case_id, event_type, user_id, user_name, details, ip_address, timestamp
                FROM audit_log
                WHERE case_id = ?
                ORDER BY id DESC
                LIMIT ?;
            """, (case_id, limit))
        else:
            cursor.execute("""
                SELECT id, case_id, event_type, user_id, user_name, details, ip_address, timestamp
                FROM audit_log
                ORDER BY id DESC
                LIMIT ?;
            """, (limit,))
        return [dict(r) for r in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Patient Notifications & Case Activity History
# ---------------------------------------------------------------------------

def get_patient_notifications(
    patient_session_id: Optional[str] = None,
    case_ids: Optional[List[str]] = None,
    limit: int = 50,
    db_path: Optional[Path | str] = None
) -> List[Dict[str, Any]]:
    """Retrieve chronological notifications for a patient session or list of case IDs."""
    conditions = []
    params: List[Any] = []

    if patient_session_id:
        conditions.append("patient_session_id = ?")
        params.append(patient_session_id)

    if case_ids:
        clean_ids = [cid.strip() for cid in case_ids if cid and cid.strip()]
        if clean_ids:
            placeholders = ",".join("?" for _ in clean_ids)
            conditions.append(f"case_id IN ({placeholders})")
            params.extend(clean_ids)

    if not conditions:
        return []

    where_clause = f"WHERE {' OR '.join(conditions)}"

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT id, notification_id, case_id, patient_session_id, event_type,
                   title, title_te, message, message_te, case_version,
                   status_badge, status_badge_te, doctor_name, doctor_license,
                   comments, action_url, created_at, read_at, metadata_json
            FROM patient_notifications
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ?;
        """, params + [limit])
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_patient_notification_by_id(
    notification_id: str,
    db_path: Optional[Path | str] = None
) -> Optional[Dict[str, Any]]:
    """Retrieve single notification by its unique ID."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, notification_id, case_id, patient_session_id, event_type,
                   title, title_te, message, message_te, case_version,
                   status_badge, status_badge_te, doctor_name, doctor_license,
                   comments, action_url, created_at, read_at, metadata_json
            FROM patient_notifications
            WHERE notification_id = ?;
        """, (notification_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def mark_patient_notification_read(
    notification_id: str,
    db_path: Optional[Path | str] = None
) -> bool:
    """Mark a notification as read."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE patient_notifications
            SET read_at = ?
            WHERE notification_id = ? AND read_at IS NULL;
        """, (now_iso, notification_id))
        return cursor.rowcount > 0
