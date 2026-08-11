"""LLM tabanlı doküman değişikliği sınıflandırıcısı."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from impactdoc_ai.analysis.change_category import (
    ChangeCategory,
    ChangeClassification,
    get_category_catalog,
    parse_change_category,
)
from impactdoc_ai.analysis.llm_impact_analyzer import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    post_json,
)


LLMGenerateFunction = Callable[[str], str]

DEFAULT_CLASSIFICATION_REASON = (
    "LLM geçerli bir içerik gerekçesi üretmedi. "
    "Sınıflandırma, eski ve yeni metin arasındaki "
    "somut değişiklik dikkate alınarak kabul edildi."
)

CLASSIFICATION_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": [
                "task_change",
                "process_change",
                "authority_change",
                "definition_change",
                "technical_change",
                "legislation_change",
                "other",
            ],
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
        "reason": {
            "type": "string",
        },
    },
    "required": [
        "category",
        "confidence",
        "reason",
    ],
}


def build_classification_prompt(
    old_text: str,
    new_text: str,
) -> str:
    """Değişiklik sınıflandırması için LLM prompt'u oluşturur."""

    categories = get_category_catalog()

    category_lines = "\n".join(
        (
            f"- {item['value']}: "
            f"{item['label']} — "
            f"{item['description']}"
        )
        for item in categories
    )

    return f"""
Sen bir kurumsal doküman değişiklik sınıflandırma uzmanısın.

Görevin, eski ve yeni metin arasındaki değişikliğin baskın kategorisini
belirlemektir.

Desteklenen kategoriler:

{category_lines}

Sınıflandırma kuralları:

1. Yalnızca desteklenen kategori değerlerinden birini kullan.
2. Birden fazla kategori mümkünse değişikliğin baskın etkisini seç.
3. Bir işin yapılma biçimi değişti diye otomatik olarak process_change seçme.
4. MFA, parola, kimlik doğrulama, yetkilendirme, şifreleme, ağ,
   sunucu, veri tabanı, API, entegrasyon, loglama veya bilgi güvenliği
   gereksinimleri technical_change olarak sınıflandırılmalıdır.
5. Onay, imza, karar, erişim veya kontrol yetkisi değişiyorsa
   authority_change seçilmelidir.
6. Bir rolün görevi veya sorumluluğu değişiyorsa task_change seçilmelidir.
7. İş akışının adımları, sırası, başvuru kanalı, formun yürütülme
   yöntemi veya süreç için tanımlanan süre/son tarih değişiyorsa ve
   baskın teknik güvenlik unsuru yoksa process_change seçilmelidir.
8. Kanun, yönetmelik, genelge veya uyum yükümlülüğü temel nedense
   legislation_change seçilmelidir.
9. Bir kavramın anlamı veya kapsamı değişiyorsa definition_change seçilmelidir.
10. confidence alanı 0.0 ile 1.0 arasında sayı olmalıdır.
11. reason kısa, açık ve değişikliğe özel olmalıdır.
12. Yalnızca geçerli JSON üret.
13. JSON dışında açıklama veya Markdown üretme.
14. reason alanı en fazla iki kısa cümle olmalıdır.
15. Gerekçede kategori kodunu, kural numarasını, prompt'u veya
    sınıflandırma talimatlarını anma.
16. Yalnızca eski ve yeni metin arasındaki somut farkı açıkla.
17. reason alanında "kurala göre", "kategoriye göre",
    "technical_change olduğu için" gibi ifadeler kullanma.
18. Sürüm numarası, revizyon numarası, doküman tarihi, başlık,
    numaralandırma veya yalnızca biçimsel doküman değişiklikleri
    technical_change değildir. Başka bir baskın kategori yoksa
    other olarak sınıflandırılmalıdır.
19. Yazılım, uygulama, sistem, API veya platform sürümünün değiştirilmesi
    doküman sürüm değişikliği değildir; teknik etkisi varsa technical_change seç.
20. Bir işlemin tamamlanma süresi veya son tarihi değişiyor ancak rolün temel
    sorumluluğu değişmiyorsa process_change seç.

Örnekler:

- "Form artık elektronik ortamda doldurulur."
  → process_change

- "Sisteme girişte MFA zorunludur."
  → technical_change

- "Talebi yalnızca birim yöneticisi onaylar."
  → authority_change

- "Çalışan aylık rapor hazırlar."
  → task_change

- "Doküman sürümü 1.0'dan 2.0'a çıkarılmıştır."
  → other

- "Revizyon tarihi 01.01.2026 olarak güncellenmiştir."
  → other

- "Sistemin yazılım sürümü 2.0'a yükseltilmiştir."
  → technical_change

Eski metin:
{old_text}

Yeni metin:
{new_text}

Beklenen çıktı biçimi:

{{
  "category": "process_change",
  "confidence": 0.90,
  "reason": "Değişiklik gerekçesi"
}}
""".strip()


