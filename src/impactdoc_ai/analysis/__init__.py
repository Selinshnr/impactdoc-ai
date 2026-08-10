"""Doküman değişiklik analiz bileşenleri."""

from impactdoc_ai.analysis.llm_impact_analyzer import (
    LLMChangeImpact,
    LLMImpactAnalysisResult,
    analyze_change_with_llm,
    analyze_role_impacts_with_llm,
)
from impactdoc_ai.analysis.impact_scoring import (
    ImpactDecision,
    ImpactLevel,
    calculate_impact_decision,
)
from impactdoc_ai.analysis.role_impact_analyzer import (
    ChangeImpact,
    RoleImpactAnalysisResult,
    analyze_change,
    analyze_role_impacts,
)
from impactdoc_ai.analysis.change_category import (
    ChangeCategory,
    ChangeClassification,
    get_category_catalog,
    parse_change_category,
)
from impactdoc_ai.analysis.change_classifier import (
    build_classification_prompt,
    classify_change_with_llm,
    extract_json_object,
    parse_classification_response,
    validate_classification_response,
    classify_change_with_ollama,
)

__all__ = [
    "ChangeImpact",
    "ImpactLevel",
    "RoleImpactAnalysisResult",
    "analyze_change",
    "analyze_role_impacts",
    "LLMChangeImpact",
    "LLMImpactAnalysisResult",
    "ImpactDecision",
    "calculate_impact_decision",
    "analyze_change_with_llm",
    "analyze_role_impacts_with_llm",
    "ChangeCategory",
    "ChangeClassification",
    "get_category_catalog",
    "parse_change_category",
    "build_classification_prompt",
    "classify_change_with_llm",
    "extract_json_object",
    "parse_classification_response",
    "validate_classification_response",
    "classify_change_with_ollama",
]