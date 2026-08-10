"""LLM tabanlı değişiklik analizi için kontrollü istemler üretir."""

from impactdoc_ai.comparison import TextChange
from impactdoc_ai.analysis.change_category import ChangeClassification


IMPACT_LEVEL_GUIDE = """
Etki seviyesi kuralları:

low:
- Sürüm, revizyon, başlık veya biçim değişikliği
- Açıklama niteliğindeki küçük güncelleme
- Operasyonel sorumluluğu değiştirmeyen tarih güncellemesi
- Yazım veya ifade düzeltmesi

medium:
- İş akışı veya işlem adımı değişikliği
- Yeni sorumluluk veya görev
- Onay yöntemi ya da işlem süresi değişikliği
- Çalışanın veya yöneticinin uygulamasını değiştiren yeni kural
- Yeni kayıt, bildirim veya takip yükümlülüğü

high:
- Yetkilendirme veya erişim kontrolü değişikliği
- Kullanıcı hesabının açılması veya kapatılması
- Kritik sistem, güvenlik veya kişisel veri riski
- Zorunlu mevzuat veya uyum yükümlülüğü
- İşten ayrılma sırasında kritik erişimlerin sonlandırılması
- Güvenlik ihlaline yol açabilecek kontrol değişikliği
""".strip()

CATEGORY_ROLE_GUIDES: dict[str, str] = {
    "task_change": (
        "Rolün görev veya sorumluluğu ekleniyor, kaldırılıyor ya da "
        "değişiyorsa doğrudan işi yapan ve işi yöneten rollere öncelik ver."
    ),
    "process_change": (
        "İş akışı, başvuru kanalı, form, kayıt veya işlem yöntemi "
        "değişiyorsa süreci uygulayan, yöneten ve kontrol eden rollere "
        "öncelik ver."
    ),
    "authority_change": (
        "Onay, imza, karar, kontrol veya erişim yetkisi değişiyorsa "
        "yetkiyi kullanan ve yetkiden doğrudan etkilenen rollere öncelik ver."
    ),
    "definition_change": (
        "Bir kavramın veya kapsamın tanımı değişiyorsa bu tanımı işinde "
        "uygulayan ve yorumlayan rollere öncelik ver."
    ),
    "technical_change": (
        "Sistem, MFA, parola, kimlik doğrulama, güvenlik, entegrasyon veya "
        "teknik altyapı değişiyorsa ilgili teknik roller ile sistemi "
        "doğrudan kullanan rolleri değerlendir."
    ),
    "legislation_change": (
        "Mevzuat veya uyum yükümlülüğü değişiyorsa kuralı uygulayan, "
        "denetleyen ve uyumdan sorumlu rollere öncelik ver."
    ),
    "other": (
        "Kategori belirgin bir rol grubu göstermediği için yalnızca "
        "değişiklik metnindeki doğrudan etkilere dayan."
    ),
}

def build_classification_context(
    classification: ChangeClassification | None,
) -> str:
    """Sınıflandırma sonucunu rol analizi için yönlendirici metne dönüştürür."""

    if classification is None:
        return (
            "Değişiklik kategorisi henüz sınıflandırılmamıştır. "
            "Rol seçimini yalnızca değişiklik metnine göre yap."
        )

    role_guide = CATEGORY_ROLE_GUIDES.get(
        classification.category.value,
        CATEGORY_ROLE_GUIDES["other"],
    )

    return f"""
Değişiklik sınıflandırması:
- Kategori: {classification.category.label}
- Kategori kodu: {classification.category.value}
- Sınıflandırma güveni: {classification.confidence:.2f}
- Sınıflandırma gerekçesi: {classification.reason}

Kategoriye bağlı rol seçim yönlendirmesi:
{role_guide}

Bu kategori yalnızca yönlendirici bağlamdır. Değişiklik metninde doğrudan
desteklenmeyen bir rolü yalnızca kategori nedeniyle seçme.
""".strip()


