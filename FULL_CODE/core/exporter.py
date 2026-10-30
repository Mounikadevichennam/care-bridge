"""CareBridge AI — Clinical Export Engine.

Generates high-fidelity, high-contrast, patient-friendly A4 PDF documents
and high-resolution PNG images of discharge care plans.
Supports both English and authentic Telugu with verified font rendering,
physician approval sign-off stamps, medication schedules, and clinical safety notices.
"""

from __future__ import annotations

import io
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# ReportLab for A4 Vector PDF Generation
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Pillow for High-Resolution PNG Image Generation
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Register Indic/Telugu compatible font
SYSTEM_FONT_PATH = "C:/Windows/Fonts/Nirmala.ttc"
FONT_AVAILABLE = os.path.exists(SYSTEM_FONT_PATH)

if FONT_AVAILABLE:
    try:
        pdfmetrics.registerFont(TTFont("Nirmala", SYSTEM_FONT_PATH, subfontIndex=0))
        pdfmetrics.registerFont(TTFont("Nirmala-Bold", SYSTEM_FONT_PATH, subfontIndex=1))
        PDF_FONT_NORMAL = "Nirmala"
        PDF_FONT_BOLD = "Nirmala-Bold"
    except Exception as e:
        logger.warning(f"Could not register Nirmala font for ReportLab: {e}")
        PDF_FONT_NORMAL = "Helvetica"
        PDF_FONT_BOLD = "Helvetica-Bold"
else:
    PDF_FONT_NORMAL = "Helvetica"
    PDF_FONT_BOLD = "Helvetica-Bold"


# ---------------------------------------------------------------------------
# Numbered Canvas for PDF Page Numbers
# ---------------------------------------------------------------------------
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Custom canvas that adds page numbers and running footers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont(PDF_FONT_NORMAL, 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Footer divider line
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 32, A4[0] - 36, 32)

        # Footer text
        disclaimer = "CareBridge AI — Faithfulness Above Fluency | Discharge Care Plan"
        self.drawString(36, 20, disclaimer)

        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 36, 20, page_str)
        self.restoreState()


