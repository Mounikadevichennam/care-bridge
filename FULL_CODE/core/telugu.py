"""Telugu Medical Translation and Script Engine.

Produces patient-understandable Telugu discharge care plans.
Preserves medicine brand/generic names in Latin script, Western digits,
dosages, and dates, while rendering narrative clinical instructions
in authentic Telugu script with high script density and function-word coverage.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Dict, Any, List

if TYPE_CHECKING:
    from core.extractor import CarePlanData, MedicineInfo, FollowUpInfo

logger = logging.getLogger(__name__)

# Telugu script unicode range: 0x0C00 - 0x0C7F
TELUGU_CHAR_REGEX = re.compile(r'[\u0C00-\u0C7F]')

class TeluguTranslationEngine:
    """Translates clinical care plan facts into natural Telugu."""

    # Timing translations
    TIMING_MAP = {
        "before food": "భోజనానికి ముందు",
        "before meals": "భోజనానికి ముందు",
        "on empty stomach": "ఖాళీ కడుపుతో",
        "after food": "భోజనం తర్వాత",
        "after meals": "భోజనం తర్వాత",
        "at bedtime": "రాత్రి పడుకునే ముందు",
        "before breakfast": "అల్పాహారానికి ముందు",
        "with food": "ఆహారంతో పాటు",
        "with milk": "పాలతో పాటు",
        "as directed": "డాక్టర్ సూచించిన విధంగా"
    }

    # Frequency translations
    FREQ_MAP = {
        "od": "రోజుకు ఒకసారి",
        "once daily": "రోజుకు ఒకసారి",
        "bd": "రోజుకు రెండుసార్లు (ఉదయం మరియు రాత్రి)",
        "bid": "రోజుకు రెండుసార్లు",
        "twice daily": "రోజుకు రెండుసార్లు (ఉదయం మరియు రాత్రి)",
        "tds": "రోజుకు మూడుసార్లు (ఉదయం, మధ్యాహ్నం, రాత్రి)",
        "tid": "రోజుకు మూడుసార్లు",
        "thrice daily": "రోజుకు మూడుసార్లు",
        "qid": "రోజుకు నాలుగుసార్లు",
        "four times daily": "రోజుకు నాలుగుసార్లు",
        "hs": "రాత్రి పడుకునే ముందు",
        "sos": "అవసరమైనప్పుడు మాత్రమే (నొప్పి లేదా జ్వరం వచ్చినప్పుడు)",
        "prn": "అవసరమైనప్పుడు మాత్రమే",
        "once weekly": "వారానికి ఒకసారి",
        "as advised": "వైద్యుల సలహా ప్రకారం"
    }

    def translate_care_plan(self, data: CarePlanData) -> str:
        """Translate CarePlanData into a comprehensive Telugu care guide."""
        lines: List[str] = []

        lines.append("కేర్‌బ్రిడ్జ్ రోగి డిశ్చార్జ్ సంరక్షణ ప్రణాళిక (CareBridge Telugu Care Plan)")
        lines.append("=" * 45)
        lines.append("ఈ సమాచారం మీరు ఆసుపత్రి నుండి ఇంటికి వెళ్ళిన తర్వాత పాటించవలసిన ముఖ్యమైన జాగ్రత్తలు మరియు ఔషధ సూచనలను వివరిస్తుంది. దయచేసి మీ డాక్టర్ సూచనలను తప్పకుండా పాటించండి.")
        lines.append("")

        # 1. Active Medicines
        lines.append("1. ఇంట్లో క్రమం తప్పకుండా వేసుకోవలసిన మందులు (Medicines to Take):")
        lines.append("-" * 40)
        if data.medicines:
            for idx, med in enumerate(data.medicines, 1):
                tel_freq = self._translate_frequency(med.frequency)
                tel_timing = self._translate_timing(med.timing)
                tel_dur = self._translate_duration(med.duration)

                lines.append(
                    f"{idx}. మందు పేరు: {med.name} ({med.dose})\n"
                    f"   • ఎలా తీసుకోవాలి: {tel_freq}, {tel_timing}.\n"
                    f"   • కాలపరిమితి: {tel_dur}.\n"
                    f"   • ముఖ్య సూచన: ఈ మందును సమయానికి మంచి నీటితో తీసుకోండి."
                )
        else:
            lines.append("ప్రస్తుతం ఎలాంటి కొత్త మందులు సూచించబడలేదు.")
        lines.append("")

        # 2. Stop Medicines
        lines.append("2. పూర్తిగా నిలిపివేయవలసిన మందులు (Medicines to Stop):")
        lines.append("-" * 38)
        if data.stop_medicines:
            for idx, sm in enumerate(data.stop_medicines, 1):
                name = sm.get("name", "")
                reason = sm.get("reason", "వైద్యుల ఆదేశాల మేరకు నిలిపివేయబడింది")
                lines.append(f"{idx}. {name}: ఈ మందును వెంటనే వాడటం ఆపండి ({reason}). పొరపాటున కూడా మళ్లీ వేసుకోవద్దు.")
        else:
            lines.append("పాత మందులలో వేటినీ నిలిపివేయవలసిన అవసరం లేదు. పై మందులను మాత్రమే వాడండి.")
        lines.append("")

        # 3. Follow-up
        lines.append("3. డాక్టర్ తదుపరి పరీక్ష తేదీ (Follow-up Appointments):")
        lines.append("-" * 38)
        if data.follow_ups:
            for idx, fu in enumerate(data.follow_ups, 1):
                lines.append(
                    f"{idx}. తనిఖీ తేదీ: {fu.date}\n"
                    f"   • ఎవరిని కలవాలి: {fu.with_whom}\n"
                    f"   • పరీక్ష ఉద్దేశం: {fu.purpose} కొరకు ఆసుపత్రికి వచ్చి చూపించుకోండి."
                )
        else:
            lines.append("• డిశ్చార్జ్ సారాంశంలో ప్రత్యేక సమీక్ష తేదీ పేర్కొనబడలేదు. దయచేసి మీ వైద్యుడిని సంప్రదించండి.")
        lines.append("")

        # 4. Warning Signs
        lines.append("4. అత్యవసర ప్రమాద హెచ్చరికలు - వెంటనే ఆసుపత్రికి వెళ్ళవలసిన పరిస్థితులు (Emergency Warning Signs):")
        lines.append("-" * 65)
        if data.warning_signs:
            for sign in data.warning_signs:
                tel_sign = self._translate_warning(sign)
                lines.append(f"• {tel_sign}")
        else:
            lines.append("• డిశ్చార్జ్ సారాంశంలో ప్రత్యేక హెచ్చరికలు పేర్కొనబడలేదు. ఏదైనా అసౌకర్యం లేదా తీవ్రమైన లక్షణాలు కనిపిస్తే వెంటనే వైద్యుడిని సంప్రదించండి.")
        lines.append("")

        # 5. Diet
        lines.append("5. ఆహార నియమాలు (Dietary Instructions):")
        lines.append("-" * 30)
        if data.diet:
            for d in data.diet:
                lines.append(f"• {self._translate_diet(d)}")
        else:
            lines.append("• డిశ్చార్జ్ సారాంశంలో ప్రత్యేక ఆహార సూచనలు పేర్కొనబడలేదు. దయచేసి మీ వైద్యుడిని సంప్రదించండి.")
        lines.append("")

        # 6. Activity
        lines.append("6. విశ్రాంతి మరియు శారీరక శ్రమ (Activity & Rest):")
        lines.append("-" * 32)
        if data.activity:
            for a in data.activity:
                lines.append(f"• {self._translate_activity(a)}")
        else:
            lines.append("• డిశ్చార్జ్ సారాంశంలో ప్రత్యేక శారీరక శ్రమ సూచనలు పేర్కొనబడలేదు. దయచేసి మీ వైద్యుడిని సంప్రదించండి.")
        lines.append("")

        lines.append("గమనిక: ఏదైనా అత్యవసర పరిస్థితి తలెత్తితే ఆలస్యం చేయకుండా వెంటనే సమీపంలోని అత్యవసర చికిత్స విభాగానికి (Emergency Room) వెళ్ళండి.")

        return "\n".join(lines)

    def _translate_frequency(self, freq: str) -> str:
        clean = (freq or "").strip().lower()
        if "1-0-1" in clean:
            return "ఉదయం 1 మరియు రాత్రి 1 (రోజుకు రెండుసార్లు)"
        if "1-1-1" in clean:
            return "ఉదయం 1, మధ్యాహ్నం 1, రాత్రి 1 (రోజుకు మూడుసార్లు)"
        if "0-0-1" in clean:
            return "రాత్రి పడుకునే ముందు 1 మాత్ర"
        if "1-0-0" in clean:
            return "ఉదయం మాత్రమే 1 మాత్ర"

        for k, v in self.FREQ_MAP.items():
            if k in clean:
                return v
        return f"{freq} ప్రకారం"

    def _translate_timing(self, timing: str) -> str:
        clean = (timing or "").strip().lower()
        for k, v in self.TIMING_MAP.items():
            if k in clean:
                return v
        return "భోజనం తర్వాత లేదా డాక్టర్ చెప్పినట్లు"

    def _translate_duration(self, duration: str) -> str:
        clean = (duration or "").strip().lower()
        if "lifelong" in clean or "long term" in clean:
            return "జీవితాంతం క్రమం తప్పకుండా వాడాలి"
        if "till next review" in clean:
            return "తదుపరి డాక్టర్ పరిశీలన వరకు"

        m = re.search(r'(\d+)\s*(days?|weeks?|months?)', clean)
        if m:
            n, unit = m.group(1), m.group(2)
            if "day" in unit: return f"{n} రోజుల పాటు"
            if "week" in unit: return f"{n} వారాల పాటు"
            if "month" in unit: return f"{n} నెలల పాటు"
        return duration or "వైద్యులు సూచించిన కాలపరిమితి వరకు"

    def _translate_warning(self, sign: str) -> str:
        s_low = sign.lower()
        if "chest pain" in s_low:
            return f"ఛాతీ నొప్పి లేదా దడ: {sign}"
        if "breath" in s_low or "dyspnea" in s_low:
            return f"శ్వాస తీసుకోవడంలో తీవ్ర ఇబ్బంది లేదా ఆయాసం: {sign}"
        if "fever" in s_low:
            return f"తీవ్రమైన జ్వరం లేదా చలి: {sign}"
        if "bleed" in s_low:
            return f"రక్తస్రావం కావడం: {sign}"
        if "swelling" in s_low or "edema" in s_low:
            return f"కాళ్ళ వాపు లేదా మొహం వాపు పెరగడం: {sign}"
        return f"హెచ్చరిక: {sign} కనిపిస్తే వెంటనే డాక్టర్‌ను సంప్రదించండి"

    def _translate_diet(self, d: str) -> str:
        d_low = d.lower()
        if "salt" in d_low:
            return f"ఉప్పు నియంత్రణ: ఉప్పు తక్కువగా వాడండి ({d})"
        if "sugar" in d_low or "diabetic" in d_low:
            return f"మధుమేహ ఆహారం: చక్కెర పదార్థాలు మరియు తీపి వస్తువులు తీసుకోకండి ({d})"
        if "fluid" in d_low or "water" in d_low:
            return f"ద్రవపదార్థాల నియంత్రణ: డాక్టర్ చెప్పిన పరిమాణంలోనే నీరు త్రాగండి ({d})"
        return f"ఆహార సలహా: {d}"

    def _translate_activity(self, a: str) -> str:
        a_low = a.lower()
        if "rest" in a_low:
            return f"విశ్రాంతి: శరీరానికి తగినంత విశ్రాంతి ఇవ్వండి ({a})"
        if "lifting" in a_low:
            return f"బరువులు ఎత్తవద్దు: బరువైన వస్తువులను ఎత్తడం పూర్తిగా నిషిద్ధం ({a})"
        if "walk" in a_low:
            return f"నడక: క్రమం తప్పకుండా తేలికపాటి నడక చేయండి ({a})"
        return f"శారీరక శ్రమ సూచన: {a}"

    def compute_telugu_script_share(self, text: str) -> float:
        """Calculate the proportion of Telugu Unicode characters relative to alphabetic chars."""
        if not text:
            return 0.0
        telugu_chars = len(TELUGU_CHAR_REGEX.findall(text))
        total_letters = len(re.findall(r'[\u0C00-\u0C7Fa-zA-Z]', text))
        if total_letters == 0:
            return 0.0
        return round(telugu_chars / total_letters, 4)

