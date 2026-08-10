"""LLM etki analizi sonuçlarını rol bazında JSON raporuna dönüştürür."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from impactdoc_ai.analysis import (
    LLMChangeImpact,
    LLMImpactAnalysisResult,
    ImpactLevel,
)


_IMPACT_PRIORITY = {
    ImpactLevel.HIGH: 3,
    ImpactLevel.MEDIUM: 2,
    ImpactLevel.LOW: 1,
}

def _unique_preserve_order(
    values: list[str],
) -> list[str]:
    """Metin listesindeki tekrarları sıralamayı koruyarak kaldırır."""

    unique_values: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = value.strip()

        if not normalized:
            continue

        key = normalized.casefold()

        if key in seen:
            continue

        seen.add(key)
        unique_values.append(normalized)

    return unique_values


def _impact_to_role_item(
    impact: LLMChangeImpact,
) -> dict[str, Any]:
    """Bir etki sonucunu rol raporunda kullanılacak yapıya dönüştürür."""

    return {
        "change_id": impact.change_id,
        "change_type": impact.change_type.value,
        "change_category": impact.change_category,
        "change_category_label": impact.change_category_label,
        "impact_level": impact.impact_level.value,
        "old_text": impact.old_text,
        "new_text": impact.new_text,
        "reason": impact.reason,
        "classification_reason": impact.classification_reason,
        "recommended_actions": impact.recommended_actions,
        "confidence": impact.confidence,
        "classification_confidence": (
            impact.classification_confidence
        ),
        "classification_source": impact.classification_source,
    }


def _build_role_summary(
    impacts: list[LLMChangeImpact],
) -> dict[str, Any]:
    """Bir rolün etki seviyesi ve kategori özetini üretir."""

    impact_level_counts = {
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    category_counts: dict[str, int] = {}

    for impact in impacts:
        impact_level_counts[
            impact.impact_level.value
        ] += 1

        category = impact.change_category
        category_counts[category] = (
            category_counts.get(category, 0) + 1
        )

    sorted_categories = dict(
        sorted(
            category_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )

    highest_impact = None

    if impact_level_counts["high"] > 0:
        highest_impact = "high"
    elif impact_level_counts["medium"] > 0:
        highest_impact = "medium"
    elif impact_level_counts["low"] > 0:
        highest_impact = "low"

    return {
        "total_change_count": len(impacts),
        "highest_impact_level": highest_impact,
        "impact_level_counts": impact_level_counts,
        "category_counts": sorted_categories,
    }


def role_analysis_result_to_dict(
    result: LLMImpactAnalysisResult,
) -> dict[str, Any]:
    """LLM analiz sonucunu rol merkezli JSON yapısına dönüştürür."""

    impacts_by_role: dict[str, list[LLMChangeImpact]] = {}

    for impact in result.impacts:
        for role in impact.affected_roles:
            impacts_by_role.setdefault(
                role,
                [],
            ).append(impact)

    role_reports: list[dict[str, Any]] = []

    for role, impacts in impacts_by_role.items():
        sorted_impacts = sorted(
            impacts,
            key=lambda item: (
                -_IMPACT_PRIORITY[item.impact_level],
                item.change_id,
            ),
        )

        recommended_actions = _unique_preserve_order(
            [
                action
                for impact in sorted_impacts
                for action in impact.recommended_actions
            ]
        )

        high_change_ids = [
            impact.change_id
            for impact in sorted_impacts
            if impact.impact_level == ImpactLevel.HIGH
        ]

        medium_change_ids = [
            impact.change_id
            for impact in sorted_impacts
            if impact.impact_level == ImpactLevel.MEDIUM
        ]

        low_change_ids = [
            impact.change_id
            for impact in sorted_impacts
            if impact.impact_level == ImpactLevel.LOW
        ]

        role_reports.append(
            {
                "role": role,
                "summary": _build_role_summary(
                    sorted_impacts
                ),
                "change_ids_by_impact": {
                    "high": high_change_ids,
                    "medium": medium_change_ids,
                    "low": low_change_ids,
                },
                "recommended_actions": recommended_actions,
                "impacts": [
                    _impact_to_role_item(impact)
                    for impact in sorted_impacts
                ],
            }
        )

    role_reports.sort(
        key=lambda item: (
            -item["summary"]["impact_level_counts"]["high"],
            -item["summary"]["impact_level_counts"]["medium"],
            -item["summary"]["total_change_count"],
            item["role"],
        )
    )

    return {
        "report_metadata": {
            "generated_at": datetime.now().isoformat(
                timespec="seconds"
            ),
            "report_type": "role_based_impact_analysis",
            "model_name": result.model_name,
        },
        "documents": {
            "old_file_name": result.old_file_name,
            "new_file_name": result.new_file_name,
        },
        "summary": {
            "role_count": len(role_reports),
            "analyzed_change_count": len(result.impacts),
            "roles": [
                item["role"]
                for item in role_reports
            ],
        },
        "roles": role_reports,
    }


def save_role_analysis_report(
    result: LLMImpactAnalysisResult,
    output_path: str | Path,
) -> Path:
    """Rol bazlı analiz sonucunu JSON dosyasına kaydeder."""

    destination = Path(output_path)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_data = role_analysis_result_to_dict(result)

    destination.write_text(
        json.dumps(
            report_data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return destination