# ImpactDoc-AI

ImpactDoc-AI, kurumsal dokümanların farklı sürümleri arasındaki değişiklikleri tespit eden ve bu değişikliklerin organizasyondaki roller üzerindeki etkisini analiz eden yapay zekâ destekli bir doküman değişiklik analiz sistemidir.

Sistem; doküman karşılaştırma, değişiklik sınıflandırma, rol tespiti, kural tabanlı değerlendirme ve yerel LLM analizi katmanlarını bir araya getirerek her değişiklik için etkilenen rolleri ve etki seviyesini belirler.

## Problem

Kurumsal prosedürler, politikalar ve operasyon dokümanları zaman içinde sürekli güncellenir.

Ancak bir dokümanda yapılan değişikliğin:

* hangi çalışanları veya ekipleri etkilediği,
* yeni bir görev veya sorumluluk oluşturup oluşturmadığı,
* yetki yapısını değiştirip değiştirmediği,
* teknik veya güvenlik gereksinimi getirip getirmediği,
* etkisinin düşük, orta veya yüksek seviyede olup olmadığı

manuel olarak değerlendirilmek zorunda kalabilir.

ImpactDoc-AI bu süreci otomatikleştirmeyi amaçlar.

## Temel Özellikler

* TXT, DOCX ve PDF doküman desteği
* Eski ve yeni doküman sürümlerini karşılaştırma
* Added, modified ve removed değişikliklerini tespit etme
* Değişiklikleri anlamsal kategorilere ayırma
* Kural tabanlı ve LLM destekli hibrit sınıflandırma
* Doküman içeriğine göre dinamik rol havuzu oluşturma
* Değişiklikten etkilenen rolleri belirleme
* LLM tarafından üretilen geçersiz veya uydurma rolleri filtreleme
* Düşük, orta ve yüksek etki seviyesi hesaplama
* Kural motoru ile LLM etki değerlendirmesini birleştirme
* LLM gerekçelerini semantik olarak doğrulama
* JSON analiz raporu üretme
* Yönetici seviyesinde analiz özeti oluşturma
* Komut satırı üzerinden tek komutla analiz çalıştırma
* Otomatik regresyon testleri

## Sistem Akışı

```text
Doküman V1
    │
    ├── Doküman Okuma
    │
Doküman V2
    │
    ▼
Doküman Karşılaştırma
    │
    ▼
Değişiklik Tespiti
    │
    ├── Added
    ├── Modified
    └── Removed
    │
    ▼
Değişiklik Sınıflandırma
    │
    ├── Kural Motoru
    └── Ollama / LLM
    │
    ▼
Dinamik Rol Havuzu
    │
    ▼
Etkilenen Rol Analizi
    │
    ▼
LLM Yanıt Doğrulama
    │
    ▼
Etki Seviyesi Hesaplama
    │
    ├── Rule Impact Level
    ├── LLM Impact Level
    └── Final Impact Level
    │
    ▼
JSON Rapor + Yönetici Özeti
```

## Değişiklik Kategorileri

ImpactDoc-AI değişiklikleri aşağıdaki kategorilerden biriyle sınıflandırır:

| Kategori             | Açıklama                                                   |
| -------------------- | ---------------------------------------------------------- |
| `task_change`        | Bir rolün görev veya sorumluluğundaki değişiklik           |
| `process_change`     | İş akışı, yöntem, süre veya süreç adımlarındaki değişiklik |
| `authority_change`   | Onay, karar veya yetki değişikliği                         |
| `definition_change`  | Kapsam veya tanım değişikliği                              |
| `technical_change`   | Sistem, erişim, güvenlik veya teknik altyapı değişikliği   |
| `legislation_change` | Mevzuat veya uyum kaynaklı değişiklik                      |
| `other`              | Doküman metadata'sı veya diğer biçimsel değişiklikler      |

## Etki Seviyeleri

Her değişiklik üç seviyeden biriyle değerlendirilir:

* `low`
* `medium`
* `high`

Nihai etki seviyesi yalnızca LLM çıktısına bağlı değildir.

Sistem hem kural tabanlı hesaplama hem de LLM değerlendirmesi üretir:

```text
Rule Impact Level
        +
LLM Impact Level
        ↓
Final Impact Level
```

Kural motorunun belirlediği minimum etki seviyesi LLM tarafından düşürülemez.

