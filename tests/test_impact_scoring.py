from impactdoc_ai.analysis.change_category import (
    ChangeCategory,
    ChangeClassification,
)
from impactdoc_ai.analysis.impact_scoring import (
    ImpactLevel,
    calculate_impact_decision,
    calculate_rule_level,
    maximum_level,
    parse_impact_level,
)
from impactdoc_ai.comparison import ChangeType, TextChange


def make_change(
    old_text: str | None,
    new_text: str | None,
    change_type: ChangeType,
) -> TextChange:
    return TextChange(
        change_type=change_type,
        old_text=old_text,
        new_text=new_text,
        old_position=1 if old_text is not None else None,
        new_position=1 if new_text is not None else None,
        similarity_score=0.80,
    )


def make_classification(
    category: ChangeCategory,
) -> ChangeClassification:
    return ChangeClassification(
        category=category,
        confidence=0.95,
        reason="Test sınıflandırması.",
        source="rule",
    )


def test_parse_impact_level():
    assert parse_impact_level("LOW") == ImpactLevel.LOW
    assert parse_impact_level(" medium ") == ImpactLevel.MEDIUM
    assert parse_impact_level(ImpactLevel.HIGH) == ImpactLevel.HIGH


def test_maximum_level():
    assert maximum_level(
        ImpactLevel.LOW,
        ImpactLevel.MEDIUM,
    ) == ImpactLevel.MEDIUM

    assert maximum_level(
        ImpactLevel.LOW,
        ImpactLevel.HIGH,
        ImpactLevel.MEDIUM,
    ) == ImpactLevel.HIGH


def test_added_change_is_at_least_medium():
    change = make_change(
        None,
        "Çalışan aylık rapor hazırlar.",
        ChangeType.ADDED,
    )

    classification = make_classification(
        ChangeCategory.TASK,
    )

    rule_level, _, rules = calculate_rule_level(
        change,
        classification,
        ["Çalışan"],
    )

    assert rule_level in {
        ImpactLevel.MEDIUM,
        ImpactLevel.HIGH,
    }

    assert any(
        "Yeni eklenen içerik en az medium" in rule
        for rule in rules
    )


def test_removed_change_is_at_least_medium():
    change = make_change(
        "Çalışan aylık rapor hazırlar.",
        None,
        ChangeType.REMOVED,
    )

    classification = make_classification(
        ChangeCategory.TASK,
    )

    rule_level, _, rules = calculate_rule_level(
        change,
        classification,
        ["Çalışan"],
    )

    assert rule_level in {
        ImpactLevel.MEDIUM,
        ImpactLevel.HIGH,
    }

    assert any(
        "Kaldırılan içerik en az medium" in rule
        for rule in rules
    )


def test_high_keyword_forces_high():
    change = make_change(
        None,
        "Kritik sistem erişimi güvenlik onayından sonra tanımlanır.",
        ChangeType.ADDED,
    )

    classification = make_classification(
        ChangeCategory.TECHNICAL,
    )

    rule_level, matched_keywords, _ = calculate_rule_level(
        change,
        classification,
        ["Bilgi Güvenliği Uzmanı"],
    )

    assert rule_level == ImpactLevel.HIGH
    assert matched_keywords


def test_rule_engine_can_override_lower_llm_level():
    change = make_change(
        None,
        "Kritik sistem erişimi güvenlik onayından sonra tanımlanır.",
        ChangeType.ADDED,
    )

    classification = make_classification(
        ChangeCategory.TECHNICAL,
    )

    decision = calculate_impact_decision(
        change=change,
        classification=classification,
        affected_roles=["Bilgi Güvenliği Uzmanı"],
        llm_level=ImpactLevel.LOW,
    )

    assert decision.final_level == ImpactLevel.HIGH
    assert decision.rule_level == ImpactLevel.HIGH
    assert decision.llm_level == ImpactLevel.LOW
    assert decision.source == "rule_engine"


def test_llm_level_is_kept_when_higher_than_rule():
    change = make_change(
        "Doküman başlığı güncellendi.",
        "Doküman başlığı revize edildi.",
        ChangeType.MODIFIED,
    )

    classification = make_classification(
        ChangeCategory.OTHER,
    )

    decision = calculate_impact_decision(
        change=change,
        classification=classification,
        affected_roles=["Doküman Yöneticisi"],
        llm_level=ImpactLevel.HIGH,
    )

    assert decision.final_level == ImpactLevel.HIGH
    assert decision.llm_level == ImpactLevel.HIGH
    assert decision.source == "llm"


def test_equal_llm_and_rule_levels_use_combined_source():
    change = make_change(
        None,
        "Çalışan aylık rapor hazırlar.",
        ChangeType.ADDED,
    )

    classification = make_classification(
        ChangeCategory.TASK,
    )

    decision = calculate_impact_decision(
        change=change,
        classification=classification,
        affected_roles=["Çalışan"],
        llm_level=ImpactLevel.MEDIUM,
    )

    assert decision.final_level == ImpactLevel.MEDIUM
    assert decision.rule_level == ImpactLevel.MEDIUM
    assert decision.llm_level == ImpactLevel.MEDIUM
    assert decision.source == "llm_and_rule_engine"


def test_decision_to_dict_contains_expected_fields():
    change = make_change(
        None,
        "Çalışan aylık rapor hazırlar.",
        ChangeType.ADDED,
    )

    classification = make_classification(
        ChangeCategory.TASK,
    )

    decision = calculate_impact_decision(
        change=change,
        classification=classification,
        affected_roles=["Çalışan"],
        llm_level=ImpactLevel.MEDIUM,
    )

    data = decision.to_dict()

    assert data["final_impact_level"] == "medium"
    assert data["llm_impact_level"] == "medium"
    assert data["rule_impact_level"] == "medium"
    assert "impact_source" in data
    assert "impact_reason" in data
    assert "matched_impact_keywords" in data
    assert "applied_impact_rules" in data