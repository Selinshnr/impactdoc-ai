from impactdoc_ai.analysis.impact_scoring import ImpactLevel
from impactdoc_ai.analysis.role_impact_analyzer import (
    ChangeImpact,
    RoleImpactAnalysisResult,
    analyze_change,
    find_affected_roles,
    normalize_text,
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


def test_normalize_text_handles_turkish_i():
    assert normalize_text("İzin Talebi") == "izin talebi"


def test_explicit_role_is_detected():
    text = normalize_text(
        "Bilgi Güvenliği Uzmanı kritik sistemleri kontrol eder."
    )

    roles, _ = find_affected_roles(text)

    assert roles == [
        "Bilgi Güvenliği Uzmanı",
    ]


def test_keyword_based_role_detection():
    text = normalize_text(
        "Personele VPN erişimi tanımlar."
    )

    roles, keywords = find_affected_roles(text)

    assert "Bilgi İşlem Uzmanı" in roles
    assert "vpn" in keywords


def test_no_role_evidence_defaults_to_document_manager():
    text = normalize_text(
        "Genel açıklama metni güncellenmiştir."
    )

    roles, keywords = find_affected_roles(text)

    assert roles == [
        "Doküman Yöneticisi",
    ]
    assert keywords == []


def test_analyze_change_returns_expected_structure():
    change = make_change(
        None,
        "Bilgi İşlem Uzmanı personele VPN erişimi tanımlar.",
        ChangeType.ADDED,
    )

    impact = analyze_change(
        change=change,
        change_number=1,
    )

    assert impact.change_id == "change-1"
    assert impact.change_type == ChangeType.ADDED
    assert "Bilgi İşlem Uzmanı" in impact.affected_roles
    assert impact.impact_level in {
        ImpactLevel.MEDIUM,
        ImpactLevel.HIGH,
    }
    assert isinstance(impact.reason, str)
    assert impact.reason


def test_role_analysis_summary_counts_impacts():
    impacts = [
        ChangeImpact(
            change_id="change-1",
            change_type=ChangeType.ADDED,
            old_text=None,
            new_text="Test 1",
            affected_roles=["Çalışan"],
            impact_level=ImpactLevel.HIGH,
            reason="Test.",
            matched_keywords=[],
        ),
        ChangeImpact(
            change_id="change-2",
            change_type=ChangeType.MODIFIED,
            old_text="Test 2",
            new_text="Test 3",
            affected_roles=[
                "Çalışan",
                "Birim Yöneticisi",
            ],
            impact_level=ImpactLevel.MEDIUM,
            reason="Test.",
            matched_keywords=[],
        ),
        ChangeImpact(
            change_id="change-3",
            change_type=ChangeType.MODIFIED,
            old_text="Test 4",
            new_text="Test 5",
            affected_roles=["Doküman Yöneticisi"],
            impact_level=ImpactLevel.LOW,
            reason="Test.",
            matched_keywords=[],
        ),
    ]

    result = RoleImpactAnalysisResult(
        old_file_name="v1.txt",
        new_file_name="v2.txt",
        impacts=impacts,
    )

    summary = result.summary()

    assert summary["analyzed_change_count"] == 3
    assert summary["high_impact"] == 1
    assert summary["medium_impact"] == 1
    assert summary["low_impact"] == 1

    assert result.role_change_counts()["Çalışan"] == 2

    assert set(summary["affected_roles"]) == {
        "Çalışan",
        "Birim Yöneticisi",
        "Doküman Yöneticisi",
    }


def test_change_impact_to_dict():
    impact = ChangeImpact(
        change_id="change-1",
        change_type=ChangeType.ADDED,
        old_text=None,
        new_text="Yeni içerik",
        affected_roles=["Çalışan"],
        impact_level=ImpactLevel.MEDIUM,
        reason="Test gerekçesi.",
        matched_keywords=["çalışan"],
        new_position=2,
    )

    data = impact.to_dict()

    assert data["change_id"] == "change-1"
    assert data["change_type"] == "added"
    assert data["impact_level"] == "medium"
    assert data["affected_roles"] == [
        "Çalışan",
    ]
    assert data["matched_keywords"] == [
        "çalışan",
    ]