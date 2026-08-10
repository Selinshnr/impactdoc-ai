"""Ollama üzerinden LLM destekli doküman değişiklik etki analizi."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from impactdoc_ai.analysis.prompt_builder import (
    build_change_prompt,
    build_system_prompt,
)
from impactdoc_ai.analysis.role_catalog import (
    detect_document_category,
    get_role_pool,
)
from impactdoc_ai.analysis.response_validator import (
    validate_response_payload,
)

from impactdoc_ai.analysis.impact_scoring import (
    ImpactLevel,
    calculate_impact_decision,
)

from impactdoc_ai.analysis.impact_scoring import (
    ImpactLevel,
    calculate_impact_decision,
)

from impactdoc_ai.comparison import (
    ChangeType,
    ComparisonResult,
    TextChange,
)


DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:4b"


@dataclass
class LLMChangeImpact:
    """Tek bir değişiklik için LLM etki analizi."""

    change_id: str
    change_type: ChangeType
    old_text: str | None
    new_text: str | None
    affected_roles: list[str]

    # Nihai karar. Eski kodlarla uyumluluk için adı korunur.
    impact_level: ImpactLevel

    # LLM'nin ilk önerisi ve merkezi motorun açıklanabilir sonucu.
    llm_impact_level: ImpactLevel
    rule_impact_level: ImpactLevel
    impact_source: str
    impact_decision_reason: str
    matched_impact_keywords: list[str]
    applied_impact_rules: list[str]

    reason: str
    recommended_actions: list[str]
    confidence: float

    change_category: str
    change_category_label: str
    classification_confidence: float
    classification_reason: str
    classification_source: str

    old_position: int | None = None
    new_position: int | None = None
    similarity_score: float | None = None
    model_name: str = DEFAULT_MODEL

    def to_dict(self) -> dict[str, Any]:
        """Analiz sonucunu JSON uyumlu sözlüğe dönüştürür."""

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
            "llm_impact_level": self.llm_impact_level.value,
            "rule_impact_level": self.rule_impact_level.value,
            "impact_source": self.impact_source,
            "impact_decision_reason": (
                self.impact_decision_reason
            ),
            "matched_impact_keywords": (
                self.matched_impact_keywords
            ),
            "applied_impact_rules": (
                self.applied_impact_rules
            ),
            "reason": self.reason,
            "recommended_actions": self.recommended_actions,
            "confidence": self.confidence,
            "model_name": self.model_name,
            "change_category": self.change_category,
            "change_category_label": self.change_category_label,
            "classification_confidence": self.classification_confidence,
            "classification_reason": self.classification_reason,
            "classification_source": self.classification_source,
        }


@dataclass
class LLMImpactAnalysisResult:
    """Tüm değişikliklere ait LLM etki analizi."""

    old_file_name: str
    new_file_name: str
    model_name: str
    impacts: list[LLMChangeImpact]

    @property
    def high_impact_count(self) -> int:
        return sum(
            impact.impact_level == ImpactLevel.HIGH
            for impact in self.impacts
        )

    @property
    def medium_impact_count(self) -> int:
        return sum(
            impact.impact_level == ImpactLevel.MEDIUM
            for impact in self.impacts
        )

    @property
    def low_impact_count(self) -> int:
        return sum(
            impact.impact_level == ImpactLevel.LOW
            for impact in self.impacts
        )

    @property
    def affected_roles(self) -> list[str]:
        roles = {
            role
            for impact in self.impacts
            for role in impact.affected_roles
        }
        return sorted(roles)

    def role_change_counts(self) -> dict[str, int]:
        """Her rolün etkilendiği değişiklik sayısını döndürür."""

        counts: dict[str, int] = {}

        for impact in self.impacts:
            for role in impact.affected_roles:
                counts[role] = counts.get(role, 0) + 1

        return dict(
            sorted(
                counts.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        )

    def category_counts(self) -> dict[str, int]:
        """Her değişiklik kategorisinin kaç kez görüldüğünü döndürür."""

        counts: dict[str, int] = {}

        for impact in self.impacts:
            category = impact.change_category
            counts[category] = counts.get(category, 0) + 1

        return dict(
            sorted(
                counts.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        )

    def classification_source_counts(self) -> dict[str, int]:
        """Sınıflandırma kaynaklarının kullanım sayılarını döndürür."""

        counts: dict[str, int] = {}

        for impact in self.impacts:
            source = impact.classification_source
            counts[source] = counts.get(source, 0) + 1

        return dict(
            sorted(
                counts.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        )

    def category_percentages(self) -> dict[str, float]:
        """Değişiklik kategorilerinin yüzde dağılımını döndürür."""

        total = len(self.impacts)

        if total == 0:
            return {}

        counts = self.category_counts()

        return {
            category: round(
                (count / total) * 100,
                2,
            )
            for category, count in counts.items()
        }

    def summary(self) -> dict[str, Any]:
        """Analiz özetini döndürür."""

        return {
            "old_file_name": self.old_file_name,
            "new_file_name": self.new_file_name,
            "model_name": self.model_name,
            "analyzed_change_count": len(self.impacts),
            "high_impact": self.high_impact_count,
            "medium_impact": self.medium_impact_count,
            "low_impact": self.low_impact_count,
            "affected_roles": self.affected_roles,
            "role_change_counts": self.role_change_counts(),
            "category_counts": self.category_counts(),
            "category_percentages": self.category_percentages(),
            "classification_source_counts": (
                self.classification_source_counts()
            ),
        }


IMPACT_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "affected_roles": {
            "type": "array",
            "items": {
                "type": "string",
            },
            "maxItems": 3,
        },
        "impact_level": {
            "type": "string",
            "enum": [
                "low",
                "medium",
                "high",
            ],
        },
        "reason": {
            "type": "string",
        },
        "recommended_actions": {
            "type": "array",
            "items": {
                "type": "string",
            },
            "minItems": 1,
            "maxItems": 3,
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
    },
    "required": [
        "affected_roles",
        "impact_level",
        "reason",
        "recommended_actions",
        "confidence",
    ],
    "additionalProperties": False,
}


def post_json(
    url: str,
    payload: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    """HTTP POST isteği gönderir ve JSON yanıtını döndürür."""

    encoded_payload = json.dumps(
        payload,
        ensure_ascii=False,
    ).encode("utf-8")

    http_request = request.Request(
        url=url,
        data=encoded_payload,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(
            http_request,
            timeout=timeout,
        ) as response:
            response_text = response.read().decode("utf-8")

    except error.HTTPError as exc:
        error_body = exc.read().decode(
            "utf-8",
            errors="replace",
        )
        raise RuntimeError(
            f"Ollama HTTP hatası ({exc.code}): {error_body}"
        ) from exc

    except error.URLError as exc:
        raise RuntimeError(
            "Ollama API'ye bağlanılamadı. "
            "Ollama'nın çalıştığını ve "
            f"{url} adresinin erişilebilir olduğunu kontrol et."
        ) from exc

    except TimeoutError as exc:
        raise RuntimeError(
            f"Ollama isteği {timeout} saniye içinde tamamlanamadı."
        ) from exc

    try:
        response_data = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Ollama API geçerli JSON döndürmedi."
        ) from exc

    if not isinstance(response_data, dict):
        raise RuntimeError(
            "Ollama API yanıtı JSON nesnesi olmalıdır."
        )

    return response_data


def call_ollama_for_change(
    change: TextChange,
    change_number: int,
    role_pool: list[str],
    document_category: str,
    classification=None,
    model_name: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 180,
) -> dict[str, Any]:
    """Bir değişikliği Ollama modeliyle analiz eder."""

    endpoint = f"{ollama_url.rstrip('/')}/api/chat"

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": build_system_prompt(
                    role_pool=role_pool,
                    document_category=document_category,
                    classification=classification,
                ),
            },
            {
                "role": "user",
                "content": build_change_prompt(
                    change=change,
                    change_number=change_number,
                    role_pool=role_pool,
                    document_category=document_category,
                    classification=classification,
                ),
            },
        ],
        "format": IMPACT_RESPONSE_SCHEMA,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.1,
            "seed": 42,
        },
    }

    response_data = post_json(
        url=endpoint,
        payload=payload,
        timeout=timeout,
    )

    message = response_data.get("message")

    if not isinstance(message, dict):
        raise RuntimeError(
            "Ollama yanıtında 'message' alanı bulunamadı."
        )

    content = message.get("content")

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(
            "Ollama yanıtında analiz içeriği bulunamadı."
        )

    try:
        parsed_content = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Model yanıtı geçerli yapılandırılmış JSON değil."
        ) from exc

    if not isinstance(parsed_content, dict):
        raise RuntimeError(
            "Model yanıtı bir JSON nesnesi olmalıdır."
        )

    return parsed_content


def parse_llm_impact(
    response_data: dict[str, Any],
    change: TextChange,
    change_number: int,
    role_pool: list[str],
    model_name: str,
    classification,
) -> LLMChangeImpact:
    """Model çıktısını doğrulanmış etki nesnesine dönüştürür."""

    validated_data = validate_response_payload(
        response_data=response_data,
        role_pool=role_pool,
        change=change,
    )

    try:
        llm_impact_level = ImpactLevel(
            validated_data["impact_level"]
        )

    except ValueError as exc:
        raise ValueError(
            "Model geçerli bir impact_level üretmedi."
        ) from exc

    impact_decision = calculate_impact_decision(
        change=change,
        classification=classification,
        affected_roles=validated_data[
            "affected_roles"
        ],
        llm_level=llm_impact_level.value,
    )

    final_impact_level = ImpactLevel(
        impact_decision.final_level.value
    )

    rule_impact_level = ImpactLevel(
        impact_decision.rule_level.value
    )

    return LLMChangeImpact(
        change_id=f"CHG-{change_number:04d}",
        change_type=change.change_type,
        old_text=change.old_text,
        new_text=change.new_text,
        old_position=change.old_position,
        new_position=change.new_position,
        similarity_score=change.similarity_score,
        change_category=classification.category.value,
        change_category_label=classification.category.label,
        classification_confidence=classification.confidence,
        classification_reason=classification.reason,
        classification_source=classification.source,
                affected_roles=validated_data[
            "affected_roles"
        ],
        impact_level=final_impact_level,
        llm_impact_level=llm_impact_level,
        rule_impact_level=rule_impact_level,
        impact_source=impact_decision.source,
        impact_decision_reason=impact_decision.reason,
        matched_impact_keywords=list(
            impact_decision.matched_keywords
        ),
        applied_impact_rules=list(
            impact_decision.applied_rules
        ),
        reason=validated_data["reason"],
        recommended_actions=validated_data[
            "recommended_actions"
        ],
        confidence=validated_data["confidence"],
        model_name=model_name,
    )


def analyze_change_with_llm(
    change: TextChange,
    change_number: int,
    role_pool: list[str],
    document_category: str,
    classification=None,
    model_name: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 180,
) -> LLMChangeImpact:
    """Tek değişikliği LLM ile analiz eder."""

    response_data = call_ollama_for_change(
        change=change,
        change_number=change_number,
        role_pool=role_pool,
        document_category=document_category,
        classification=classification,
        model_name=model_name,
        ollama_url=ollama_url,
        timeout=timeout,
    )

    return parse_llm_impact(
        response_data=response_data,
        change=change,
        change_number=change_number,
        role_pool=role_pool,
        model_name=model_name,
        classification=classification,
    )


def analyze_role_impacts_with_llm(
    comparison_result: ComparisonResult,
    model_name: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 180,
    include_unchanged: bool = False,
    limit: int | None = None,
) -> LLMImpactAnalysisResult:
    """Karşılaştırma sonucunu LLM ile rol bazında analiz eder."""

    analyzable_changes = [
        change
        for change in comparison_result.changes
        if include_unchanged
        or change.change_type != ChangeType.UNCHANGED
    ]

    if limit is not None:
        if limit < 1:
            raise ValueError("limit en az 1 olmalıdır.")

        analyzable_changes = analyzable_changes[:limit]

    document_text = " ".join(
        change.new_text or change.old_text or ""
        for change in analyzable_changes
    )

    document_category = detect_document_category(
        old_file_name=comparison_result.old_file_name,
        new_file_name=comparison_result.new_file_name,
        document_text=document_text,
    )

    print(f"Doküman kategorisi: {document_category}")

    impacts: list[LLMChangeImpact] = []

    # Yerel import, change_classifier ile oluşabilecek döngüsel
    # import riskini önler.
    from impactdoc_ai.analysis.change_classifier import (
        classify_change_with_ollama,
    )

    for index, change in enumerate(
        analyzable_changes,
        start=1,
    ):
        print(
            f"LLM analizi: {index}/{len(analyzable_changes)} "
            f"({change.change_type.value})"
        )

        classification = classify_change_with_ollama(
            old_text=change.old_text or "",
            new_text=change.new_text or "",
            model_name=model_name,
            ollama_url=ollama_url,
            timeout=timeout,
        )

        print(
            "Değişiklik kategorisi: "
            f"{classification.category.label} "
            f"({classification.category.value}, "
            f"güven={classification.confidence:.2f})"
        )
        print(
            "Sınıflandırma gerekçesi: "
            f"{classification.reason}"
        )

        role_pool = get_role_pool(
    change=change,
    document_category=document_category,
    classification=classification,
)

        if not role_pool:
            raise RuntimeError(
                f"CHG-{index:04d} için rol havuzu oluşturulamadı."
            )

        print("Rol havuzu: " + ", ".join(role_pool))

        impact = analyze_change_with_llm(
            change=change,
            change_number=index,
            role_pool=role_pool,
            document_category=document_category,
            classification=classification,
            model_name=model_name,
            ollama_url=ollama_url,
            timeout=timeout,
        )

        impacts.append(impact)

    return LLMImpactAnalysisResult(
        old_file_name=comparison_result.old_file_name,
        new_file_name=comparison_result.new_file_name,
        model_name=model_name,
        impacts=impacts,
    )

