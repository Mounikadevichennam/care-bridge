"""English Care Plan Renderer.

Generates a clear, structured, patient-friendly English discharge care plan
at an approximate 8th-grade reading level while strictly preserving all clinical facts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.extractor import CarePlanData

class EnglishCarePlanRenderer:
    """Renders structured CarePlanData into a clear patient-friendly English narrative."""

    def render(self, data: CarePlanData) -> str:
        """Render care plan sections."""
        sections = []

        sections.append("CAREBRIDGE DISCHARGE CARE PLAN")
        sections.append("=" * 30)
        sections.append("This document summarizes your discharge care instructions in simple language. Always follow your doctor's exact medical guidance.")
        sections.append("")

        # 1. Medications to Take
        sections.append("1. MEDICINES TO TAKE AT HOME")
        sections.append("-" * 28)
        if data.medicines:
            for idx, med in enumerate(data.medicines, 1):
                timing_str = f", {med.timing}" if med.timing and med.timing != "As directed" else ""
                dur_str = f" for {med.duration}" if med.duration and med.duration != "As advised by doctor" else ""
                sections.append(
                    f"{idx}. {med.name} ({med.dose}): Take {med.frequency}{timing_str}{dur_str}. Instruction: {med.how_to_take_plain}."
                )
        else:
            sections.append("No active medications listed on this discharge summary.")
        sections.append("")

        # 2. Medicines to Stop
        sections.append("2. MEDICINES TO STOP")
        sections.append("-" * 20)
        if data.stop_medicines:
            for idx, sm in enumerate(data.stop_medicines, 1):
                name = sm.get("name", "")
                reason = sm.get("reason", "Discontinued per doctor instructions")
                sections.append(f"{idx}. STOP taking {name} - {reason}.")
        else:
            sections.append("No medicines were marked to stop. Continue only what is listed above.")
        sections.append("")

        # 3. Follow-up Appointments
        sections.append("3. FOLLOW-UP APPOINTMENTS")
        sections.append("-" * 25)
        if data.follow_ups:
            for idx, fu in enumerate(data.follow_ups, 1):
                sections.append(f"{idx}. Date: {fu.date} | With: {fu.with_whom} | Purpose: {fu.purpose}.")
        else:
            sections.append("• Not specified in the discharge summary. Please verify with your healthcare provider.")
        sections.append("")

        # 4. Warning Signs (When to seek urgent care)
        sections.append("4. WARNING SIGNS (SEEK IMMEDIATE EMERGENCY CARE IF YOU NOTICE)")
        sections.append("-" * 55)
        if data.warning_signs:
            for sign in data.warning_signs:
                sections.append(f"• {sign}")
        else:
            sections.append("• Not specified in the discharge summary. Please verify with your healthcare provider.")
        sections.append("")

        # 5. Diet Advice
        sections.append("5. DIET INSTRUCTIONS")
        sections.append("-" * 20)
        if data.diet:
            for d in data.diet:
                sections.append(f"• {d}")
        else:
            sections.append("• Not specified in the discharge summary. Please verify with your healthcare provider.")
        sections.append("")

        # 6. Physical Activity
        sections.append("6. ACTIVITY & REST")
        sections.append("-" * 18)
        if data.activity:
            for a in data.activity:
                sections.append(f"• {a}")
        else:
            sections.append("• Not specified in the discharge summary. Please verify with your healthcare provider.")
        sections.append("")

        sections.append("Important Safety Notice: This care plan is an assistance tool. If you experience any severe symptoms, please visit the nearest hospital emergency room immediately.")

        return "\n".join(sections)

