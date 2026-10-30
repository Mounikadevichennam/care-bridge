"""CareBridge AI — Flask Web Application.

Converts clinical discharge summaries into patient-understandable care plans.
"""
import json
import logging
import os
from pathlib import Path

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max upload for docs/images

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

# Canonical organizer data directory
DATA_DIR = get_data_dir()


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
    return render_template('index.html', samples=samples)


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


@app.route('/api/process', methods=['POST'])
def process_summary():
    """Process a discharge summary and return the care plan.

    Expects JSON body with ``text`` (required) and optional ``summary_id``.
    Returns a JSON object containing extracted facts, English and Telugu
    care plans, faithfulness report, readability metrics, and fridge-sheet
    data.
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No discharge summary text provided'}), 400

        summary_text = data['text'].strip()
        if not summary_text:
            return jsonify({'error': 'Empty discharge summary text'}), 400

        if len(summary_text) > 50000:
            return jsonify({'error': 'Summary text exceeds maximum length'}), 400

        summary_id = data.get('summary_id', 'USER-INPUT')

        # Import here to allow app to start even if core modules have issues
        from core.care_plan import CarePlanProcessor

        processor = CarePlanProcessor(
            abbreviation_path=str(DATA_DIR / "abbreviation_glossary.csv"),
            drug_reference_path=str(DATA_DIR / "drug_reference.csv")
        )

        result = processor.process(summary_id, summary_text)

        return jsonify(result)

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


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