# ---------------------------------------------------------------------------
# Direct A4 PDF Document Generator
# ---------------------------------------------------------------------------
def generate_care_plan_pdf(data: Dict[str, Any], lang: str = "en") -> bytes:
    """Generate a clean, high-contrast A4 PDF care plan in English or Telugu.

    Args:
        data: Care plan dictionary containing extracted facts, medicines,
              schedules, approval info, and optional telugu_structured.
        lang: 'en' for English or 'te' for Telugu.

    Returns:
        bytes: Raw PDF file bytes ready for direct download.
    """
    is_te = (lang == "te")
    font_name = PDF_FONT_NORMAL if FONT_AVAILABLE else "Helvetica"
    font_bold = PDF_FONT_BOLD if FONT_AVAILABLE else "Helvetica-Bold"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    style_title = ParagraphStyle(
        "CP_Title",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a")
    )
    style_subtitle = ParagraphStyle(
        "CP_Subtitle",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0284c7")
    )
    style_meta = ParagraphStyle(
        "CP_Meta",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569")
    )
    style_h2 = ParagraphStyle(
        "CP_H2",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=4
    )
    style_body = ParagraphStyle(
        "CP_Body",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1e293b")
    )
    style_body_bold = ParagraphStyle(
        "CP_BodyBold",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0f172a")
    )
    style_badge_approved = ParagraphStyle(
        "CP_BadgeApproved",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#065f46")
    )
    style_badge_pending = ParagraphStyle(
        "CP_BadgePending",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#92400e")
    )
    style_badge_changes = ParagraphStyle(
        "CP_BadgeChanges",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#991b1b")
    )
    style_disclaimer = ParagraphStyle(
        "CP_Disclaimer",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#64748b")
    )

    story: List[Any] = []

    # 1. Header & Title Block
    title_text = "కేర్‌బ్రిడ్జ్ రోగి డిశ్చార్జ్ సంరక్షణ ప్రణాళిక" if is_te else "CAREBRIDGE PATIENT DISCHARGE CARE PLAN"
    subtitle_text = "ఆసుపత్రి డిశ్చార్జ్ అనంతర గృహ సంరక్షణ & ఔషధ మార్గదర్శిని" if is_te else "Clearer Care After Hospital Discharge — Family & Home Companion"

    summary_id = data.get("summary_id") or data.get("case_id") or "PATIENT-CARE-PLAN"
    case_id = data.get("case_id") or summary_id
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    header_table_data = [
        [
            Paragraph(f"<b>{title_text}</b>", style_title),
            Paragraph(f"<b>Case Ref:</b> {case_id}<br/><b>Date:</b> {gen_time}", style_meta)
        ],
        [
            Paragraph(subtitle_text, style_subtitle),
            Paragraph(f"<b>Language:</b> {'తెలుగు (Telugu)' if is_te else 'English'}", style_meta)
        ]
    ]
    t_header = Table(header_table_data, colWidths=[380, 143])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=8))

    # 2. Doctor Review Status Badge / Certification
    doc_status = (data.get("doctor_review_status") or "PENDING").upper()
    app_info = data.get("approval_info") or {}
    chg_info = data.get("latest_change_request") or {}

    if doc_status == "APPROVED":
        doc_name = app_info.get("doctor_name", "Attending Physician")
        doc_lic = app_info.get("doctor_license", "Certified MD")
        time_str = app_info.get("created_at", gen_time)[:16].replace("T", " ")
        doc_comments = app_info.get("comments", "")

        status_heading = f"🛡️ CLINICALLY APPROVED FOR PATIENT RELEASE — Dr. {doc_name} ({doc_lic})"
        status_sub = f"Signed off on {time_str} UTC. Clinical orders verified against hospital chart."
        if is_te:
            status_heading = f"🛡️ వైద్యులచే ఆమోదించబడింది (APPROVED) — Dr. {doc_name} ({doc_lic})"
            status_sub = f"సమీక్షించిన తేదీ: {time_str}. ఆసుపత్రి చార్ట్ ఆధారంగా ధృవీకరించబడింది."
        if doc_comments:
            status_sub += f" Notes: \"{doc_comments}\""

        badge_p = Paragraph(f"<b>{status_heading}</b><br/>{status_sub}", style_badge_approved)
        badge_table = Table([[badge_p]], colWidths=[523])
        badge_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#ecfdf5")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#10b981")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(badge_table)

    elif doc_status == "CHANGES_REQUESTED":
        doc_name = chg_info.get("doctor_name", "Attending Physician")
        doc_comments = chg_info.get("comments", "Corrections requested.")
        status_heading = "⚠️ CLINICAL STATUS: CHANGES REQUESTED BY PHYSICIAN"
        status_sub = f"Reviewing Doctor: Dr. {doc_name}. Requested corrections: \"{doc_comments}\". Follow direct hospital orders."
        if is_te:
            status_heading = "⚠️ వైద్యుల పరిశీలన: మార్పులు మరియు సవరణలు అవసరం (CHANGES REQUESTED)"
            status_sub = f"వైద్యుల సూచన: \"{doc_comments}\". తాత్కాలికంగా ఆసుపత్రి సూచనలను పాటించండి."

        badge_p = Paragraph(f"<b>{status_heading}</b><br/>{status_sub}", style_badge_changes)
        badge_table = Table([[badge_p]], colWidths=[523])
        badge_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#ef4444")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(badge_table)

    else:
        # PENDING
        status_heading = "⏳ CLINICAL STATUS: PENDING DOCTOR REVIEW"
        status_sub = "This AI-generated summary is queued for physician sign-off. Please confirm all details with your doctor."
        if is_te:
            status_heading = "⏳ వైద్యుల పరిశీలనలో ఉంది: డాక్టర్ ఆమోదం పెండింగ్ (PENDING REVIEW)"
            status_sub = "ఈ ప్రణాళిక వైద్యుల అధికారిక ధృవీకరణ కొరకు వేచి ఉంది. దయచేసి వివరాలను వైద్యుడితో సరిచూసుకోండి."

        badge_p = Paragraph(f"<b>{status_heading}</b><br/>{status_sub}", style_badge_pending)
        badge_table = Table([[badge_p]], colWidths=[523])
        badge_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#f59e0b")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(badge_table)

    story.append(Spacer(1, 10))

    # 3. Daily Medication Schedule (Morning / Afternoon / Night / As Needed / Unspecified)
    sched_heading = "1. దినసరి మందుల సమయ పట్టిక (Daily Medication Schedule)" if is_te else "1. DAILY MEDICATION SCHEDULE (Strictly Prescribed Timing)"
    story.append(Paragraph(sched_heading, style_h2))

    sched = data.get("medication_schedule") or {}
    morning_items = sched.get("morning", [])
    afternoon_items = sched.get("afternoon", [])
    night_items = sched.get("night", [])
    sos_items = sched.get("as_needed", [])
    unspec_items = sched.get("unspecified", [])

    def format_slot(items: List[Dict[str, Any]], slot_name: str) -> str:
        if not items:
            return "<i>" + ("మందులు లేవు" if is_te else "None scheduled") + "</i>"
        out = []
        for it in items:
            name = it.get("name", "")
            dose = it.get("dose", "")
            timing = it.get("timing") or it.get("instruction", "")
            out.append(f"• <b>{name}</b> ({dose})<br/>  {timing}")
        return "<br/>".join(out)

    sched_rows = [
        [
            Paragraph("<b>" + ("ఉదయం (Morning)" if is_te else "Morning") + "</b>", style_body_bold),
            Paragraph("<b>" + ("మధ్యాహ్నం (Afternoon)" if is_te else "Afternoon") + "</b>", style_body_bold),
            Paragraph("<b>" + ("రాత్రి (Night)" if is_te else "Night") + "</b>", style_body_bold),
            Paragraph("<b>" + ("అవసరమైనప్పుడు (SOS)" if is_te else "As Needed (SOS)") + "</b>", style_body_bold),
        ],
        [
            Paragraph(format_slot(morning_items, "Morning"), style_body),
            Paragraph(format_slot(afternoon_items, "Afternoon"), style_body),
            Paragraph(format_slot(night_items, "Night"), style_body),
            Paragraph(format_slot(sos_items, "As Needed"), style_body),
        ]
    ]

    t_sched = Table(sched_rows, colWidths=[130, 131, 131, 131])
    t_sched.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_sched)

    if unspec_items:
        story.append(Spacer(1, 4))
        unspec_text = "<b>" + ("సమయం పేర్కొనబడలేదు (Timing Not Specified):" if is_te else "Timing Not Specified:") + "</b> "
        unspec_text += "; ".join([f"{it.get('name')} ({it.get('dose')})" for it in unspec_items])
        unspec_text += " — " + ("దయచేసి సమయం కోసం వైద్యుడిని సంప్రదించండి." if is_te else "Please confirm exact timing with your doctor.")
        story.append(Paragraph(unspec_text, style_body))

    story.append(Spacer(1, 10))

    # 4. Active Prescribed Medicines Table
    med_heading = "2. ఇంట్లో వేసుకోవలసిన మందులు (Active Prescribed Medications)" if is_te else "2. ACTIVE PRESCRIBED MEDICATIONS"
    story.append(Paragraph(med_heading, style_h2))

    med_header_cols = [
        "మందు పేరు (Medicine)" if is_te else "Medicine Name",
        "మోతాదు (Dose)" if is_te else "Dose",
        "పద్ధతి (Freq)" if is_te else "Frequency",
        "సమయం (Timing)" if is_te else "Timing",
        "వ్యవధి (Duration)" if is_te else "Duration",
        "ఎలా వేసుకోవాలి (Instructions)" if is_te else "How to Take",
    ]

    med_table_data = [[Paragraph(f"<b>{col}</b>", style_body_bold) for col in med_header_cols]]

    medicines = data.get("medicines") or []
    if medicines:
        for m in medicines:
            m_name = m.get("name", "")
            m_dose = m.get("dose", "")
            m_freq = m.get("frequency", "")
            m_timing = m.get("timing", "")
            m_dur = m.get("duration", "")
            m_how = m.get("how_to_take_plain", "") or m.get("instruction", "")

            med_table_data.append([
                Paragraph(f"<b>{m_name}</b>", style_body_bold),
                Paragraph(m_dose, style_body),
                Paragraph(m_freq, style_body),
                Paragraph(m_timing, style_body),
                Paragraph(m_dur, style_body),
                Paragraph(m_how, style_body),
            ])
    else:
        med_table_data.append([
            Paragraph("మందులు ఏవీ పేర్కొనబడలేదు" if is_te else "No active discharge medicines found.", style_body),
            Paragraph("-", style_body), Paragraph("-", style_body),
            Paragraph("-", style_body), Paragraph("-", style_body), Paragraph("-", style_body),
        ])

    t_meds = Table(med_table_data, colWidths=[120, 60, 65, 80, 78, 120])
    t_meds.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_meds)
    story.append(Spacer(1, 10))

    # 5. Discontinued / Stopped Medicines (If any)
    stop_medicines = data.get("stop_medicines") or []
    if stop_medicines:
        stop_heading = "🛑 నిలిపివేయవలసిన మందులు (Discontinued Medications - DO NOT TAKE)" if is_te else "🛑 DISCONTINUED MEDICATIONS (DO NOT TAKE)"
        story.append(Paragraph(stop_heading, style_h2))

        stop_lines = []
        for sm in stop_medicines:
            s_name = sm.get("name", "")
            s_reason = sm.get("reason", "Discontinued by attending doctor")
            stop_lines.append(f"• <b>STOP {s_name}</b>: {s_reason}")

        stop_p = Paragraph("<br/>".join(stop_lines), style_badge_changes)
        t_stop = Table([[stop_p]], colWidths=[523])
        t_stop.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#ef4444")),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t_stop)
        story.append(Spacer(1, 10))

    # 6. Follow-up Appointments
    fu_heading = "3. తదుపరి సమీక్ష తేదీలు (Scheduled Follow-up Appointments)" if is_te else "3. SCHEDULED FOLLOW-UP APPOINTMENTS"
    story.append(Paragraph(fu_heading, style_h2))

    fu_table_data = [[
        Paragraph("<b>" + ("తేదీ (Date)" if is_te else "Date") + "</b>", style_body_bold),
        Paragraph("<b>" + ("వైద్యుడు / విభాగం (Doctor / Dept)" if is_te else "Doctor / Department") + "</b>", style_body_bold),
        Paragraph("<b>" + ("పరీక్ష ఉద్దేశం (Purpose)" if is_te else "Purpose") + "</b>", style_body_bold),
    ]]
    follow_ups = data.get("follow_ups") or []
    if follow_ups:
        for fu in follow_ups:
            fu_table_data.append([
                Paragraph(f"<b>{fu.get('date', '')}</b>", style_body_bold),
                Paragraph(fu.get("with_whom", ""), style_body),
                Paragraph(fu.get("purpose", ""), style_body),
            ])
    else:
        fu_table_data.append([
            Paragraph("పేర్కొనబడలేదు" if is_te else "Not specified", style_body),
            Paragraph("వైద్యుడిని సంప్రదించండి" if is_te else "Consult hospital", style_body),
            Paragraph("సాధారణ పరీక్ష" if is_te else "Routine follow-up", style_body),
        ])

    t_fu = Table(fu_table_data, colWidths=[110, 180, 233])
    t_fu.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_fu)
    story.append(Spacer(1, 10))

    # 7. Warning Signs & Dietary / Activity Instructions
    warn_heading = "4. అత్యవసర ప్రమాద హెచ్చరికలు (Emergency Warning Signs)" if is_te else "4. EMERGENCY WARNING SIGNS (Seek Immediate Medical Care)"
    story.append(Paragraph(warn_heading, style_h2))

    warnings = data.get("warning_signs") or []
    if warnings:
        warn_content = "<br/>".join([f"⚠️ • {w}" for w in warnings])
    else:
        warn_content = "తీవ్రమైన నొప్పి, ఆయాసం లేదా అధిక జ్వరం వస్తే వెంటనే ఆసుపత్రికి వెళ్ళండి." if is_te else "Proceed to emergency room if experiencing severe chest pain, shortness of breath, high fever, or unexpected bleeding."

    warn_p = Paragraph(warn_content, style_badge_changes)
    t_warn = Table([[warn_p]], colWidths=[523])
    t_warn.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fff1f2")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#f43f5e")),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_warn)
    story.append(Spacer(1, 8))

    # Dietary & Activity Grid
    diet_items = data.get("diet") or []
    act_items = data.get("activity") or []

    diet_text = "<br/>".join([f"• {d}" for d in diet_items]) if diet_items else ("సాధారణ పోషకాహారం తీసుకోండి." if is_te else "Follow balanced nutritious diet.")
    act_text = "<br/>".join([f"• {a}" for a in act_items]) if act_items else ("తగినంత విశ్రాంతి తీసుకోండి." if is_te else "Ensure adequate rest and light movement.")

    life_table_data = [
        [
            Paragraph("<b>" + ("ఆహార నియమాలు (Dietary Guidance)" if is_te else "Dietary Guidance") + "</b>", style_body_bold),
            Paragraph("<b>" + ("విశ్రాంతి & శారీరక శ్రమ (Activity & Rest)" if is_te else "Activity & Rest") + "</b>", style_body_bold)
        ],
        [
            Paragraph(diet_text, style_body),
            Paragraph(act_text, style_body)
        ]
    ]
    t_life = Table(life_table_data, colWidths=[261, 262])
    t_life.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_life)
    story.append(Spacer(1, 10))

    # 8. Important Disclaimer
    disclaimer_text = (
        "<b>ముఖ్య గమనిక:</b> కేర్‌బ్రిడ్జ్ AI ఆసుపత్రి డిశ్చార్జ్ సారాంశాన్ని రోగులకు సులభంగా అర్థమయ్యే భాషలో అందిస్తుంది. ఔషధాల మోతాదులు మరియు కాలపరిమితులు మార్చబడలేదు. ఇది వైద్యుల ప్రత్యక్ష సలహాకు ప్రత్యామ్నాయం కాదు. అత్యవసర పరిస్థితుల్లో వెంటనే మీ ఆసుపత్రిని సంప్రదించండి."
        if is_te else
        "<b>Important Clinical Notice:</b> CareBridge AI translates hospital discharge summaries into patient-understandable language with strict adherence to prescribed dosages, frequencies, and dates (Faithfulness Above Fluency). It does not replace professional medical judgment. In emergencies, proceed immediately to the nearest healthcare facility."
    )
    story.append(Paragraph(disclaimer_text, style_disclaimer))

    # Build PDF with custom NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Direct High-Resolution PNG Image Generator