## LLM

Projede yerel LLM çalıştırmak için Ollama kullanılmaktadır.

Test edilen model:

```text
qwen3:4b
```

Varsayılan Ollama servisi:

```text
http://localhost:11434
```

Bu yaklaşım kurumsal dokümanların dış bir API'ye gönderilmeden yerel ortamda analiz edilebilmesine olanak sağlar.

## Kurulum

### 1. Projeyi klonlayın

```bash
git clone https://github.com/Selinshnr/impactdoc-ai.git
cd impactdoc-ai
```

### 2. Sanal ortam oluşturun

Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Projeyi editable olarak kurun

```powershell
python -m pip install -e .
```

### 4. Test geliştirme bağımlılığını kurun

```powershell
python -m pip install pytest
```

### 5. Ollama'yı çalıştırın

Gerekli modeli indirin:

```powershell
ollama pull qwen3:4b
```

Ollama servisinin çalıştığından emin olun.

## CLI Kullanımı

ImpactDoc-AI paket olarak doğrudan çalıştırılabilir.

### Yardım

```powershell
python -m impactdoc_ai --help
```

Mevcut komutlar:

```text
inspect
analyze
```

## Tek Dokümanı İnceleme

```powershell
python -m impactdoc_ai inspect `
    data/raw/personel_yonetimi/personel_yonetim_faaliyetleri_v1.txt
```

Bu komut dokümanın metadata bilgisini görüntüler.

Örnek bilgiler:

```text
Dosya adı
Dosya yolu
Dosya türü
Sayfa sayısı
Karakter sayısı
Kelime sayısı
SHA-256
```

## İki Doküman Sürümünü Analiz Etme

```powershell
python -m impactdoc_ai analyze `
    data/raw/personel_yonetimi/personel_yonetim_faaliyetleri_v1.txt `
    data/raw/personel_yonetimi/personel_yonetim_faaliyetleri_v2.txt `
    --model qwen3:4b `
    --output data/reports/final.json
```

Test amacıyla analiz sayısı sınırlandırılabilir:

```powershell
python -m impactdoc_ai analyze `
    data/raw/personel_yonetimi/personel_yonetim_faaliyetleri_v1.txt `
    data/raw/personel_yonetimi/personel_yonetim_faaliyetleri_v2.txt `
    --model qwen3:4b `
    --output data/reports/test.json `
    --limit 3
```

## Örnek Analiz Sonucu

Personel yönetimi örnek dokümanlarında gerçekleştirilen tam analiz:

```text
Analiz edilen değişiklik : 24

High Impact   : 8
Medium Impact : 13
Low Impact    : 3
```

Kategori dağılımı:

| Kategori          | Sayı |   Oran |
| ----------------- | ---: | -----: |
| Süreç değişikliği |   10 | %41.67 |
| Teknik değişiklik |    6 | %25.00 |
| Diğer             |    3 | %12.50 |
| Tanım değişikliği |    2 |  %8.33 |
| Yetki değişikliği |    2 |  %8.33 |
| Görev değişikliği |    1 |  %4.17 |

Sınıflandırma kaynağı:

```text
Ollama / LLM : 15
Rule Engine  : 9
```

En çok etkilenen roller:

| Rol                     | Değişiklik Sayısı |
| ----------------------- | ----------------: |
| Bilgi Güvenliği Uzmanı  |                 7 |
| Birim Yöneticisi        |                 6 |
| İnsan Kaynakları Uzmanı |                 6 |
| Doküman Yöneticisi      |                 5 |
| Bilgi İşlem Uzmanı      |                 4 |
| Çalışan                 |                 4 |

## Rol Doğrulama

LLM tarafından döndürülen roller doğrudan kabul edilmez.

Sistem:

1. Rolün dokümanın rol havuzunda bulunup bulunmadığını kontrol eder.
2. Değişiklik metninde rolü destekleyen kanıt arar.
3. Uydurma rolleri çıkarır.
4. Teknik kanıt bulunmadığında gereksiz teknik rolleri filtreler.
5. Etkilenen rol sayısını sınırlar.
6. Gerekirse metindeki kanıtlardan eksik rolleri tamamlar.

Bu mekanizma LLM hallucination riskini azaltmak için kullanılmaktadır.

## Gerekçe Doğrulama

