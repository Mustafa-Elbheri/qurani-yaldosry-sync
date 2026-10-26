# محرك الفهرسة والمزامنة السحابية لتلاوات الشيخ د. ياسر الدوسري
### المزوّد الصوتي الرسمي لتطبيق [قرآني — Qurani App](https://github.com/Mustafa-Elbheri/Qurani-Releases)

[![GitHub Actions Status](https://github.com/Mustafa-Elbheri/qurani-yaldosry-sync/workflows/Auto-Sync%20YouTube%20Channel%20to%20Archive.org/badge.svg)](https://github.com/Mustafa-Elbheri/qurani-yaldosry-sync/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Archive.org Backend](https://img.shields.io/badge/Audio%20Backend-Archive.org-orange)](https://archive.org/details/@albheri2020)

نظام أتمتة سحابي مفتوح المصدر يعمل على خوادم **GitHub Actions**، مخصص لسحب وأرشفة وتوليد فهرس تلاوات القرآن الكريم الخاصة بفضيلة الشيخ **د. ياسر بن راشد الدوسري** وتوفيرها لتطبيق الهاتف المحمول **[قرآني (Qurani)](https://github.com/Mustafa-Elbheri/Qurani-Releases)**.

---

## ⚖️ التوافق التام مع سياسات وباندويث GitHub
1. **عدم استضافة وسائط أو ملفات صوتية على GitHub:**
   - يلتزم هذا المستودع حرفياً بسياسات استخدام GitHub (ToS).
   - لا يتم رفع أي ملف صوتي أو صورة ثنائية إلى مستودع GitHub نهائياً لتجنب استهلاك مساحة أو باندويث GitHub.
2. **الاستضافة والتدفق بالكامل عبر أرشيف الإنترنت (Archive.org):**
   - يتم تخزين وبث وتحميل جميع التلاوات الصوتية (`.mp3`) وأغلفتها عالية الجودة (`.jpg`) عبر خوادم **[Internet Archive](https://archive.org/details/qurani-yasser-aldosari-prayers)** بحساب موثوق ومرخص ومجاني مدى الحياة وباندويث غير محدود.
3. **دور هذا المستودع:**
   - استضافة كود الأتمتة السحابية.
   - نشر وتحديث ملف الفهرس النصي الخفيف `catalog.json` الذي يعتمد عليه تطبيق **قرآني** لقراءة قائمة التلاوات وروابط تشغيلها المباشرة.

---

## 🕋 مصدر التلاوات وقواعد التصفية الصارمة
* **المصدر الرسمي:** القناة الرسمية لفضيلة الشيخ د. ياسر الدوسري على يوتيوب (`@yasser_aldosari`).
* **استبعاد الخطب والكلمات نهائياً:** يتم استبعاد خطب الجمعة، الكلمات التوجيهية، المحاضرات، والندوات عبر فلتر الكلمات الدلالية (`is_khutbah()`) بنسبة 100% ليقتصر الأرشيف على **التلاوات القرآنية الخالصة فقط**.
* **استبعاد مقاطع Shorts:** يتم سحب مقاطع التلاوات الطويلة والكاملة فقط واستبعاد مقاطع Shorts تماماً.
* **بيانات وصفية متوافقة مع الأرشيف:** كل تلاوة يتم ترقيمها وتوثيق تاريخها الهجري واسم السورة، مع إرفاق غلاف مخصص عالي الجودة لضمان المعايير الفنية لأرشيف الإنترنت وتطبيق قرآني.

---

## 📡 كيفية استخدام التطبيق للفهرس (API Integration)

يقرأ تطبيق **قرآني (Qurani)** الفهرس المحدث لحظياً عبر الرابط المباشر:

```url
https://raw.githubusercontent.com/Mustafa-Elbheri/qurani-yaldosry-sync/master/catalog.json
```

### هيكل كل عنصر في الفهرس (`catalog.json`):
```json
{
  "id": "yt_8Vx-d6WHY3s",
  "youtube_id": "8Vx-d6WHY3s",
  "title": "أحسن القصص! خواتيم سورة يوسف بتحبير يفوق الوصف للشيخ د. ياسر الدوسري | ليلة 30 رمضان 1447هـ",
  "standard_name": "1447_Prayer_Yusuf_yt_8Vx-d6WHY3s",
  "section": "prayers",
  "category": "صلوات الحرم المكي",
  "date": "1447",
  "year": "1447",
  "source_type": "youtube",
  "archive_url": "https://archive.org/download/qurani-yasser-aldosari-prayers/1447_Prayer_Yusuf_yt_8Vx-d6WHY3s.mp3",
  "archive_cover_url": "https://archive.org/download/qurani-yasser-aldosari-prayers/1447_Prayer_Yusuf_yt_8Vx-d6WHY3s.jpg",
  "size_mb": 18.74,
  "uploaded_at": "2026-10-26 01:32:54"
}
```

* يقوم التطبيق بتشغيل وتحميل الصوت مباشرة من `archive_url`.
* يقرأ الغلاف من `archive_cover_url`.
* **الباندويث:** مجاني 100% وسرعة فائقة من سيرفرات الأرشيف العالمية.

---

## 🔗 روابط هامة
* **مستودع إصدارات تطبيق قرآني:** [Mustafa-Elbheri/Qurani-Releases](https://github.com/Mustafa-Elbheri/Qurani-Releases)
* **مجموعة التلاوات على Archive.org:** [qurani-yasser-aldosari-prayers](https://archive.org/details/qurani-yasser-aldosari-prayers)
* **مصحف الحرم على Archive.org:** [qurani-yasser-aldosari-mushaf](https://archive.org/details/qurani-yasser-aldosari-mushaf)
