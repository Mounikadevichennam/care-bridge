"""CareBridge AI — Flask Web Application.

Converts clinical discharge summaries into patient-understandable care plans.
Provides integrated Doctor Review Portal with role-based authentication,
case comparison, clinical sign-off, and persistent audit trail.
"""
from __future__ import annotations

import json
import logging
import os
import re
from functools import wraps
from pathlib import Path
from typing import Optional, Dict, Any

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    flash,
    make_response,
    Response
)

import secrets

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max upload for docs/images
# Cryptographically secure random secret key with optional environment override
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


# ---------------------------------------------------------------------------
# CSRF Protection Helpers
# ---------------------------------------------------------------------------

def generate_csrf_token() -> str:
    """Generate or retrieve a per-session cryptographic CSRF token."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(16)
    return session['_csrf_token']


app.jinja_env.globals['csrf_token'] = generate_csrf_token


def verify_csrf() -> bool:
    """Validate CSRF token for state-changing HTTP requests."""
    if app.config.get('TESTING') or app.config.get('WTF_CSRF_ENABLED') is False:
        return True
    token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
    expected = session.get('_csrf_token')
    if not expected or token != expected:
        return False
    return True

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import dataset provider
from core.dataset import (
    get_data_dir,
    get_summaries_file,
    get_abbreviation_glossary_file,
    get_drug_reference_file,
)

# Import database & audit trail engine
from core.database import (
    init_db,
    authenticate_doctor,
    get_doctor_by_id,
    save_case_care_plan,
    get_case,
    list_cases,
    get_dashboard_stats,
    submit_doctor_review,
    log_audit_event,
    get_audit_logs,
    get_patient_notifications,
    get_patient_notification_by_id,
    mark_patient_notification_read,
)

# Canonical organizer data directory
try:
    DATA_DIR = get_data_dir()
    logger.info("Organizer dataset loaded from: %s", DATA_DIR)
except FileNotFoundError:
    DATA_DIR = Path(__file__).resolve().parent / "data"
    logger.warning(
        "Organizer dataset unavailable. Using built-in clinical references. "
        "Sample summaries will be unavailable."
    )
# Initialize SQLite database schema and default doctors
init_db()


# ---------------------------------------------------------------------------
# Authentication Helper & Decorator
# ---------------------------------------------------------------------------

def doctor_required(f):
    """Decorator ensuring only authenticated doctors can access clinical routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'doctor_id' not in session:
            if request.is_json or request.path.startswith('/api/doctor'):
                return jsonify({'error': 'Unauthorized: Clinician authentication required.'}), 401
            return redirect(url_for('doctor_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def get_current_doctor() -> Optional[Dict[str, Any]]:
    """Retrieve logged-in doctor profile from session."""
    if 'doctor_id' not in session:
        return None
    return {
        'id': session['doctor_id'],
        'name': session.get('doctor_name', 'Doctor'),
        'email': session.get('doctor_email', ''),
        'license_number': session.get('doctor_license', ''),
        'department': session.get('doctor_department', '')
    }


# ---------------------------------------------------------------------------
# Patient Portal Routes
# ---------------------------------------------------------------------------

def get_sample_summaries() -> list[dict]:
    """Load sample summaries for the demo selector.

    Returns:
        A list of dicts with ``id`` and ``preview`` keys for each sample
        discharge summary available in the data directory.
    """
    samples: list[dict] = []
    summaries_file = DATA_DIR / "summaries.jsonl"
    if summaries_file.exists():
        with open(summaries_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    # Only include first 10 for demo
                    samples.append({
                        'id': record['summary_id'],
                        'preview': record['text'][:150] + '...'
                    })
                    if len(samples) >= 10:
                        break
    return samples


@app.route('/')
def index():
    """Render the main application page."""
    samples = get_sample_summaries()
    return render_template('index.html', samples=samples, current_doctor=get_current_doctor())


@app.route('/api/samples', methods=['GET'])
def get_samples_list():
    """API endpoint returning available sample summaries list."""
    return jsonify(get_sample_summaries())


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle document and image uploads (.txt, .pdf, .png, .jpg, .jpeg).

    Extracts text using DocumentReader, cleans up temporary files,
    and returns extracted text with OCR/parsing warnings for user confirmation.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in upload request'}), 400

    uploaded_file = request.files['file']
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({'error': 'No selected file'}), 400

    filename = uploaded_file.filename
    suffix = Path(filename).suffix.lower()
    allowed_suffixes = {'.txt', '.pdf', '.png', '.jpg', '.jpeg'}

    if suffix not in allowed_suffixes:
        return jsonify({
            'error': f"Unsupported file type '{suffix}'. Please upload a TXT, PDF, JPG, or PNG document."
        }), 400

    import tempfile
    from core.document_reader import DocumentReader

    temp_path = None
    try:
        # Create a safe temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = Path(tmp.name)
            uploaded_file.save(str(temp_path))

        reader = DocumentReader()
        result = reader.read_document(temp_path, original_filename=filename)
        result['filename'] = filename
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error handling file upload {filename}: {e}", exc_info=True)
        return jsonify({'error': f"Failed to process document: {str(e)}"}), 500

    finally:
        # Always remove temporary uploaded file
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_path}: {e}")


def get_patient_session_id() -> str:
    """Retrieve or establish an anonymous secure patient session token."""
    if 'patient_session_id' not in session:
        session['patient_session_id'] = f"PAT-{secrets.token_hex(8).upper()}"
    return session['patient_session_id']


@app.route('/api/process', methods=['POST'])
def process_summary():
    """Process a discharge summary and return the care plan.

    Clinical Protocol & Strict Server-Side Safety:
    - Extracts clinical facts, generates preliminary draft, runs faithfulness audit.
    - Persists case in SQLite with status PENDING.
    - If caller is an authenticated doctor: returns full case result for review.
    - If caller is unauthenticated/patient: does NOT expose preliminary care plan.
      Returns case_id, status PENDING, and redirect_url to Doctor Portal.
    """
    try:
        data = request.get_json(silent=True)
        if not data or 'text' not in data:
            return jsonify({'error': 'No discharge summary text provided'}), 400

        raw_text = data.get('text')
        if not isinstance(raw_text, str):
            return jsonify({'error': 'Discharge summary text must be a string'}), 400
        summary_text = raw_text.strip()
        if not summary_text:
            return jsonify({'error': 'Empty discharge summary text'}), 400

        if len(summary_text) > 50000:
            return jsonify({'error': 'Summary text exceeds maximum length (50,000 characters)'}), 400

        summary_id = data.get('summary_id', 'USER-INPUT')

        # Import here to allow app to start even if core modules have issues
        from core.care_plan import CarePlanProcessor

        processor = CarePlanProcessor(
            abbreviation_path=str(DATA_DIR / "abbreviation_glossary.csv"),
            drug_reference_path=str(DATA_DIR / "drug_reference.csv")
        )

        result = processor.process(summary_id, summary_text)

        # Automatically persist case to database with PENDING review status
        pat_sess = get_patient_session_id()
        case_info = save_case_care_plan(
            summary_id=summary_id,
            original_text=summary_text,
            care_plan_result=result,
            patient_session_id=pat_sess,
            ip_address=request.remote_addr
        )

        case_id = case_info["case_id"]
        status = case_info["status"]
        version = case_info["version"]

        is_doctor = ('doctor_id' in session)

        if is_doctor:
            result["case_id"] = case_id
            result["doctor_review_status"] = status
            result["status"] = status
            result["case_version"] = version
            result["patient_session_id"] = pat_sess
            full_case = get_case(case_id)
            if full_case:
                result["approval_info"] = full_case.get("approval_info")
                result["latest_change_request"] = full_case.get("latest_change_request")
            return jsonify(result)

        # Patient / unauthenticated caller:
        # Mandatory Clinical Protocol: Do NOT expose preliminary care plan to patient interface!
        # Return case_id, status PENDING, redirect instruction, and patient session token.
        return jsonify({
            "success": True,
            "case_id": case_id,
            "summary_id": summary_id,
            "status": "PENDING",
            "doctor_review_status": "PENDING",
            "case_version": version,
            "patient_session_id": pat_sess,
            "message": "Care plan draft generated and queued for mandatory physician review. Release to patient requires doctor approval.",
            "redirect_url": f"/doctor/login?next=/doctor/case/{case_id}"
        })

    except Exception as e:
        logger.error(f"Error processing summary: {e}", exc_info=True)
        return jsonify({'error': f'Processing error: {str(e)}'}), 500


@app.route('/api/sample/<summary_id>')
def get_sample(summary_id: str):
    """Get a sample discharge summary by ID.

    Args:
        summary_id: The unique identifier of the sample summary to retrieve.
    """
    try:
        summaries_file = DATA_DIR / "summaries.jsonl"
        if summaries_file.exists():
            with open(summaries_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        if record['summary_id'] == summary_id:
                            return jsonify(record)
        return jsonify({'error': 'Summary not found'}), 404
    except Exception as e:
        logger.error(f"Error loading sample: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/case/<case_id>', methods=['GET'])
def api_get_case(case_id: str):
    """Retrieve full case details, care plan, and doctor review status by case ID.

    Strict Server-Side Access Control:
    - If user is an authenticated doctor: returns full case data.
    - If case is APPROVED: returns the approved patient care plan.
    - If case is PENDING or CHANGES_REQUESTED: rejects unapproved patient access with HTTP 403.
    """
    case_data = get_case(case_id)
    if not case_data:
        return jsonify({'error': f"Case '{case_id}' not found"}), 404

    is_doctor = ('doctor_id' in session)
    status = case_data.get('status', 'PENDING')

    if not is_doctor and status != 'APPROVED':
        return jsonify({
            'error': 'Forbidden: Care plan is awaiting mandatory physician review.',
            'case_id': case_id,
            'status': status,
            'doctor_review_status': status,
            'is_approved': False,
            'message': 'Care plan pending doctor review. Patient distribution is blocked until physician certification.',
            'latest_change_request': case_data.get('latest_change_request')
        }), 403

    return jsonify(case_data)


# ---------------------------------------------------------------------------
# Patient Notifications & Case Activity History Endpoints
# ---------------------------------------------------------------------------

@app.route('/api/patient/notifications', methods=['GET'])
def api_get_patient_notifications():
    """Retrieve persistent activity notifications for the current patient session or cases."""
    pat_sess = get_patient_session_id()
    case_ids_param = request.args.get('case_ids', '').strip()
    case_ids = [c.strip() for c in case_ids_param.split(',') if c.strip()] if case_ids_param else None

    notifs = get_patient_notifications(
        patient_session_id=pat_sess,
        case_ids=case_ids,
        limit=50
    )
    unread = sum(1 for n in notifs if not n.get('read_at'))
    return jsonify({
        'success': True,
        'patient_session_id': pat_sess,
        'notifications': notifs,
        'total': len(notifs),
        'unread_count': unread
    })


@app.route('/api/patient/notifications/<notification_id>', methods=['GET'])
def api_get_patient_notification(notification_id: str):
    """Retrieve single patient notification by ID."""
    notif = get_patient_notification_by_id(notification_id)
    if not notif:
        return jsonify({'error': 'Notification not found'}), 404
    return jsonify(notif)


@app.route('/api/patient/notifications/<notification_id>/read', methods=['POST'])
def api_mark_patient_notification_read(notification_id: str):
    """Mark a patient notification as read."""
    success = mark_patient_notification_read(notification_id)
    return jsonify({'success': success, 'notification_id': notification_id})


@app.route('/api/validate', methods=['POST'])
def validate_output():
    """Run faithfulness validation on a processed care plan.

    Expects JSON body with ``source_text``, ``care_plan_data``,
    ``english_plan``, and ``telugu_plan``.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        from core.validator import FaithfulnessValidator

        validator = FaithfulnessValidator()
        report = validator.validate(
            source_text=data.get('source_text', ''),
            care_plan_data=data.get('care_plan_data', {}),
            english_plan=data.get('english_plan', ''),
            telugu_plan=data.get('telugu_plan', '')
        )

        return jsonify(report)
    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Direct Export Routes (PDF & PNG)
# ---------------------------------------------------------------------------

@app.route('/api/export/pdf', methods=['POST'])
@app.route('/api/export/pdf/<case_id>', methods=['GET'])
def export_care_plan_pdf(case_id: Optional[str] = None):
    """Directly generate and download an A4 PDF care plan in English or Telugu.

    Strict Server-Side Access Control:
    - Rejects unapproved cases (PENDING or CHANGES_REQUESTED) with HTTP 403.
    - Never trusts client-submitted JSON to bypass approval; always fetches verified DB record.
    """
    try:
        from core.exporter import generate_care_plan_pdf

        lang = request.args.get('lang', 'en').lower()
        plan_data = None

        if request.method == 'POST':
            req_data = request.get_json(silent=True) or {}
            lang = req_data.get('lang', lang)
            if not case_id:
                case_id = req_data.get('case_id')
                if not case_id and 'care_plan_data' in req_data:
                    case_id = req_data['care_plan_data'].get('case_id')

        # In testing mode: allow mock care plan data if marked APPROVED
        if app.config.get('TESTING') and request.method == 'POST':
            req_data = request.get_json(silent=True) or {}
            test_data = req_data.get('care_plan_data') or req_data.get('data')
            if test_data:
                if test_data.get('doctor_review_status') != 'APPROVED':
                    return jsonify({'error': 'Forbidden: Care plan must be approved by an attending physician before export.'}), 403
                plan_data = test_data

        # Otherwise look up verified case from SQLite database
        if not plan_data and case_id:
            try:
                c = get_case(case_id)
            except Exception:
                c = None

            if c:
                if c.get('status') != 'APPROVED':
                    return jsonify({
                        'error': 'Forbidden: Care plan must be approved by an attending physician before export.',
                        'status': c.get('status'),
                        'case_id': c.get('id')
                    }), 403

                plan_data = c.get('care_plan_data') or {}
                plan_data['case_id'] = c.get('id')
                plan_data['doctor_review_status'] = c.get('status')
                plan_data['approval_info'] = c.get('approval_info')
        elif not plan_data:
            return jsonify({'error': 'Valid approved case_id required for export.'}), 400

        if not plan_data:
            return jsonify({'error': 'No care plan data available for export.'}), 404

        pdf_bytes = generate_care_plan_pdf(plan_data, lang=lang)
        summary_id = plan_data.get('summary_id') or plan_data.get('case_id') or 'CAREPLAN'
        clean_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(summary_id))

        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="CareBridge_Care_Plan_{clean_id}_{lang}.pdf"'
        return response

    except Exception as e:
        logger.error(f"Error exporting PDF: {e}", exc_info=True)
        return jsonify({'error': f"Failed to export PDF: {str(e)}"}), 500


@app.route('/api/export/image', methods=['POST'])
@app.route('/api/export/image/<case_id>', methods=['GET'])
def export_care_plan_image(case_id: Optional[str] = None):
    """Directly generate and download a crisp PNG image of the care plan in English or Telugu.

    Strict Server-Side Access Control:
    - Rejects unapproved cases (PENDING or CHANGES_REQUESTED) with HTTP 403.
    - Never trusts client-submitted JSON to bypass approval; always fetches verified DB record.
    """
    try:
        from core.exporter import generate_care_plan_image

        lang = request.args.get('lang', 'en').lower()
        plan_data = None

        if request.method == 'POST':
            req_data = request.get_json(silent=True) or {}
            lang = req_data.get('lang', lang)
            if not case_id:
                case_id = req_data.get('case_id')
                if not case_id and 'care_plan_data' in req_data:
                    case_id = req_data['care_plan_data'].get('case_id')

        # In testing mode: allow mock care plan data if marked APPROVED
        if app.config.get('TESTING') and request.method == 'POST':
            req_data = request.get_json(silent=True) or {}
            test_data = req_data.get('care_plan_data') or req_data.get('data')
            if test_data:
                if test_data.get('doctor_review_status') != 'APPROVED':
                    return jsonify({'error': 'Forbidden: Care plan must be approved by an attending physician before export.'}), 403
                plan_data = test_data

        # Otherwise look up verified case from SQLite database
        if not plan_data and case_id:
            try:
                c = get_case(case_id)
            except Exception:
                c = None

            if c:
                if c.get('status') != 'APPROVED':
                    return jsonify({
                        'error': 'Forbidden: Care plan must be approved by an attending physician before export.',
                        'status': c.get('status'),
                        'case_id': c.get('id')
                    }), 403

                plan_data = c.get('care_plan_data') or {}
                plan_data['case_id'] = c.get('id')
                plan_data['doctor_review_status'] = c.get('status')
                plan_data['approval_info'] = c.get('approval_info')
        elif not plan_data:
            return jsonify({'error': 'Valid approved case_id required for export.'}), 400

        if not plan_data:
            return jsonify({'error': 'No care plan data available for export.'}), 404

        img_bytes = generate_care_plan_image(plan_data, lang=lang)
        summary_id = plan_data.get('summary_id') or plan_data.get('case_id') or 'CAREPLAN'
        clean_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(summary_id))

        response = make_response(img_bytes)
        response.headers['Content-Type'] = 'image/png'
        response.headers['Content-Disposition'] = f'attachment; filename="CareBridge_Care_Plan_{clean_id}_{lang}.png"'
        return response

    except Exception as e:
        logger.error(f"Error exporting Image: {e}", exc_info=True)
        return jsonify({'error': f"Failed to export Image: {str(e)}"}), 500


# ---------------------------------------------------------------------------
# Doctor Clinical Portal Routes
# ---------------------------------------------------------------------------

@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    """Doctor login page and credential authentication."""
    if request.method == 'GET':
        if 'doctor_id' in session:
            next_url = request.args.get('next', '')
            if next_url and next_url.startswith('/doctor'):
                return redirect(next_url)
            return redirect(url_for('doctor_dashboard'))
        next_url = request.args.get('next', '')
        message = request.args.get('message', '')
        return render_template('doctor_login.html', next_url=next_url, message=message)

    if not verify_csrf():
        return render_template(
            'doctor_login.html',
            error="CSRF verification failed. Please try again.",
            next_url=request.form.get('next', '')
        ), 400

    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    next_url = request.form.get('next', '').strip()

    doc = authenticate_doctor(email, password)
    if not doc:
        log_audit_event(
            event_type="LOGIN_FAILED",
            user_id=email,
            user_name="ANONYMOUS",
            details=f"Invalid doctor login attempt for {email}",
            ip_address=request.remote_addr
        )
        return render_template(
            'doctor_login.html',
            error="Invalid email or password. Please verify your hospital credentials.",
            email=email,
            next_url=next_url
        ), 401

    # Establish session
    session['doctor_id'] = doc['id']
    session['doctor_name'] = doc['name']
    session['doctor_email'] = doc['email']
    session['doctor_license'] = doc['license_number']
    session['doctor_department'] = doc['department']

    log_audit_event(
        event_type="DOCTOR_LOGIN",
        user_id=str(doc['id']),
        user_name=doc['name'],
        details=f"Doctor logged in successfully: {doc['name']} ({doc['license_number']})",
        ip_address=request.remote_addr
    )

    if next_url and next_url.startswith('/doctor'):
        return redirect(next_url)
    return redirect(url_for('doctor_dashboard'))


@app.route('/doctor/logout')
def doctor_logout():
    """Terminate doctor session and record audit event."""
    doc_id = session.get('doctor_id')
    doc_name = session.get('doctor_name')
    if doc_id:
        log_audit_event(
            event_type="DOCTOR_LOGOUT",
            user_id=str(doc_id),
            user_name=doc_name,
            details=f"Doctor logged out: {doc_name}",
            ip_address=request.remote_addr
        )
    session.clear()
    return redirect(url_for('doctor_login', message="You have been safely logged out of the Doctor Portal."))


@app.route('/doctor')
@app.route('/doctor/dashboard')
@doctor_required
def doctor_dashboard():
    """Display doctor dashboard with live review queue, KPI statistics, and filter options."""
    doctor = get_current_doctor()
    status_filter = request.args.get('status', 'ALL').strip().upper()
    search_query = request.args.get('q', '').strip()

    cases, total_count = list_cases(status=status_filter, query=search_query)
    stats = get_dashboard_stats()

    return render_template(
        'doctor_dashboard.html',
        doctor=doctor,
        cases=cases,
        stats=stats,
        total_cases=total_count,
        current_status=status_filter,
        search_query=search_query
    )


@app.route('/doctor/case/<case_id>')
@doctor_required
def doctor_case_view(case_id: str):
    """Side-by-side case comparison between verbatim discharge summary and generated plan."""
    doctor = get_current_doctor()
    case_data = get_case(case_id)
    if not case_data:
        return redirect(url_for('doctor_dashboard'))

    return render_template('doctor_case_review.html', doctor=doctor, case=case_data)


@app.route('/doctor/case/<case_id>/review', methods=['POST'])
@doctor_required
def doctor_submit_review_action(case_id: str):
    """Process doctor decision: approve or request changes."""
    doctor = get_current_doctor()
    if not verify_csrf():
        case_data = get_case(case_id)
        return render_template('doctor_case_review.html', doctor=doctor, case=case_data, error="CSRF validation failed."), 400

    action = request.form.get('action', '').strip().upper()
    comments = request.form.get('comments', '').strip()

    try:
        result = submit_doctor_review(
            case_id=case_id,
            doctor_id=doctor['id'],
            action=action,
            comments=comments,
            ip_address=request.remote_addr
        )
        case_data = get_case(case_id)
        action_word = "approved for release" if action == "APPROVE" else "marked with changes requested"
        msg = f"Care plan {action_word} by {doctor['name']}."
        return render_template('doctor_case_review.html', doctor=doctor, case=case_data, success_msg=msg)

    except Exception as e:
        logger.error(f"Error submitting review for case {case_id}: {e}", exc_info=True)
        case_data = get_case(case_id)
        return render_template('doctor_case_review.html', doctor=doctor, case=case_data, error=str(e)), 400


@app.route('/doctor/case/<case_id>/resubmit', methods=['POST'])
@doctor_required
def doctor_resubmit_case(case_id: str):
    """Generate a new care plan version from updated discharge text.

    Status resets to PENDING and requires fresh doctor approval.
    """
    doctor = get_current_doctor()
    if not verify_csrf():
        case_data = get_case(case_id)
        return render_template('doctor_case_review.html', doctor=doctor, case=case_data, error="CSRF validation failed."), 400

    revised_text = request.form.get('revised_text', '').strip()
    if not revised_text:
        case_data = get_case(case_id)
        return render_template('doctor_case_review.html', doctor=doctor, case=case_data, error="Revised summary text cannot be empty."), 400

    try:
        from core.care_plan import CarePlanProcessor
        case_data = get_case(case_id)
        summary_id = case_data.get('summary_id', 'USER-INPUT') if case_data else 'USER-INPUT'

        processor = CarePlanProcessor(
            abbreviation_path=str(DATA_DIR / "abbreviation_glossary.csv"),
            drug_reference_path=str(DATA_DIR / "drug_reference.csv")
        )
        new_result = processor.process(summary_id, revised_text)

        updated_info = save_case_care_plan(
            summary_id=summary_id,
            original_text=revised_text,
            care_plan_result=new_result,
            case_id=case_id,
            ip_address=request.remote_addr
        )

        msg = f"Generated revised care plan version v{updated_info['version']}. Status reset to PENDING for clinical certification."
        updated_case = get_case(case_id)
        return render_template('doctor_case_review.html', doctor=doctor, case=updated_case, success_msg=msg)

    except Exception as e:
        logger.error(f"Error resubmitting case {case_id}: {e}", exc_info=True)
        case_data = get_case(case_id)
        return render_template('doctor_case_review.html', doctor=doctor, case=case_data, error=str(e)), 400


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