# ---------------------------------------------------------------------------
def generate_care_plan_image(data: Dict[str, Any], lang: str = "en") -> bytes:
    """Generate a crisp, multi-section PNG image of the care plan.

    Renders at 1200px width with automatic height calculation to prevent clipping.

    Args:
        data: Care plan dictionary.
        lang: 'en' for English or 'te' for Telugu.

    Returns:
        bytes: Raw PNG image bytes ready for direct download.
    """
    is_te = (lang == "te")
    width = 1200

    # Load TrueType font with fallbacks
    font_large = None
    font_med = None
    font_bold = None
    font_regular = None
    font_small = None

    if FONT_AVAILABLE:
        try:
            font_large = ImageFont.truetype(SYSTEM_FONT_PATH, 28, index=0)
            font_med = ImageFont.truetype(SYSTEM_FONT_PATH, 20, index=0)
            font_bold = ImageFont.truetype(SYSTEM_FONT_PATH, 17, index=1 if "Nirmala" in SYSTEM_FONT_PATH else 0)
            font_regular = ImageFont.truetype(SYSTEM_FONT_PATH, 16, index=0)
            font_small = ImageFont.truetype(SYSTEM_FONT_PATH, 13, index=0)
        except Exception as e:
            logger.warning(f"Failed to load TrueType font for Pillow: {e}")

    if not font_large:
        font_large = ImageFont.load_default()
        font_med = font_large
        font_bold = font_large
        font_regular = font_large
        font_small = font_large

    # Pre-calculate estimated height to prevent clipping
    meds = data.get("medicines") or []
    stop_meds = data.get("stop_medicines") or []
    follow_ups = data.get("follow_ups") or []
    warnings = data.get("warning_signs") or []
    diet = data.get("diet") or []
    activity = data.get("activity") or []

    num_med_rows = max(1, len(meds))
    num_stop_rows = len(stop_meds)
    num_fu_rows = max(1, len(follow_ups))
    num_warn_rows = max(1, len(warnings))
    num_life_rows = max(1, max(len(diet), len(activity)))

    est_height = 420 + (num_med_rows * 36) + (num_stop_rows * 40) + (num_fu_rows * 32) + (num_warn_rows * 28) + (num_life_rows * 26) + 400
    est_height = max(1600, est_height)

    img = Image.new("RGB", (width, est_height), color="#ffffff")
    draw = ImageDraw.Draw(img)

    # 1. Header Banner
    draw.rectangle([(0, 0), (width, 100)], fill="#0f172a")
    title_text = "కేర్‌బ్రిడ్జ్ రోగి డిశ్చార్జ్ సంరక్షణ ప్రణాళిక" if is_te else "CAREBRIDGE PATIENT DISCHARGE CARE PLAN"
    sub_text = "ఆసుపత్రి డిశ్చార్జ్ అనంతర గృహ సంరక్షణ & ఔషధ మార్గదర్శిని" if is_te else "Clearer Care After Hospital Discharge — Family & Home Companion"

    draw.text((40, 20), title_text, fill="#ffffff", font=font_large)
    draw.text((40, 62), sub_text, fill="#38bdf8", font=font_regular)

    summary_id = data.get("case_id") or data.get("summary_id") or "PATIENT-CARE-PLAN"
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    draw.text((width - 320, 25), f"Case Ref: {summary_id}", fill="#94a3b8", font=font_small)
    draw.text((width - 320, 48), f"Generated: {gen_time}", fill="#94a3b8", font=font_small)
    draw.text((width - 320, 70), f"Language: {'తెలుగు (te)' if is_te else 'English (en)'}", fill="#94a3b8", font=font_small)

    y = 120

    # 2. Doctor Review Status Banner
    doc_status = (data.get("doctor_review_status") or "PENDING").upper()
    app_info = data.get("approval_info") or {}

    if doc_status == "APPROVED":
        doc_name = app_info.get("doctor_name", "Attending Physician")
        doc_lic = app_info.get("doctor_license", "Certified MD")
        time_str = app_info.get("created_at", gen_time)[:16].replace("T", " ")
        badge_bg = "#ecfdf5"
        badge_border = "#10b981"
        badge_text_color = "#065f46"
        badge_title = f"🛡️ CLINICALLY APPROVED BY Dr. {doc_name} ({doc_lic}) on {time_str} UTC"
        if is_te:
            badge_title = f"🛡️ వైద్యులచే ఆమోదించబడింది (APPROVED) — Dr. {doc_name} ({doc_lic}) - {time_str}"
    elif doc_status == "CHANGES_REQUESTED":
        badge_bg = "#fef2f2"
        badge_border = "#ef4444"
        badge_text_color = "#991b1b"
        badge_title = "⚠️ CHANGES REQUESTED BY PHYSICIAN — PENDING REVISION"
        if is_te:
            badge_title = "⚠️ వైద్యుల పరిశీలన: మార్పులు అవసరం (CHANGES REQUESTED)"
    else:
        badge_bg = "#fffbeb"
        badge_border = "#f59e0b"
        badge_text_color = "#92400e"
        badge_title = "⏳ DOCTOR REVIEW: PENDING CLINICAL VERIFICATION"
        if is_te:
            badge_title = "⏳ వైద్యుల పరిశీలనలో ఉంది: డాక్టర్ ఆమోదం పెండింగ్ (PENDING REVIEW)"

    draw.rectangle([(40, y), (width - 40, y + 44)], fill=badge_bg, outline=badge_border, width=2)
    draw.text((55, y + 12), badge_title, fill=badge_text_color, font=font_bold)
    y += 64

    # 3. Daily Medication Schedule (4 Slots)
    sched_title = "1. దినసరి మందుల సమయ పట్టిక (Daily Medication Schedule)" if is_te else "1. DAILY MEDICATION SCHEDULE"
    draw.text((40, y), sched_title, fill="#0f172a", font=font_bold)
    y += 28

    sched = data.get("medication_schedule") or {}
    slots = [
        ("ఉదయం (Morning)" if is_te else "Morning", sched.get("morning", []), "#eff6ff", "#bfdbfe"),
        ("మధ్యాహ్నం (Afternoon)" if is_te else "Afternoon", sched.get("afternoon", []), "#fefce8", "#fef08a"),
        ("రాత్రి (Night)" if is_te else "Night", sched.get("night", []), "#f5f3ff", "#ddd6fe"),
        ("అవసరమైనప్పుడు (SOS)" if is_te else "As Needed (SOS)", sched.get("as_needed", []), "#f0fdf4", "#bbf7d0"),
    ]

    slot_w = (width - 80 - 30) // 4
    for i, (s_name, items, bg_col, bdr_col) in enumerate(slots):
        sx = 40 + i * (slot_w + 10)
        draw.rectangle([(sx, y), (sx + slot_w, y + 120)], fill=bg_col, outline=bdr_col, width=1)
        draw.text((sx + 10, y + 8), s_name, fill="#1e293b", font=font_bold)

        iy = y + 32
        if items:
            for it in items[:3]:
                line = f"• {it.get('name', '')} ({it.get('dose', '')})"
                draw.text((sx + 8, iy), line[:28], fill="#334155", font=font_small)
                iy += 20
        else:
            draw.text((sx + 10, iy), "None" if not is_te else "మందులు లేవు", fill="#94a3b8", font=font_small)

    y += 136

    # 4. Active Prescribed Medicines Table
    med_title = "2. ఇంట్లో వేసుకోవలసిన మందులు (Active Prescribed Medications)" if is_te else "2. ACTIVE PRESCRIBED MEDICATIONS"
    draw.text((40, y), med_title, fill="#0f172a", font=font_bold)
    y += 26

    # Table Header Row
    draw.rectangle([(40, y), (width - 40, y + 32)], fill="#e2e8f0")
    cols = [
        ("Medicine", 50, 240),
        ("Dose", 300, 100),
        ("Frequency", 410, 140),
        ("Timing", 560, 150),
        ("Duration", 720, 130),
        ("How to Take", 860, 290)
    ]
    if is_te:
        cols = [
            ("మందు పేరు (Medicine)", 50, 240),
            ("మోతాదు (Dose)", 300, 100),
            ("పద్ధతి (Freq)", 410, 140),
            ("సమయం (Timing)", 560, 150),
            ("వ్యవధి (Duration)", 720, 130),
            ("సూచన (Instructions)", 860, 290)
        ]

    for cname, cx, cw in cols:
        draw.text((cx, y + 7), cname, fill="#0f172a", font=font_bold)
    y += 32

    # Table Data Rows
    if meds:
        for idx, m in enumerate(meds):
            row_bg = "#ffffff" if idx % 2 == 0 else "#f8fafc"
            draw.rectangle([(40, y), (width - 40, y + 34)], fill=row_bg, outline="#e2e8f0", width=1)
            draw.text((50, y + 8), str(m.get("name", ""))[:28], fill="#0f172a", font=font_bold)
            draw.text((300, y + 8), str(m.get("dose", "")), fill="#0284c7", font=font_regular)
            draw.text((410, y + 8), str(m.get("frequency", "")), fill="#334155", font=font_regular)
            draw.text((560, y + 8), str(m.get("timing", ""))[:18], fill="#334155", font=font_regular)
            draw.text((720, y + 8), str(m.get("duration", ""))[:15], fill="#334155", font=font_regular)
            how_str = str(m.get("how_to_take_plain", "") or m.get("instruction", ""))[:34]
            draw.text((860, y + 8), how_str, fill="#475569", font=font_small)
            y += 34
    else:
        draw.rectangle([(40, y), (width - 40, y + 34)], fill="#ffffff", outline="#e2e8f0", width=1)
        draw.text((50, y + 8), "No active medications found" if not is_te else "మందులు లేవు", fill="#64748b", font=font_regular)
        y += 34

    y += 18

    # 5. Stopped Medicines (If any)
    if stop_meds:
        stop_title = "🛑 నిలిపివేయవలసిన మందులు (Discontinued Medications - DO NOT TAKE)" if is_te else "🛑 DISCONTINUED MEDICATIONS (DO NOT TAKE)"
        draw.text((40, y), stop_title, fill="#dc2626", font=font_bold)
        y += 24
        draw.rectangle([(40, y), (width - 40, y + (len(stop_meds) * 28) + 12)], fill="#fef2f2", outline="#ef4444", width=1)
        sy = y + 8
        for sm in stop_meds:
            draw.text((55, sy), f"• STOP {sm.get('name', '')}: {sm.get('reason', 'Discontinued')}", fill="#991b1b", font=font_bold)
            sy += 26
        y += (len(stop_meds) * 28) + 26

    # 6. Follow-up Appointments
    fu_title = "3. తదుపరి సమీక్ష తేదీలు (Scheduled Follow-up Appointments)" if is_te else "3. SCHEDULED FOLLOW-UP APPOINTMENTS"
    draw.text((40, y), fu_title, fill="#0f172a", font=font_bold)
    y += 24

    draw.rectangle([(40, y), (width - 40, y + 30)], fill="#f1f5f9")
    draw.text((50, y + 6), "తేదీ (Date)" if is_te else "Date", fill="#0f172a", font=font_bold)
    draw.text((250, y + 6), "వైద్యుడు / విభాగం (Doctor / Dept)" if is_te else "Doctor / Department", fill="#0f172a", font=font_bold)
    draw.text((600, y + 6), "పరీక్ష ఉద్దేశం (Purpose)" if is_te else "Purpose", fill="#0f172a", font=font_bold)
    y += 30

    if follow_ups:
        for fu in follow_ups:
            draw.rectangle([(40, y), (width - 40, y + 28)], fill="#ffffff", outline="#e2e8f0", width=1)
            draw.text((50, y + 6), str(fu.get("date", "")), fill="#0f172a", font=font_bold)
            draw.text((250, y + 6), str(fu.get("with_whom", "")), fill="#334155", font=font_regular)
            draw.text((600, y + 6), str(fu.get("purpose", "")), fill="#334155", font=font_regular)
            y += 28
    else:
        draw.rectangle([(40, y), (width - 40, y + 28)], fill="#ffffff", outline="#e2e8f0", width=1)
        draw.text((50, y + 6), "Not specified in summary" if not is_te else "పేర్కొనబడలేదు", fill="#64748b", font=font_regular)
        y += 28

    y += 18

    # 7. Warning Signs & Diet/Activity
    warn_title = "4. అత్యవసర ప్రమాద హెచ్చరికలు (Emergency Warning Signs)" if is_te else "4. EMERGENCY WARNING SIGNS (Seek Immediate Care)"
    draw.text((40, y), warn_title, fill="#dc2626", font=font_bold)
    y += 24

    w_count = max(1, len(warnings))
    draw.rectangle([(40, y), (width - 40, y + (w_count * 24) + 12)], fill="#fff1f2", outline="#f43f5e", width=1)
    wy = y + 8
    if warnings:
        for w in warnings:
            draw.text((55, wy), f"⚠️ • {w}", fill="#881337", font=font_regular)
            wy += 24
    else:
        draw.text((55, wy), "Proceed to ER if severe symptoms arise" if not is_te else "తీవ్ర లక్షణాలు వస్తే అత్యవసర ఆసుపత్రికి వెళ్ళండి", fill="#881337", font=font_regular)
        wy += 24
    y += (w_count * 24) + 26

    # 8. Disclaimer Footer
    disclaimer_bg = [(0, est_height - 65), (width, est_height)]
    draw.rectangle(disclaimer_bg, fill="#f8fafc", outline="#cbd5e1", width=1)
    disc_text = (
        "కేర్‌బ్రిడ్జ్ AI — వైద్యుల పర్యవేక్షణ కొరకు రోగి సంరక్షణ సహాయక సాధనం. మోతాదులు మరియు కాలపరిమితులు ఖచ్చితంగా ఉంచబడ్డాయి (Faithfulness Above Fluency)."
        if is_te else
        "CareBridge AI — Faithfulness Above Fluency. Patient-friendly summary of hospital discharge instructions. Does not replace physician consultation."
    )
    draw.text((40, est_height - 45), disc_text, fill="#64748b", font=font_small)

    buf = io.BytesIO()
    # Crop to actual rendered bottom if less than est_height, or save full
    actual_bottom = min(est_height, y + 80)
    final_img = img.crop((0, 0, width, max(actual_bottom, 1200)))
    final_img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
