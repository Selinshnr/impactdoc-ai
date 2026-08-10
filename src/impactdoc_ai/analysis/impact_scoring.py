"""Merkezi değişiklik etki seviyesi hesaplama modülü."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from impactdoc_ai.analysis.change_category import ChangeClassification
from impactdoc_ai.analysis.impact_rules import (
    CATEGORY_MINIMUM_LEVEL_VALUE,
    HIGH_IMPACT_KEYWORDS,
    LOW_IMPACT_KEYWORDS,
    MEDIUM_IMPACT_KEYWORDS,
)
from impactdoc_ai.comparison import ChangeType, TextChange

class ImpactLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

_IMPACT_SCORE = {ImpactLevel.LOW: 1, ImpactLevel.MEDIUM: 2, ImpactLevel.HIGH: 3}

@dataclass(frozen=True)
class ImpactDecision:
    final_level: ImpactLevel
    llm_level: ImpactLevel
    rule_level: ImpactLevel
    source: str
    reason: str
    matched_keywords: tuple[str, ...]
    applied_rules: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "final_impact_level": self.final_level.value,
            "llm_impact_level": self.llm_level.value,
            "rule_impact_level": self.rule_level.value,
            "impact_source": self.source,
            "impact_reason": self.reason,
            "matched_impact_keywords": list(self.matched_keywords),
            "applied_impact_rules": list(self.applied_rules),
        }

def normalize_text(text: str | None) -> str:
    return "" if not text else " ".join(text.casefold().split())

def combine_change_text(change: TextChange) -> str:
    return " ".join(
        part for part in (normalize_text(change.old_text), normalize_text(change.new_text)) if part
    )

def parse_impact_level(value: ImpactLevel | str) -> ImpactLevel:
    if isinstance(value, ImpactLevel):
        return value
    if not isinstance(value, str):
        raise TypeError("Etki seviyesi ImpactLevel veya metin olmalıdır.")
    try:
        return ImpactLevel(value.strip().casefold())
    except ValueError as exc:
        raise ValueError("Etki seviyesi low, medium veya high olmalıdır.") from exc

def maximum_level(*levels: ImpactLevel) -> ImpactLevel:
    if not levels:
        raise ValueError("En az bir etki seviyesi verilmelidir.")
    return max(levels, key=lambda level: _IMPACT_SCORE[level])

def find_matched_keywords(text: str, keywords: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({keyword for keyword in keywords if keyword in text}))

def calculate_rule_level(
    change: TextChange,
    classification: ChangeClassification,
    affected_roles: list[str],
) -> tuple[ImpactLevel, tuple[str, ...], tuple[str, ...]]:
    text = combine_change_text(change)
    high_matches = find_matched_keywords(text, HIGH_IMPACT_KEYWORDS)
    medium_matches = find_matched_keywords(text, MEDIUM_IMPACT_KEYWORDS)
    low_matches = find_matched_keywords(text, LOW_IMPACT_KEYWORDS)

    applied_rules: list[str] = []
    category_level = ImpactLevel(CATEGORY_MINIMUM_LEVEL_VALUE[classification.category])
    rule_level = category_level
    applied_rules.append(
        f"Kategori alt sınırı: {classification.category.value} -> {category_level.value}"
    )

    scope_expansion = (
        classification.category.value == "definition_change"
        and any(term in text for term in ("kapsar", "kapsam"))
        and any(term in text for term in ("birim", "çalışan", "insan kaynakları", "bilgi işlem", "bilgi güvenliği"))
    )

    if scope_expansion:
        rule_level = maximum_level(rule_level, ImpactLevel.MEDIUM)
        applied_rules.append(
            "Doküman kapsamına yeni organizasyon birimi veya rol grubu eklenmiştir."
        )

    if high_matches:
        rule_level = ImpactLevel.HIGH
        applied_rules.append(
            "Kritik güvenlik, erişim veya otomatik hesap sonlandırma ifadesi bulundu."
        )
    elif medium_matches:
        rule_level = maximum_level(rule_level, ImpactLevel.MEDIUM)
        applied_rules.append(
            "Süreç, onay, operasyon veya hesap yönetimi ifadesi bulundu."
        )
    elif low_matches:
        applied_rules.append("Biçimsel veya doküman bilgisi ifadesi bulundu.")

    if change.change_type == ChangeType.REMOVED:
        rule_level = maximum_level(rule_level, ImpactLevel.MEDIUM)
        applied_rules.append("Kaldırılan içerik en az medium kabul edildi.")
    elif change.change_type == ChangeType.ADDED:
        rule_level = maximum_level(rule_level, ImpactLevel.MEDIUM)
        applied_rules.append("Yeni eklenen içerik en az medium kabul edildi.")

    role_count = len({role.strip() for role in affected_roles if role.strip()})
    if role_count >= 2:
        applied_rules.append(
            f"{role_count} rol etkilendi; rol sayısı tek başına etki seviyesini yükseltmedi."
        )

    matched_keywords = tuple(sorted(set(high_matches + medium_matches + low_matches)))
    return rule_level, matched_keywords, tuple(applied_rules)

def create_decision_reason(
    llm_level: ImpactLevel,
    rule_level: ImpactLevel,
    final_level: ImpactLevel,
    classification: ChangeClassification,
    affected_roles: list[str],
    applied_rules: tuple[str, ...],
) -> str:
    role_count = len({role.strip() for role in affected_roles if role.strip()})
    if final_level == llm_level == rule_level:
        decision_text = "LLM önerisi ile kural tabanlı değerlendirme aynı seviyede sonuçlanmıştır."
    elif final_level == rule_level:
        decision_text = "Kural tabanlı değerlendirme, LLM önerisinden daha yüksek bir etki seviyesi belirlemiştir."
    else:
        decision_text = "LLM tarafından önerilen seviye, kural tabanlı alt sınırdan daha yüksek olduğu için korunmuştur."

    return (
        f"{decision_text} Kategori: {classification.category.label}. "
        f"Etkilenen rol sayısı: {role_count}. Nihai etki seviyesi: {final_level.value}. "
        f"Uygulanan kurallar: {'; '.join(applied_rules)}"
    )

def calculate_impact_decision(
    change: TextChange,
    classification: ChangeClassification,
    affected_roles: list[str],
    llm_level: ImpactLevel | str,
) -> ImpactDecision:
    parsed_llm_level = parse_impact_level(llm_level)
    rule_level, matched_keywords, applied_rules = calculate_rule_level(
        change=change,
        classification=classification,
        affected_roles=affected_roles,
    )
    final_level = maximum_level(parsed_llm_level, rule_level)

    if final_level == parsed_llm_level == rule_level:
        source = "llm_and_rule_engine"
    elif final_level == rule_level:
        source = "rule_engine"
    else:
        source = "llm"

    reason = create_decision_reason(
        llm_level=parsed_llm_level,
        rule_level=rule_level,
        final_level=final_level,
        classification=classification,
        affected_roles=affected_roles,
        applied_rules=applied_rules,
    )

    return ImpactDecision(
        final_level=final_level,
        llm_level=parsed_llm_level,
        rule_level=rule_level,
        source=source,
        reason=reason,
        matched_keywords=matched_keywords,
        applied_rules=applied_rules,
    )