"""LLM etki analizi yanıtlarını doğrulayan yardımcılar."""
from __future__ import annotations
from typing import Any
from impactdoc_ai.comparison import TextChange

TECHNICAL_ROLES = {"Bilgi İşlem Uzmanı", "Bilgi Güvenliği Uzmanı"}
ROLE_EVIDENCE_KEYWORDS = {
    "İnsan Kaynakları Uzmanı": ("insan kaynakları", "insan kaynakları birimi", "personel dosyası", "personel sistemi", "izin kaydı", "sözleşme", "uzaktan çalışma talebi"),
    "Birim Yöneticisi": ("birim yöneticisi", "birim yöneticileri", "yönetici", "iş sürekliliği"),
    "Çalışan": ("çalışan", "kurum çalışanları", "izin talebi", "uzaktan çalışma talebi", "işten ayrılan personel", "zimmetli cihaz"),
    "Bilgi İşlem Uzmanı": ("bilgi işlem", "bilgi işlem birimi", "kullanıcı hesabı", "vpn", "erişim tanımlama", "erişim tanımlar", "devre dışı"),
    "Bilgi Güvenliği Uzmanı": ("bilgi güvenliği", "bilgi güvenliği birimi", "güvenlik onayı", "kritik sistem", "çok faktörlü", "kimlik doğrulama", "erişim kontrolü", "erişim rol", "erişim roller", "kullanıcı erişim", "uzaktan erişim", "açık oturum"),
    "Doküman Yöneticisi": ("sürüm", "revizyon", "yürürlük tarihi", "doküman", "prosedür", "kapsam", "başlık"),
}
TECHNICAL_EVIDENCE_KEYWORDS = {k for r in TECHNICAL_ROLES for k in ROLE_EVIDENCE_KEYWORDS[r]}

def normalize_text(value: str | None) -> str:
    if value is None:
        return ""

    normalized = value.translate(
        str.maketrans(
            {
                "İ": "i",
                "I": "ı",
            }
        )
    ).lower()

    return " ".join(normalized.split())

def combine_change_text(change: TextChange) -> str:
    return normalize_text(f"{change.old_text or ''} {change.new_text or ''}")

def has_technical_evidence(change: TextChange) -> bool:
    text = combine_change_text(change)
    return any(k in text for k in TECHNICAL_EVIDENCE_KEYWORDS)

def find_evidence_roles(change: TextChange, role_pool: list[str]) -> list[str]:
    text = combine_change_text(change)
    return [role for role in role_pool if any(k in text for k in ROLE_EVIDENCE_KEYWORDS.get(role, ()))]

def validate_affected_roles(value: Any, role_pool: list[str], change: TextChange, max_roles: int = 3) -> list[str]:
    if not role_pool:
        raise ValueError("Rol havuzu boş olamaz.")
    if not isinstance(value, list):
        raise ValueError("affected_roles alanı liste olmalıdır.")
    evidence_roles = find_evidence_roles(change, role_pool)
    validated = []
    for role in value:
        if not isinstance(role, str):
            continue
        role = role.strip()
        if role and role in role_pool and role in evidence_roles and role not in validated:
            validated.append(role)
        if len(validated) >= max_roles:
            return validated
    for role in evidence_roles:
        if role not in validated:
            validated.append(role)
        if len(validated) >= max_roles:
            return validated
    if validated:
        return validated
    for role in value:
        if not isinstance(role, str):
            continue
        role = role.strip()
        if role and role in role_pool and role not in validated:
            if role in TECHNICAL_ROLES and not has_technical_evidence(change):
                continue
            validated.append(role)
        if len(validated) >= max_roles:
            break
    if validated:
        return validated
    return ["Doküman Yöneticisi" if "Doküman Yöneticisi" in role_pool else role_pool[0]]

def validate_recommended_actions(value: Any, min_actions: int = 1, max_actions: int = 3) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("recommended_actions alanı liste olmalıdır.")
    actions = []
    for action in value:
        if not isinstance(action, str):
            continue
        action = action.strip()
        if action and action not in actions:
            actions.append(action)
        if len(actions) >= max_actions:
            break
    if len(actions) < min_actions:
        raise ValueError("Model en az bir uygulanabilir aksiyon üretmelidir.")
    return actions

def validate_confidence(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("confidence sayısal bir değer olmalıdır.")
    try:
        confidence = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("confidence sayısal bir değer olmalıdır.") from exc
    return round(max(0.0, min(confidence, 1.0)), 4)

def validate_reason(value: Any) -> str:
    reason = str(value or "").strip()
    if not reason:
        raise ValueError("Model etki gerekçesi üretmedi.")
    return reason

def validate_response_payload(response_data: dict[str, Any], role_pool: list[str], change: TextChange) -> dict[str, Any]:
    if not isinstance(response_data, dict):
        raise ValueError("Model yanıtı JSON nesnesi olmalıdır.")
    return {
        "affected_roles": validate_affected_roles(response_data.get("affected_roles"), role_pool, change),
        "impact_level": str(response_data.get("impact_level", "")).strip().lower(),
        "reason": validate_reason(response_data.get("reason")),
        "recommended_actions": validate_recommended_actions(response_data.get("recommended_actions")),
        "confidence": validate_confidence(response_data.get("confidence")),
    }