def extract_json_object(response_text: str) -> dict[str, Any]:
    """LLM yanıtından JSON nesnesini çıkarır."""

    if not isinstance(response_text, str):
        raise TypeError("LLM yanıtı metin olmalıdır.")

    cleaned_text = response_text.strip()

    if not cleaned_text:
        raise ValueError("LLM boş yanıt döndürdü.")

    if cleaned_text.startswith("```"):
        cleaned_text = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned_text,
            flags=re.IGNORECASE,
        )
        cleaned_text = re.sub(
            r"\s*```$",
            "",
            cleaned_text,
        ).strip()

    try:
        parsed = json.loads(cleaned_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned_text, flags=re.DOTALL)

        if match is None:
            raise ValueError(
                "LLM yanıtında ayrıştırılabilir JSON nesnesi bulunamadı."
            )

        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ValueError(
                "LLM yanıtındaki JSON geçerli değil."
            ) from exc

    if not isinstance(parsed, dict):
        raise ValueError("LLM yanıtı bir JSON nesnesi olmalıdır.")

    return parsed


def clean_classification_reason(reason: str) -> str:
    """Prompt, kural ve kategori talimatlarını gerekçeden temizler."""

    if not isinstance(reason, str):
        raise TypeError("reason değeri metin olmalıdır.")

    forbidden_expressions = (
    "kurala göre",
    "kuralına göre",
    "kategoriye göre",
    "prompt'a göre",
    "prompt'a dayanarak",
    "talimatlara göre",
    "sınıflandırma kurallarına göre",
    "sınıflandırma, değişikliğin baskın etkisine göre yapılır",
    "olarak sınıflandırılır",
    "olarak sınıflandırılmalıdır",
    "olarak sınıflandırılmıştır",
    "olarak kabul edilir",
    "kategori seçilmelidir",
    "seçilmelidir",
    "teknik güvenlik unsuru yoksa",
    "baskın teknik güvenlik unsuru",
)

    category_codes_pattern = re.compile(
        r"\b("
        r"task_change|"
        r"process_change|"
        r"authority_change|"
        r"definition_change|"
        r"technical_change|"
        r"legislation_change|"
        r"other"
        r")\b",
        flags=re.IGNORECASE,
    )

    sentences = [
        sentence.strip()
        for sentence in re.split(
            r"(?<=[.!?])\s+",
            reason.strip(),
        )
        if sentence.strip()
    ]

    clean_sentences = [
        sentence
        for sentence in sentences
        if not any(
            expression in sentence.lower()
            for expression in forbidden_expressions
        )
        and not re.search(
            r"\bkural\s*\d+\b",
            sentence,
            flags=re.IGNORECASE,
        )
        and not category_codes_pattern.search(sentence)
    ]

    cleaned_reason = " ".join(clean_sentences).strip()

    if not cleaned_reason:
        return DEFAULT_CLASSIFICATION_REASON

    return cleaned_reason


