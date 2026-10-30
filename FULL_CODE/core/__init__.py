"""CareBridge AI Core Extraction Engine.

This package contains the complete pipeline for converting clinical
discharge summaries into patient-understandable care plans.
"""

from .abbreviation import AbbreviationResolver
from .medicine_mapper import MedicineMapper
from .frequency_parser import FrequencyParser
from .date_parser import DateParser
from .extractor import DischargeSummaryExtractor, CarePlanData, MedicineInfo, FollowUpInfo
from .english_renderer import EnglishCarePlanRenderer, EnglishCarePlanRenderer as EnglishRenderer
from .telugu import TeluguTranslationEngine, TeluguTranslationEngine as TeluguTranslator
from .validator import FaithfulnessValidator, ValidationReport, ValidationItem
from .readability import ReadabilityCalculator, ReadabilityCalculator as ReadabilityScorer
from .care_plan import CarePlanProcessor, CarePlanProcessor as CarePlanPipeline

__all__ = [
    "AbbreviationResolver",
    "MedicineMapper",
    "FrequencyParser",
    "DateParser",
    "DischargeSummaryExtractor",
    "CarePlanData",
    "MedicineInfo",
    "FollowUpInfo",
    "EnglishCarePlanRenderer",
    "EnglishRenderer",
    "TeluguTranslationEngine",
    "TeluguTranslator",
    "FaithfulnessValidator",
    "ValidationReport",
    "ValidationItem",
    "ReadabilityCalculator",
    "ReadabilityScorer",
    "CarePlanProcessor",
    "CarePlanPipeline",
]
