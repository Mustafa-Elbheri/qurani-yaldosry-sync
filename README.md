# نظام المزامنة السحابية لتلاوات الشيخ د. ياسر الدوسري (لتطبيق قرآني)

نظام أتمتة متكامل ومجاني 100% يقوم بسحب التلاوات وأرشفتها من موقع [yaldosry.com](http://yaldosry.com/) ونقلها مباشرة إلى حسابك على أرشيف الإنترنت (**Archive.org**)، مع تحديث ملف الفهرس `catalog.json` لتطبيق **قرآني** تلقائياً عبر **GitHub Actions**.

---

## 📁 هيكلية الأقسام في Archive.org

تم تقسيم التلاوات إلى مجموعات مستقلة لسهولة التنقل داخل التطبيق:

| القسم | معرف المجموعة على Archive.org | الوصف |
| :--- | :--- | :--- |
| **الفروض** | `qurani-yasser-aldosari-prayers` | تلاوات صلوات الفروض بالحرم المكي مقسمة بالأعوام |
| **التراويح والتهجد** | `qurani-yasser-aldosari-taraweeh` | تسجيلات التراويح والقيام لعدة سنوات |
| **المصاحف الكاملة** | `qurani-yasser-aldosari-mushaf` | مصحف الحرم، المصحف المرتل، مصحف الدخيل |
| **الإصدارات والختمات** | `qurani-yasser-aldosari-editions` | الإصدارات الرسمية والأدعية |
| **المنوعات والخطب** | `qurani-yasser-aldosari-miscellanies` | الخطب والكلمات والتسجيلات النادرة |

---

## 🚀 كيفية نقل الأقسام (قسم بقسم)

يمكنك تشغيل المزامنة للأقسام عبر سطر الأوامر باستخدام سكربت `sync_all.py`:

### 1. مزامنة قسم الفروض (صلوات الحرم المكي):
```bash
# مزامنة عام 1448هـ فقط (أحدث الصلوات):
python sync_all.py --section prayers --category 1448

# مزامنة عام 1447هـ:
python sync_all.py --section prayers --category 1447

# مزامنة كل سنوات الفروض:
python sync_all.py --section prayers
```

### 2. مزامنة قسم التراويح والتهجد:
```bash
python sync_all.py --section taraweeh
```

### 3. مزامنة المصاحف الكاملة:
```bash
python sync_all.py --section quran
```

### 4. مزامنة الإصدارات والمنوعات:
```bash
python sync_all.py --section editions
python sync_all.py --section miscellanies
```

> **ملاحظة:** السكربت ذكي ومزود بنظام (Resume)، فإذا توقف أو أعدت تشغيله، يتجاوز المقاطع المرفوعة مسبقاً ويكمل من حيث توقف دون تكرار أي ملف.

---

## 🤖 الأتمتة السحابية 24/7 (GitHub Actions)

داخل مجلد `.github/workflows/sync.yml` يوجد نظام المزامنة الدائم:
1. يعمل تلقائياً كل 6 ساعات في خوادم GitHub المجانية.
2. يفحص قسم "الصوتيات الحديثة" بموقع الشيخ.
3. يقوم بتنزيل التلاوات الجديدة ورفعها مباشرة إلى حسابك في Archive.org.
4. يحدّث ملف `catalog.json` ويدفعه إلى المستودع.

### 🔑 إعداد المفاتيح السرية في GitHub Secrets:
في مستودعك على GitHub، اذهب إلى:
`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`
وأضف المفتاحين التاليين:
* `IA_ACCESS_KEY`: مفتاح Access الخاص بحسابك في Archive.org
* `IA_SECRET_KEY`: مفتاح Secret الخاص بحسابك في Archive.org

---

## 📱 كيف يستخدم تطبيقك هذه البيانات؟

تطبيقك يحتاج فقط لقراءة ملف الفهرس:
* رابط ملف الفهرس المباشر:
  `https://raw.githubusercontent.com/Mustafa-Elbheri/yaldosry-archive-sync/master/catalog.json`
* أو مباشرة من الأرشيف:
  `https://archive.org/download/qurani-yasser-aldosari-prayers/catalog.json`

كل تلاوة داخل الفهرس تحتوي على رابط الـ MP3 المباشر من الأرشيف:
```json
{
  "id": "5159",
  "title": "تلاوة جميلة من سورة آل عمران | فجر الأحد 7-1-1448هـ",
  "section": "prayers",
  "category": "عام 1448هـ",
  "archive_url": "https://archive.org/download/qurani-yasser-aldosari-prayers/5159_yaaser7.mp3",
  "thumbnail": "https://img.youtube.com/vi/CFeWoXlSsgA/mqdefault.jpg"
}
```
باندويث مجاني 100%، وسرعة تدفق غير محدودة مدى الحياة!