def generate_fallback_reason(
    old_text: str,
    new_text: str,
    category: ChangeCategory,
) -> str:
    """LLM gerekçe üretemediğinde içerik tabanlı kısa gerekçe üretir."""

    old_text = (old_text or "").strip()
    new_text = (new_text or "").strip()

    if not old_text and new_text:
        return f"Yeni içerik eklenmiştir: '{new_text}'."

    if old_text and not new_text:
        return f"İçerik kaldırılmıştır: '{old_text}'."

    if category == ChangeCategory.PROCESS:
        return (
            "İş sürecinin uygulanış biçimi eski ve yeni metin "
            "karşılaştırılarak güncellenmiştir."
        )

    if category == ChangeCategory.AUTHORITY:
        return (
            "Görev, onay veya karar sorumluluğunu etkileyen "
            "bir değişiklik bulunmaktadır."
        )

    if category == ChangeCategory.TECHNICAL:
        return (
            "Teknik altyapıyı veya bilgi güvenliği gereksinimlerini "
            "etkileyen bir değişiklik bulunmaktadır."
        )

    if category == ChangeCategory.DEFINITION:
        return (
            "Dokümanın kapsamını veya tanımını etkileyen "
            "bir değişiklik yapılmıştır."
        )

    if category == ChangeCategory.TASK:
        return (
            "Bir rolün görev veya sorumluluğunu etkileyen "
            "bir değişiklik yapılmıştır."
        )

    if category == ChangeCategory.LEGISLATION:
        return (
            "Mevzuat veya uyum yükümlülüğünü etkileyen "
            "bir değişiklik yapılmıştır."
        )

    return "Eski ve yeni metin arasında içerik değişikliği bulunmaktadır."

def validate_classification_reason_semantics(
    classification: ChangeClassification,
    old_text: str,
    new_text: str,
) -> ChangeClassification:
    """Gerekçenin değişiklik türüyle anlamsal olarak uyumlu olmasını sağlar."""

    old_clean = (old_text or "").strip()
    new_clean = (new_text or "").strip()
    reason_normalized = classification.reason.strip().lower()

    # ADDED:
    # Eski metin yokken LLM eski metin varmış gibi gerekçe üretemez.
    if not old_clean and new_clean:
        invalid_added_reason_terms = (
            "eski metin",
            "önceki metin",
            "eski içerik",
            "önceki içerik",
            "eski ifad",
        )

        same_content_terms = (
            "aynıdır",
            "aynı kalmıştır",
            "değişmemiştir",
            "değişiklik yok",
            "fark bulunmamaktadır",
        )

        if (
            any(
                term in reason_normalized
                for term in invalid_added_reason_terms
            )
            or any(
                term in reason_normalized
                for term in same_content_terms
            )
        ):
            return ChangeClassification(
                category=classification.category,
                confidence=classification.confidence,
                reason=generate_fallback_reason(
                    old_text="",
                    new_text=new_clean,
                    category=classification.category,
                ),
                source=classification.source,
            )

    # REMOVED:
    # Yeni metin yokken LLM yeni metin varmış gibi gerekçe üretemez.
    if old_clean and not new_clean:
        invalid_removed_reason_terms = (
            "yeni metin",
            "yeni içerik",
            "yeni ifad",
            "eklenmiştir",
            "eklenmiştir:",
        )

        if any(
            term in reason_normalized
            for term in invalid_removed_reason_terms
        ):
            return ChangeClassification(
                category=classification.category,
                confidence=classification.confidence,
                reason=generate_fallback_reason(
                    old_text=old_clean,
                    new_text="",
                    category=classification.category,
                ),
                source=classification.source,
            )

    return classification

def enrich_classification_reason(
    classification: ChangeClassification,
    old_text: str,
    new_text: str,
) -> ChangeClassification:
    """Gerekçeyi doğrular ve gerekirse içerik tabanlı gerekçeyle değiştirir."""

    classification = validate_classification_reason_semantics(
        classification=classification,
        old_text=old_text,
        new_text=new_text,
    )

    if classification.reason != DEFAULT_CLASSIFICATION_REASON:
        return classification

    generated_reason = generate_fallback_reason(
        old_text=old_text,
        new_text=new_text,
        category=classification.category,
    )

    return ChangeClassification(
        category=classification.category,
        confidence=classification.confidence,
        reason=generated_reason,
        source=classification.source,
    )


