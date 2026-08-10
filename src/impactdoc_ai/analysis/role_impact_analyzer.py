"""Doküman değişiklikleri için rol bazlı etki analizi yapar."""
from dataclasses import dataclass
from typing import Any

from impactdoc_ai.comparison import ChangeType, ComparisonResult, TextChange
from impactdoc_ai.analysis.change_category import ChangeCategory, ChangeClassification
from impactdoc_ai.analysis.change_classifier import classify_change_by_rules
from impactdoc_ai.analysis.impact_scoring import ImpactLevel, calculate_impact_decision

@dataclass
class ChangeImpact:
    change_id: str
    change_type: ChangeType
    old_text: str | None
    new_text: str | None
    affected_roles: list[str]
    impact_level: ImpactLevel
    reason: str
    matched_keywords: list[str]
    old_position: int | None = None
    new_position: int | None = None
    similarity_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "change_id": self.change_id,
            "change_type": self.change_type.value,
            "old_text": self.old_text,
            "new_text": self.new_text,
            "old_position": self.old_position,
            "new_position": self.new_position,
            "similarity_score": self.similarity_score,
            "affected_roles": self.affected_roles,
            "impact_level": self.impact_level.value,
            "reason": self.reason,
            "matched_keywords": self.matched_keywords,
        }

@dataclass
class RoleImpactAnalysisResult:
    old_file_name: str
    new_file_name: str
    impacts: list[ChangeImpact]

    @property
    def high_impact_count(self) -> int:
        return sum(i.impact_level == ImpactLevel.HIGH for i in self.impacts)

    @property
    def medium_impact_count(self) -> int:
        return sum(i.impact_level == ImpactLevel.MEDIUM for i in self.impacts)

    @property
    def low_impact_count(self) -> int:
        return sum(i.impact_level == ImpactLevel.LOW for i in self.impacts)

    @property
    def affected_roles(self) -> list[str]:
        return sorted({r for i in self.impacts for r in i.affected_roles})

    def role_change_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for impact in self.impacts:
            for role in impact.affected_roles:
                counts[role] = counts.get(role, 0) + 1
        return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))

    def summary(self) -> dict[str, Any]:
        return {
            "old_file_name": self.old_file_name,
            "new_file_name": self.new_file_name,
            "analyzed_change_count": len(self.impacts),
            "high_impact": self.high_impact_count,
            "medium_impact": self.medium_impact_count,
            "low_impact": self.low_impact_count,
            "affected_roles": self.affected_roles,
            "role_change_counts": self.role_change_counts(),
        }

ROLE_NAMES: tuple[str, ...] = (
    "İnsan Kaynakları Uzmanı", "Birim Yöneticisi", "Çalışan",
    "Bilgi İşlem Uzmanı", "Bilgi Güvenliği Uzmanı", "Doküman Yöneticisi",
)

ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "İnsan Kaynakları Uzmanı": (
        "insan kaynakları", "personel dosyası", "personel sistemi",
        "izin kaydı", "sözleşme",
    ),
    "Birim Yöneticisi": (
        "birim yöneticisi", "yönetici", "iş sürekliliği",
    ),
    "Çalışan": (
        "çalışan", "izin talebi", "uzaktan çalışma talebi",
    ),
    "Bilgi İşlem Uzmanı": (
        "bilgi işlem", "vpn", "erişim tanımlar", "devre dışı", "kullanıcı hesabı",
    ),
    "Bilgi Güvenliği Uzmanı": (
        "bilgi güvenliği", "güvenlik onayı", "kritik sistem", "çok faktörlü",
        "kimlik doğrulama", "açık oturum", "uzaktan erişim", "erişim rol",
    ),
    "Doküman Yöneticisi": (
        "sürüm", "yürürlük tarihi", "dokümanın amacı", "prosedür", "kapsar",
    ),
}

def normalize_text(text: str | None) -> str:
    if text is None:
        return ""
    normalized = text.translate(str.maketrans({"İ": "i", "I": "ı"})).lower()
    return " ".join(normalized.split())

def combine_change_text(change: TextChange) -> str:
    return " ".join(
        part for part in (normalize_text(change.old_text), normalize_text(change.new_text)) if part
    )

def find_explicit_roles(text: str) -> list[str]:
    return [role for role in ROLE_NAMES if normalize_text(role) in text]

def find_affected_roles(text: str) -> tuple[list[str], list[str]]:
    explicit_roles = find_explicit_roles(text)
    if explicit_roles:
        matched_keywords = {
            keyword
            for role in explicit_roles
            for keyword in ROLE_KEYWORDS.get(role, ())
            if keyword in text
        }
        return explicit_roles, sorted(matched_keywords)

    affected_roles: list[str] = []
    matched_keywords: set[str] = set()
    for role, keywords in ROLE_KEYWORDS.items():
        role_matches = [keyword for keyword in keywords if keyword in text]
        if role_matches:
            affected_roles.append(role)
            matched_keywords.update(role_matches)

    if not affected_roles:
        affected_roles.append("Doküman Yöneticisi")

    return affected_roles, sorted(matched_keywords)

def analyze_change(change: TextChange, change_number: int) -> ChangeImpact:
    combined_text = combine_change_text(change)
    affected_roles, role_keywords = find_affected_roles(combined_text)

    classification = classify_change_by_rules(change.old_text or "", change.new_text or "")
    if classification is None:
        classification = ChangeClassification(
            category=ChangeCategory.OTHER,
            confidence=0.50,
            reason=(
                "Değişiklik deterministik kurallarla kesin olarak sınıflandırılamadı; "
                "etki anahtar kelimeler ve etkilenen roller üzerinden hesaplandı."
            ),
            source="manual",
        )

    impact_decision = calculate_impact_decision(
        change=change,
        classification=classification,
        affected_roles=affected_roles,
        llm_level=ImpactLevel.LOW,
    )

    matched_keywords = sorted(set(role_keywords + list(impact_decision.matched_keywords)))
    return ChangeImpact(
        change_id=f"change-{change_number}",
        change_type=change.change_type,
        old_text=change.old_text,
        new_text=change.new_text,
        old_position=change.old_position,
        new_position=change.new_position,
        similarity_score=change.similarity_score,
        affected_roles=affected_roles,
        impact_level=impact_decision.final_level,
        reason=impact_decision.reason,
        matched_keywords=matched_keywords,
    )

def analyze_role_impacts(
    comparison_result: ComparisonResult,
    include_unchanged: bool = False,
) -> RoleImpactAnalysisResult:
    analyzable_changes = [
        change
        for change in comparison_result.changes
        if include_unchanged or change.change_type != ChangeType.UNCHANGED
    ]

    impacts = [
        analyze_change(change=change, change_number=index)
        for index, change in enumerate(analyzable_changes, start=1)
    ]

    return RoleImpactAnalysisResult(
        old_file_name=comparison_result.old_file_name,
        new_file_name=comparison_result.new_file_name,
        impacts=impacts,
    )