def build_system_prompt(
    role_pool: list[str],
    document_category: str,
    classification: ChangeClassification | None = None,
) -> str:
    """Rol havuzuna ve doküman türüne göre sistem istemi üretir."""

    formatted_roles = "\n".join(
        f"- {role}"
        for role in role_pool
    )
    classification_context = build_classification_context(
        classification
    )

    return f"""
Sen kurumsal doküman değişikliklerini rol bazında analiz eden uzman bir
etki analistisin.

Doküman kategorisi:
{document_category}

Değişiklik sınıflandırma bağlamı:

{classification_context}

Yalnızca aşağıdaki rol havuzundan seçim yapabilirsin:

{formatted_roles}

Zorunlu analiz kuralları:

1. Yalnızca verilen değişiklik metnine dayan.
2. Rol havuzu dışında hiçbir rol üretme.
3. En fazla 3 rol seç.
4. Bir rolü yalnızca değişiklik o rolün görevini, sorumluluğunu,
   yetkisini, kullandığı sistemi veya uyması gereken süreci etkiliyorsa seç.
5. Sadece dolaylı ve zayıf bir bağlantı varsa rolü seçme.
6. Teknik bir sistem, erişim, yetki veya güvenlik ifadesi bulunmuyorsa
   Bilgi İşlem veya Bilgi Güvenliği rollerini seçme.
7. Etki seviyesini yalnızca low, medium veya high olarak üret.
8. Gerekçede değişen ifadeyi ve bunun rol üzerindeki somut etkisini açıkla.
9. Önerilen aksiyonlar uygulanabilir, kısa ve rol odaklı olsun.
10. Aynı anlamdaki rolleri veya aksiyonları tekrar etme.
11. Güven değeri konusunda aşırı kesin davranma:
    - 0.90-1.00: Etki açıkça ve doğrudan metinde belirtiliyor.
    - 0.75-0.89: Etki güçlü fakat kısmen yorum gerektiriyor.
    - 0.55-0.74: Etki olası ancak metin sınırlı veya belirsiz.
12. Çıktıyı yalnızca istenen JSON yapısında üret.
13. JSON dışında açıklama, kod bloğu veya ek metin yazma.
14. Değişiklik kategorisini rol seçimini yönlendirmek için kullan;
    fakat yalnızca kategori nedeniyle rol seçme.
15. Kategori ile değişiklik metni çelişirse değişiklik metnindeki somut
    ifadeyi esas al.
16. Sınıflandırma güveni düşükse kategoriye daha az ağırlık ver.

{IMPACT_LEVEL_GUIDE}
""".strip()


def build_change_prompt(
    change: TextChange,
    change_number: int,
    role_pool: list[str],
    document_category: str,
    classification: ChangeClassification | None = None,
) -> str:
    """Tek değişiklik için kontrollü kullanıcı istemi üretir."""

    old_text = change.old_text or "YOK"
    new_text = change.new_text or "YOK"

    formatted_roles = ", ".join(role_pool)
    classification_context = build_classification_context(
        classification
    )

    return f"""
Aşağıdaki tek doküman değişikliğini analiz et.

Değişiklik kimliği: CHG-{change_number:04d}
Doküman kategorisi: {document_category}
Değişiklik türü: {change.change_type.value}

Eski metin:
{old_text}

Yeni metin:
{new_text}

Eski konum: {change.old_position}
Yeni konum: {change.new_position}
Metin benzerliği: {change.similarity_score}

İzin verilen roller:
{formatted_roles}

Beklenen JSON alanları:

- affected_roles:
  Yalnızca izin verilen rollerden, doğrudan etkilenen en fazla 3 rol.

- impact_level:
  Yalnızca low, medium veya high.

- reason:
  Değişen ifadenin hangi sorumluluk, işlem, yetki veya iş akışını
  etkilediğini kısa ve somut biçimde açıkla.

- recommended_actions:
  Etkilenen roller için 1 ile 3 arasında uygulanabilir aksiyon.

- confidence:
  0 ile 1 arasında, kararın metin tarafından ne kadar açık
  desteklendiğini gösteren güven değeri.

Önemli:
Teknik bir sistem, erişim, hesap, yetki veya güvenlik değişikliği yoksa
teknik rol seçme.

Yalnızca JSON üret.
""".strip()