LLM sınıflandırma gerekçeleri ayrıca semantik olarak doğrulanır.

Örneğin bir `added` değişiklik için LLM:

```text
Eski metin ... yeni metin ile aynıdır.
```

gibi mevcut olmayan bir eski metne referans verirse gerekçe geçersiz kabul edilir.

Sistem bunun yerine içerik tabanlı güvenli bir gerekçe üretir:

```text
Yeni içerik eklenmiştir: '...'
```

Benzer doğrulama kaldırılan içerikler için de uygulanır.

## Testler

Projede sınıflandırma, rol doğrulama, etki hesaplama ve rol analizi için otomatik testler bulunmaktadır.

Tüm testleri çalıştırmak için:

```powershell
python -m pytest -v
```

Mevcut test sonucu:

```text
29 passed
```

Test edilen temel davranışlardan bazıları:

* Doküman sürümü değişikliğinin `other` olması
* Yazılım sürüm değişikliğinin `technical_change` olması
* Süre değişikliklerinin `process_change` olması
* LLM gerekçe hallucination kontrolü
* Uydurma rol filtreleme
* Teknik kanıt doğrulama
* Confidence normalizasyonu
* Added ve removed değişikliklerde minimum impact seviyesi
* Rule Engine'in düşük LLM skorunu yükseltebilmesi
* LLM seviyesinin kurallardan yüksek olduğunda korunması
* Rol tespiti ve yönetici fallback mekanizması
* Özet ve serialization çıktıları

## Proje Yapısı

```text
impactdoc-ai/
│
├── data/
│   ├── raw/
│   └── reports/
│
├── docs/
├── notebooks/
│
├── src/
│   └── impactdoc_ai/
│       ├── analysis/
│       │   ├── change_category.py
│       │   ├── change_classifier.py
│       │   ├── impact_rules.py
│       │   ├── impact_scoring.py
│       │   ├── llm_impact_analyzer.py
│       │   ├── prompt_builder.py
│       │   ├── response_validator.py
│       │   ├── role_catalog.py
│       │   └── role_impact_analyzer.py
│       │
│       ├── comparison/
│       ├── ingestion/
│       ├── models/
│       ├── parsing/
│       ├── reporting/
│       ├── utils/
│       │
│       ├── main.py
│       └── __main__.py
│
├── tests/
│   ├── test_change_classifier.py
│   ├── test_impact_scoring.py
│   ├── test_response_validator.py
│   └── test_role_impact_analyzer.py
│
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Kullanılan Teknolojiler

* Python
* Ollama
* Qwen3
* PyPDF
* python-docx
* pytest
* argparse
* JSON

## Tasarım Yaklaşımı

ImpactDoc-AI tamamen LLM'e bağımlı bir sistem değildir.

Projede hibrit bir yaklaşım uygulanmaktadır:

```text
Deterministik Kurallar
        +
LLM Anlamsal Analizi
        +
Yanıt Doğrulama
        +
Etki Skorlama Kuralları
        ↓
Daha Kontrollü Nihai Karar
```

Bu yaklaşım özellikle kurumsal kullanım senaryolarında LLM çıktılarının doğrudan güvenilir kabul edilmesi yerine kontrol edilmesini amaçlar.

## Mevcut Sınırlamalar

* Rol katalogları şu anda belirli kurumsal senaryolara göre tanımlanmıştır.
* LLM analizi için Ollama servisinin çalışıyor olması gerekir.
* Kural tabanlı yaklaşım yeni doküman türleri için ek alan kuralları gerektirebilir.
* Karmaşık tablo ve görsel içeriklerin semantik analizi sınırlıdır.
* Sistem şu anda komut satırı odaklıdır ve web arayüzü bulunmamaktadır.

## Gelecek Geliştirmeler

İlerleyen sürümlerde aşağıdaki özellikler eklenebilir:

* Web tabanlı kullanıcı arayüzü
* Kurumsal rol kataloglarının yapılandırılabilir hale getirilmesi
* Farklı LLM sağlayıcıları
* İnsan onaylı değerlendirme akışı
* Değişiklik geçmişi ve versiyon takibi
* Dashboard ve görsel etki raporları
* Çoklu doküman analizi
* Daha gelişmiş PDF tablo ve görsel desteği

## Sürüm

```text
ImpactDoc-AI v0.1.0
```
