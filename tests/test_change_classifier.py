from impactdoc_ai.analysis.change_category import (
    ChangeCategory,
    ChangeClassification,
)
from impactdoc_ai.analysis.change_classifier import (
    DEFAULT_CLASSIFICATION_REASON,
    classify_change_by_rules,
    clean_classification_reason,
    validate_classification_reason_semantics,
)


def test_document_version_is_other():
    result = classify_change_by_rules(
        "Sürüm: 1.0",
        "Sürüm: 2.0",
    )

    assert result is not None
    assert result.category == ChangeCategory.OTHER


def test_software_version_is_technical():
    result = classify_change_by_rules(
        "Yazılım sürümü 1.0",
        "Yazılım sürümü 2.0",
    )

    assert result is not None
    assert result.category == ChangeCategory.TECHNICAL


def test_process_timing_change():
    result = classify_change_by_rules(
        "Talep üç iş günü içinde tamamlanır.",
        "Talep bir iş günü içinde tamamlanır.",
    )

    assert result is not None
    assert result.category == ChangeCategory.PROCESS


def test_prompt_like_reason_is_removed():
    reason = clean_classification_reason(
        "Sınıflandırma, değişikliğin baskın etkisine göre yapılır."
    )

    assert reason == DEFAULT_CLASSIFICATION_REASON


def test_added_change_reason_cannot_reference_old_text():
    classification = ChangeClassification(
        category=ChangeCategory.TECHNICAL,
        confidence=0.95,
        reason=(
            "Eski metin kritik sistem erişimleri ifadesiyle "
            "yeni metin aynıdır."
        ),
        source="ollama",
    )

    result = validate_classification_reason_semantics(
        classification,
        "",
        "Kritik sistem erişimleri güvenlik onayından sonra tanımlanır.",
    )

    assert result.category == ChangeCategory.TECHNICAL
    assert result.confidence == 0.95
    assert "Yeni içerik eklenmiştir" in result.reason
    assert "Eski metin" not in result.reason


def test_removed_change_reason_cannot_reference_new_text():
    classification = ChangeClassification(
        category=ChangeCategory.TASK,
        confidence=0.90,
        reason="Yeni metin çalışan görevini değiştirmektedir.",
        source="ollama",
    )

    result = validate_classification_reason_semantics(
        classification,
        "Çalışan aylık faaliyet raporu hazırlar.",
        "",
    )

    assert result.category == ChangeCategory.TASK
    assert result.confidence == 0.90
    assert "İçerik kaldırılmıştır" in result.reason