def validate_classification_response(
    response_data: dict[str, Any],
) -> ChangeClassification:
    """LLM sınıflandırma yanıtını doğrular ve veri modeline dönüştürür."""

    required_fields = {
        "category",
        "confidence",
        "reason",
    }

    missing_fields = required_fields - response_data.keys()

    if missing_fields:
        missing_text = ", ".join(sorted(missing_fields))
        raise ValueError(
            f"LLM yanıtında zorunlu alanlar eksik: {missing_text}"
        )

    category = parse_change_category(response_data["category"])
    confidence_value = response_data["confidence"]

    if isinstance(confidence_value, bool):
        raise TypeError("confidence değeri sayı olmalıdır.")

    try:
        confidence = float(confidence_value)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "confidence değeri sayıya dönüştürülebilir olmalıdır."
        ) from exc

    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence değeri 0.0 ile 1.0 arasında olmalıdır.")

    reason = response_data["reason"]

    if not isinstance(reason, str):
        raise TypeError("reason değeri metin olmalıdır.")

    cleaned_reason = clean_classification_reason(reason)

    return ChangeClassification(
        category=category,
        confidence=confidence,
        reason=cleaned_reason,
        source="ollama",
    )


def parse_classification_response(
    response_text: str,
) -> ChangeClassification:
    """Ham LLM yanıtını doğrulanmış sınıflandırmaya dönüştürür."""

    response_data = extract_json_object(response_text)
    return validate_classification_response(response_data)


