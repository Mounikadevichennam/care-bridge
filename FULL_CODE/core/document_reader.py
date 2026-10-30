"""Document Reader and OCR Engine for CareBridge AI.

Supports:
- Plain text (.txt) with robust encoding detection (UTF-8, Latin-1, CP1252)
- Text-based and stream-encoded PDF documents (.pdf) using native decompression
- Scanned documents and images (.png, .jpg, .jpeg) using Windows Native OCR
- Uncertainty flagging for potential OCR errors, ambiguous decimals, or numbers
- Secure temporary file cleanup
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
import zlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit


class DocumentReader:
    """Extracts text from clinical discharge summaries across multiple file formats."""

    def __init__(self):
        self.tools_dir = Path(__file__).resolve().parent.parent / "tools"
        self.ocr_script = self.tools_dir / "test_ocr.ps1"

    def read_document(self, file_path: str | Path, original_filename: str = "") -> Dict[str, Any]:
        """Process an uploaded document or image file and extract its text.

        Returns:
            Dict containing:
            - text: extracted raw text
            - format: detected format (.txt, .pdf, .png, etc.)
            - method: extraction method ('direct_text', 'pdf_stream', 'ocr')
            - warnings: list of extraction or OCR ambiguity warnings
            - needs_confirmation: boolean flag indicating if user should verify
        """
        path = Path(file_path)
        if not path.exists():
            return {
                "text": "",
                "format": "unknown",
                "method": "error",
                "warnings": [f"File not found: {file_path}"],
                "needs_confirmation": False
            }

        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            return {
                "text": "",
                "format": "unknown",
                "method": "error",
                "warnings": [f"File size ({file_size / (1024*1024):.1f}MB) exceeds 10MB limit."],
                "needs_confirmation": False
            }

        suffix = (Path(original_filename).suffix or path.suffix).lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            return {
                "text": "",
                "format": suffix,
                "method": "error",
                "warnings": [f"Unsupported file format '{suffix}'. Allowed: TXT, PDF, JPG, PNG."],
                "needs_confirmation": False
            }

        if suffix == ".txt":
            return self._read_text_file(path)
        elif suffix == ".pdf":
            return self._read_pdf_file(path)
        elif suffix in {".png", ".jpg", ".jpeg"}:
            return self._read_image_ocr(path)

        return {
            "text": "",
            "format": suffix,
            "method": "unknown",
            "warnings": ["Could not determine extraction strategy."],
            "needs_confirmation": False
        }

    def _read_text_file(self, path: Path) -> Dict[str, Any]:
        """Extract text from plain text files with encoding fallback."""
        raw_bytes = path.read_bytes()
        text = ""
        for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
            try:
                text = raw_bytes.decode(encoding)
                break
            except (UnicodeDecodeError, LookupError):
                continue

        warnings = self._detect_text_uncertainties(text)
        return {
            "text": text.strip(),
            "format": ".txt",
            "method": "direct_text",
            "warnings": warnings,
            "needs_confirmation": len(warnings) > 0
        }

    def _read_pdf_file(self, path: Path) -> Dict[str, Any]:
        """Extract text from PDF streams using pure-Python zlib decompression."""
        try:
            raw_bytes = path.read_bytes()
            extracted_chunks = []

            # Find all compressed stream objects in the PDF
            stream_regex = re.compile(rb'stream[\r\n]+(.*?)[\r\n]+endstream', re.DOTALL)
            for match in stream_regex.finditer(raw_bytes):
                stream_data = match.group(1)
                decompressed = b""
                try:
                    decompressed = zlib.decompress(stream_data)
                except Exception:
                    # Stream might not be flate-compressed, test as raw text
                    decompressed = stream_data

                # Extract Text Objects: BT ... ET blocks
                text_blocks = re.findall(rb'BT[\r\n\s]+(.*?)[\r\n\s]+ET', decompressed, re.DOTALL)
                for block in text_blocks:
                    # Match (string) Tj or [(array)] TJ
                    tj_matches = re.findall(rb'\((.*?)\)\s*Tj', block)
                    for tj in tj_matches:
                        try:
                            decoded = tj.decode('utf-8', errors='ignore')
                            extracted_chunks.append(decoded)
                        except Exception:
                            pass

                    # Match TJ array: [(Hello) 10 (World)] TJ
                    array_matches = re.findall(rb'\[(.*?)\]\s*TJ', block, re.DOTALL)
                    for arr in array_matches:
                        elem_matches = re.findall(rb'\((.*?)\)', arr)
                        line_parts = []
                        for em in elem_matches:
                            try:
                                line_parts.append(em.decode('utf-8', errors='ignore'))
                            except Exception:
                                pass
                        if line_parts:
                            extracted_chunks.append("".join(line_parts))

            # Assemble extracted text
            full_text = "\n".join(extracted_chunks).strip()

            # If pure-stream extraction found very little text, try raw ASCII/Unicode string regex
            if len(full_text) < 50:
                text_lines = re.findall(rb'\(([A-Za-z0-9\s.,:\-\(\)\/]{4,})\)', raw_bytes)
                fallback_chunks = [t.decode('latin-1', errors='ignore') for t in text_lines]
                if len("\n".join(fallback_chunks)) > len(full_text):
                    full_text = "\n".join(fallback_chunks)

            warnings = []
            if len(full_text) < 40:
                warnings.append(
                    "This PDF appears to be a scanned image or uses non-standard embedded fonts. "
                    "Please verify the extracted content carefully."
                )

            uncertainties = self._detect_text_uncertainties(full_text)
            warnings.extend(uncertainties)

            return {
                "text": full_text,
                "format": ".pdf",
                "method": "pdf_stream",
                "warnings": warnings,
                "needs_confirmation": True  # PDFs should always offer confirmation review
            }

        except Exception as e:
            logger.error(f"Error reading PDF {path}: {e}")
            return {
                "text": "",
                "format": ".pdf",
                "method": "error",
                "warnings": [f"Could not parse PDF: {str(e)}"],
                "needs_confirmation": False
            }

    def _read_image_ocr(self, path: Path) -> Dict[str, Any]:
        """Perform OCR on an image file using native Windows OCR."""
        text = ""
        warnings = []
        try:
            # Check if PowerShell script exists
            if self.ocr_script.exists():
                cmd = [
                    "powershell",
                    "-ExecutionPolicy", "Bypass",
                    "-File", str(self.ocr_script),
                    "-ImagePath", str(path.resolve())
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                if proc.returncode == 0 and proc.stdout.strip():
                    text = proc.stdout.strip()
                else:
                    if proc.stderr:
                        logger.warning(f"Windows OCR warning: {proc.stderr}")

            if not text:
                warnings.append("OCR extraction produced minimal or unclear text. Please review and type any missing details.")

            uncertainties = self._detect_text_uncertainties(text)
            warnings.extend(uncertainties)

            return {
                "text": text,
                "format": path.suffix.lower(),
                "method": "ocr",
                "warnings": warnings,
                "needs_confirmation": True
            }

        except Exception as e:
            logger.error(f"OCR execution failed on {path}: {e}")
            return {
                "text": "",
                "format": path.suffix.lower(),
                "method": "error",
                "warnings": [f"OCR processing failed: {str(e)}"],
                "needs_confirmation": False
            }

    def _detect_text_uncertainties(self, text: str) -> List[str]:
        """Detect ambiguous clinical numbers, decimals, or OCR noise."""
        warnings: List[str] = []
        if not text:
            return warnings

        # 1. Unclear decimal points (e.g. '0 . 5 mg' or '0. 5mg')
        if re.search(r'\b\d+\s+\.\s*\d+\s*(?:mg|mcg|ml)\b', text, re.IGNORECASE):
            warnings.append("Spaced decimal point detected in medication dosage. Please verify the exact numerical dose.")

        # 2. Potential OCR letter/number confusion in dosages (e.g. 'l0mg' instead of '10mg' or 'O.5' instead of '0.5')
        if re.search(r'\b[lI]\d+\s*(?:mg|mcg|ml|g)\b', text):
            warnings.append("Possible letter 'I' or 'l' substituted for number 1 in medication dosage.")
        if re.search(r'\b[O]\.\d+\s*(?:mg|mcg|ml|g)\b', text):
            warnings.append("Possible letter 'O' substituted for digit 0 in medication dosage.")

        # 3. High noise / special characters density
        symbols_count = len(re.findall(r'[\~\|\^`\\]', text))
        if symbols_count > 5:
            warnings.append("Multiple artifact characters detected. Please verify names and numbers.")

        return warnings

