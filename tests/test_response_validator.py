from impactdoc_ai.analysis.response_validator import (
    validate_affected_roles,
    validate_confidence,
    validate_recommended_actions,
    validate_response_payload,
)
from impactdoc_ai.comparison import ChangeType, TextChange


def make_change(
    old_text: str | None,
    new_text: str | None,
    change_type: ChangeType = ChangeType.MODIFIED,
) -> TextChange:
    return TextChange(
        change_type=change_type,
        old_text=old_text,
        new_text=new_text,
        old_position=1 if old_text is not None else None,
        new_position=1 if new_text is not None else None,
        similarity_score=0.80,
    )


def test_fake_role_is_removed():
    change = make_change(
        "İzin talebi yöneticiye iletilir.",
        "İzin talebi birim yöneticisi tarafından onaylanır.",
    )

    role_pool = [
        "Doküman Yöneticisi",
        "Birim Yöneticisi",
        "Bilgi İşlem Uzmanı",
    ]

    result = validate_affected_roles(
        [
            "Uydurma Rol",
            "Bilgi İşlem Uzmanı",
            "Birim Yöneticisi",
        ],
        role_pool,
        change,
    )

    assert "Uydurma Rol" not in result
    assert "Bilgi İşlem Uzmanı" not in result
    assert "Birim Yöneticisi" in result


def test_technical_role_is_kept_with_technical_evidence():
    change = make_change(
        None,
        "Bilgi İşlem Uzmanı personele VPN erişimi tanımlar.",
        ChangeType.ADDED,
    )

    role_pool = [
        "Doküman Yöneticisi",
        "Bilgi İşlem Uzmanı",
        "Çalışan",
    ]

    result = validate_affected_roles(
        ["Bilgi İşlem Uzmanı"],
        role_pool,
        change,
    )

    assert "Bilgi İşlem Uzmanı" in result


def test_evidence_roles_are_added_even_if_llm_misses_them():
    change = make_change(
        None,
        "Uzaktan çalışma talebi çalışan tarafından oluşturulur.",
        ChangeType.ADDED,
    )

    role_pool = [
        "İnsan Kaynakları Uzmanı",
        "Çalışan",
        "Doküman Yöneticisi",
    ]

    result = validate_affected_roles(
        [],
        role_pool,
        change,
    )

    assert "Çalışan" in result


def test_role_count_is_limited():
    change = make_change(
        None,
        (
            "İnsan kaynakları, çalışan ve birim yöneticisi "
            "uzaktan çalışma talebini değerlendirir."
        ),
        ChangeType.ADDED,
    )

    role_pool = [
        "İnsan Kaynakları Uzmanı",
        "Birim Yöneticisi",
        "Çalışan",
        "Doküman Yöneticisi",
    ]

    result = validate_affected_roles(
        role_pool,
        role_pool,
        change,
        max_roles=2,
    )

    assert len(result) == 2


def test_confidence_is_clamped():
    assert validate_confidence(1.5) == 1.0
    assert validate_confidence(-0.2) == 0.0
    assert validate_confidence(0.87654) == 0.8765


def test_duplicate_actions_are_removed():
    result = validate_recommended_actions(
        [
            "Rol sahiplerini bilgilendir.",
            "Rol sahiplerini bilgilendir.",
            "Prosedürü güncelle.",
        ]
    )

    assert result == [
        "Rol sahiplerini bilgilendir.",
        "Prosedürü güncelle.",
    ]


def test_response_payload_is_normalized():
    change = make_change(
        None,
        "Birim yöneticisi talebi onaylar.",
        ChangeType.ADDED,
    )

    role_pool = [
        "Birim Yöneticisi",
        "Doküman Yöneticisi",
    ]

    response = {
        "affected_roles": [
            "Birim Yöneticisi",
            "Uydurma Rol",
        ],
        "impact_level": " MEDIUM ",
        "reason": "Onay süreci etkilenmektedir.",
        "recommended_actions": [
            "Birim yöneticisini bilgilendir.",
        ],
        "confidence": 0.91,
    }

    result = validate_response_payload(
        response,
        role_pool,
        change,
    )

    assert result["affected_roles"] == [
        "Birim Yöneticisi",
    ]
    assert result["impact_level"] == "medium"
    assert result["reason"] == "Onay süreci etkilenmektedir."
    assert result["recommended_actions"] == [
        "Birim yöneticisini bilgilendir.",
    ]
    assert result["confidence"] == 0.91