def validate_classification_semantics(
    classification: ChangeClassification,
    old_text: str,
    new_text: str,
) -> ChangeClassification:
    """Kategoriyi eski ve yeni metnin somut anlamıyla doğrular.

    Yalnızca yüksek kesinlikli durumlarda sınıflandırmayı düzeltir.
    Belirsiz değişikliklerde LLM sonucunu korur.
    """

    old_clean = old_text.strip()
    new_clean = new_text.strip()
    old_normalized = old_clean.lower()
    new_normalized = new_clean.lower()
    reason_normalized = classification.reason.strip().lower()
    combined_text = f"{old_normalized} {new_normalized}"

    # Örnek: "6. İŞTEN AYRILMA" -> "7. İŞTEN AYRILMA"
    heading_pattern = re.compile(r"^\s*\d+(?:\.\d+)*[.)]?\s*")

    old_without_number = heading_pattern.sub(
        "",
        old_normalized,
    ).strip()
    new_without_number = heading_pattern.sub(
        "",
        new_normalized,
    ).strip()

    old_has_heading_number = bool(heading_pattern.match(old_normalized))
    new_has_heading_number = bool(heading_pattern.match(new_normalized))

    numbering_only_change = (
        bool(old_clean)
        and bool(new_clean)
        and old_clean != new_clean
        and old_has_heading_number
        and new_has_heading_number
        and bool(old_without_number)
        and old_without_number == new_without_number
    )

    if numbering_only_change:
        return ChangeClassification(
            category=ChangeCategory.OTHER,
            confidence=0.99,
            reason=(
                "Değişiklik yalnızca bölüm veya başlık "
                "numaralandırmasını güncellemektedir."
            ),
            source="rule",
        )

    authority_negation_expressions = (
        "yetki değişikliği bulunmamıştır",
        "yetki değişmemiştir",
        "onay yetkisi değişmemiştir",
        "onay yetkisi ile ilgili değişiklik bulunmamıştır",
        "onay yetkisiyle ilgili değişiklik bulunmamıştır",
        "yetki ile ilgili değişiklik bulunmamıştır",
        "yetkiyle ilgili değişiklik bulunmamıştır",
    )

    authority_reason_conflict = (
        classification.category == ChangeCategory.AUTHORITY
        and any(
            expression in reason_normalized
            for expression in authority_negation_expressions
        )
    )

    if authority_reason_conflict:
        process_terms = (
            "portal",
            "sistem",
            "e-posta",
            "elektronik",
            "form",
            "başvuru",
            "talep",
            "iş akışı",
            "yöntem",
            "kanal",
        )

        if any(term in combined_text for term in process_terms):
            corrected_category = ChangeCategory.PROCESS
            corrected_reason = (
                "Yetki sahibi değişmemiş, işlemin yürütülme "
                "yöntemi veya kullanılan kanal güncellenmiştir."
            )
        else:
            corrected_category = ChangeCategory.OTHER
            corrected_reason = (
                "Metin değişikliği yeni bir onay veya karar "
                "yetkisi oluşturmamaktadır."
            )

        return ChangeClassification(
            category=corrected_category,
            confidence=0.85,
            reason=corrected_reason,
            source="rule",
        )

    coverage_terms = (
        "kapsar",
        "kapsam",
        "kapsamına",
        "kapsamında",
    )

    technical_requirement_terms = (
        "mfa",
        "çok faktörlü",
        "kimlik doğrulama",
        "vpn",
        "api",
        "sunucu",
        "veri tabanı",
        "veritabanı",
        "şifreleme",
        "erişim yetkisi",
        "kullanıcı hesabı",
        "güvenlik onayı",
        "kritik sistem",
    )

    coverage_only_change = (
        classification.category == ChangeCategory.TECHNICAL
        and any(term in combined_text for term in coverage_terms)
        and not any(
            term in combined_text
            for term in technical_requirement_terms
        )
    )


    if coverage_only_change:
        return ChangeClassification(
            category=ChangeCategory.DEFINITION,
            confidence=0.90,
            reason=(
                "Değişiklik teknik bir gereksinim getirmemekte, "
                "dokümanın kapsadığı birim veya tarafları "
                "genişletmektedir."
            ),
            source="rule",
        )

    # Yalnızca yeni bir bölüm veya rol başlığı eklenmişse,
    # bunu süreç/teknik değişiklik olarak yorumlamayız.
    # Örnekler:
    # "3.4 Bilgi Güvenliği Uzmanı"
    # "6. UZAKTAN ÇALIŞMA"
    heading_action_terms = (
        "eder",
        "verir",
        "onaylar",
        "tanımlar",
        "oluşturur",
        "kontrol",
        "değerlendir",
        "hazırla",
        "doğrula",
        "takip",
        "rapor",
        "kaydet",
        "zorunlu",
        "gerekir",
        "gereklidir",
    )

    added_heading_only = (
        not old_clean
        and bool(new_clean)
        and len(new_clean.split()) <= 6
        and not new_clean.endswith(".")
        and not any(
            term in new_normalized
            for term in heading_action_terms
        )
    )

    if added_heading_only:
        return ChangeClassification(
            category=ChangeCategory.OTHER,
            confidence=0.98,
            reason=(
                "Değişiklik yalnızca yeni bir bölüm veya rol "
                "başlığı eklemektedir."
            ),
            source="rule",
        )

    # Yeni bir cümle doğrudan bir rolün yapacağı işi tanımlıyorsa,
    # teknik terimler geçse bile asıl değişiklik görev/sorumluluk eklenmesidir.
    # Örnek: "Kullanıcı erişim rollerini kontrol eder."
    task_action_terms = (
        "kontrol eder",
        "değerlendirir",
        "hazırlar",
        "doğrular",
        "takip eder",
        "raporlar",
        "kaydeder",
    )
    requirement_terms = (
        "zorunludur",
        "zorunlu",
        "gereklidir",
        "gerekir",
        "kullanılmalıdır",
        "uygulanmalıdır",
    )

    # Bazı eylem cümleleri görev fiili içerse de aslında doğrudan bir
    # güvenlik kontrolünü tanımlar. Bu tür yüksek kesinlikli teknik
    # ifadeler task_change kuralı tarafından ezilmemelidir.
    strong_security_control_terms = (
        "açık oturum",
        "mfa",
        "çok faktörlü",
        "kimlik doğrulama",
        "vpn",
        "şifreleme",
        "parola",
        "güvenlik onayı",
        "kritik sistem",
    )

    added_task_statement = (
        not old_clean
        and bool(new_clean)
        and any(term in new_normalized for term in task_action_terms)
        and not any(term in new_normalized for term in requirement_terms)
        and not any(
            term in new_normalized
            for term in strong_security_control_terms
        )
    )

    if added_task_statement:
        return ChangeClassification(
            category=ChangeCategory.TASK,
            confidence=0.94,
            reason=(
                "Yeni metin bir rolün yerine getireceği görevi veya "
                "sorumluluğu tanımlamaktadır."
            ),
            source="rule",
        )

    # Zimmetli cihaz/kart gibi varlıkların teslim kapsamının genişlemesi
    # teknik altyapıyı değiştirmez; işten ayrılış sürecindeki teslim adımını
    # genişletir.
    handover_terms = (
        "teslim edilir",
        "teslim eder",
        "iade edilir",
        "iade eder",
    )
    asset_terms = (
        "zimmetli cihaz",
        "kurumsal kart",
        "ekipman",
        "demirbaş",
    )

    asset_handover_change = (
        bool(old_clean)
        and bool(new_clean)
        and old_clean != new_clean
        and any(term in combined_text for term in handover_terms)
        and any(term in combined_text for term in asset_terms)
    )

    if asset_handover_change:
        return ChangeClassification(
            category=ChangeCategory.PROCESS,
            confidence=0.95,
            reason=(
                "Değişiklik işten ayrılış sürecinde teslim veya iade "
                "edilecek varlıkların kapsamını genişletmektedir."
            ),
            source="rule",
        )

    return classification


def classify_change_by_rules(
    old_text: str,
    new_text: str,
) -> ChangeClassification | None:
    """Açık değişiklikleri deterministik kurallarla sınıflandırır.

    Kesin bir kural eşleşmesi yoksa None döndürür ve karar LLM'e bırakılır.
    """

    old_normalized = old_text.strip().lower()
    new_normalized = new_text.strip().lower()
    combined_text = f"{old_normalized} {new_normalized}"

    # Yazılım/sistem sürümü teknik bir değişikliktir; doküman metadata
    # kurallarından önce kontrol edilerek yanlışlıkla OTHER seçilmesi önlenir.
    software_version_terms = (
        "yazılım sürümü",
        "uygulama sürümü",
        "sistem sürümü",
        "api sürümü",
        "platform sürümü",
    )

    if any(term in combined_text for term in software_version_terms):
        return ChangeClassification(
            category=ChangeCategory.TECHNICAL,
            confidence=0.98,
            reason=(
                "Değişiklik kullanılan yazılım veya sistem sürümünü "
                "güncellemektedir."
            ),
            source="rule",
        )

    # Doküman sürümü veya revizyon numarası değişikliği.
    document_version_terms = (
        "doküman sürümü",
        "doküman versiyonu",
        "revizyon no",
        "revizyon numarası",
        "doküman revizyonu",
    )

    # Bazı dokümanlarda metadata alanı yalnızca "Sürüm: 1.0" biçimindedir.
    # Bu kısa biçimi yalnızca satırın başında metadata etiketi olduğunda
    # kabul ediyoruz; böylece "yazılım sürümü" ile karışmaz.
    short_document_version_pattern = re.compile(
        r"^\s*(?:sürüm|versiyon)\s*:\s*.+$",
        flags=re.IGNORECASE,
    )
    short_document_version_change = (
        bool(short_document_version_pattern.match(old_text.strip()))
        and bool(short_document_version_pattern.match(new_text.strip()))
    )

    if (
        any(term in combined_text for term in document_version_terms)
        or short_document_version_change
    ):
        return ChangeClassification(
            category=ChangeCategory.OTHER,
            confidence=0.99,
            reason=(
                "Değişiklik yalnızca dokümanın sürüm veya revizyon "
                "bilgisini güncellemektedir."
            ),
            source="rule",
        )

    # Sürecin tamamlanma süresi / son tarihi değişiyor.
    # Rolün yaptığı iş aynı kalıp yalnızca işlem süresi değiştiğinde bu,
    # görev tanımından çok iş akışının zamanlama kuralını etkiler.
    process_timing_terms = (
        "iş günü",
        "gün içinde",
        "saat içinde",
        "en geç",
        "en az",
    )

    if (
        old_normalized
        and new_normalized
        and old_normalized != new_normalized
        and any(term in combined_text for term in process_timing_terms)
    ):
        return ChangeClassification(
            category=ChangeCategory.PROCESS,
            confidence=0.96,
            reason=(
                "Değişiklik iş akışındaki işlem süresini veya zamanlama "
                "kuralını güncellemektedir."
            ),
            source="rule",
        )

    # Yalnızca yürürlük / revizyon / yayın tarihi değişikliği.
    date_terms = (
        "yürürlük tarihi",
        "revizyon tarihi",
        "yayın tarihi",
        "doküman tarihi",
    )

    if any(term in combined_text for term in date_terms):
        return ChangeClassification(
            category=ChangeCategory.OTHER,
            confidence=0.98,
            reason=(
                "Değişiklik yalnızca dokümanın tarih bilgisini "
                "güncellemektedir."
            ),
            source="rule",
        )

    # Dokümanın amacı veya kapsamı değişiyor.
    scope_terms = (
        "bu dokümanın amacı",
        "dokümanın amacı",
        "bu dokümanın kapsamı",
        "dokümanın kapsamı",
    )

    if any(term in combined_text for term in scope_terms):
        return ChangeClassification(
            category=ChangeCategory.DEFINITION,
            confidence=0.96,
            reason=(
                "Dokümanın amacı veya kapsamı yeni içerikle "
                "değiştirilmiş veya genişletilmiştir."
            ),
            source="rule",
        )

    return None


def classify_change_with_llm(
    old_text: str,
    new_text: str,
    generate: LLMGenerateFunction,
) -> ChangeClassification:
    """Bir metin değişikliğini verilen LLM üretim fonksiyonuyla sınıflandırır."""

    if not isinstance(old_text, str):
        raise TypeError("old_text metin olmalıdır.")

    if not isinstance(new_text, str):
        raise TypeError("new_text metin olmalıdır.")

    old_text = old_text.strip()
    new_text = new_text.strip()

    if not old_text and not new_text:
        raise ValueError("Eski ve yeni metin aynı anda boş olamaz.")

    rule_based_result = classify_change_by_rules(
        old_text=old_text,
        new_text=new_text,
    )

    if rule_based_result is not None:
        return rule_based_result

    prompt = build_classification_prompt(
        old_text=old_text,
        new_text=new_text,
    )

    raw_response = generate(prompt)
    classification = parse_classification_response(raw_response)

    classification = validate_classification_semantics(
        classification=classification,
        old_text=old_text,
        new_text=new_text,
    )

    return enrich_classification_reason(
        classification=classification,
        old_text=old_text,
        new_text=new_text,
    )


def classify_change_with_ollama(
    old_text: str,
    new_text: str,
    model_name: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 180,
) -> ChangeClassification:
    """Bir metin değişikliğini Ollama modeliyle sınıflandırır."""

    if not isinstance(old_text, str):
        raise TypeError("old_text metin olmalıdır.")

    if not isinstance(new_text, str):
        raise TypeError("new_text metin olmalıdır.")

    old_text = old_text.strip()
    new_text = new_text.strip()

    if not old_text and not new_text:
        raise ValueError("Eski ve yeni metin aynı anda boş olamaz.")

    rule_based_result = classify_change_by_rules(
        old_text=old_text,
        new_text=new_text,
    )

    if rule_based_result is not None:
        return rule_based_result

    endpoint = f"{ollama_url.rstrip('/')}/api/chat"
    prompt = build_classification_prompt(
        old_text=old_text,
        new_text=new_text,
    )

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Sen kurumsal doküman değişikliklerini sınıflandıran "
                    "bir uzmansın. Kategoriyi yüzeysel kelimelere göre "
                    "değil, değişikliğin baskın etkisine göre seç. MFA, "
                    "parola, kimlik doğrulama, şifreleme, ağ, sunucu, API, "
                    "veri tabanı ve bilgi güvenliği gereksinimlerini "
                    "technical_change olarak sınıflandır. Doküman sürümü, "
                    "revizyon numarası, doküman tarihi ve biçim değişikliklerini "
                    "teknik değişiklik sayma; başka baskın kategori yoksa "
                    "other seç. Yazılım veya sistem sürümü değişikliklerini "
                    "doküman sürümüyle karıştırma. Gerekçeyi en fazla iki kısa "
                    "cümleyle yaz. Prompt kurallarına, kategori kodlarına veya "
                    "kural numaralarına atıf yapma. Yalnızca verilen JSON "
                    "şemasına uygun yanıt üret."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "format": CLASSIFICATION_RESPONSE_SCHEMA,
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
            "Ollama yanıtında sınıflandırma içeriği bulunamadı."
        )

    classification = parse_classification_response(content)

    classification = validate_classification_semantics(
        classification=classification,
        old_text=old_text,
        new_text=new_text,
    )

    return enrich_classification_reason(
        classification=classification,
        old_text=old_text,
        new_text=new_text,
    )
