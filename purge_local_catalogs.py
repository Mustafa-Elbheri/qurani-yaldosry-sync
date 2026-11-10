import os
import sys
import json
import generate_collections

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

NON_QURAN_IDS = {
    'Cq3lwri7118', 'Mj6mRgAplbY', 'CsE1KpMXPjU', 'UuM1ph5thgQ',
    'HbpmP8Rgkrs', 'dgvsyr_ed5k', 'dgvsyr-ed5k', 'u0b312zRzDk',
    '5jqyRZaml7o', 'hu9CBlHuhjs', 'ZomBkBtqQc4', 'DflPtgkRViE', 'k2t5prFD1bE'
}

RESTORED_TITLES = {
    'jrk2jLbfmjU': '﴿فلا تغرنكم الحياة الدنيا﴾ تلاوة خاشعة لخواتيم سورة لقمان د. ياسر الدوسري | عشاء الثلاثاء 24-1-1446',
    'TsfPmHK-EIg': 'ترتيل بديع لسورتي الضحى والنصر للشيخ د. ياسر الدوسري | صلاة الجمعة 12-2-1446هـ',
    'TWOCBwTlUZ4': 'تلاوة مسترسلة بديعة من سورة الكهف للشيخ د. ياسر الدوسري | فجر السبت 14-5-1446هـ',
    '0g6xKKGIUog': 'ترتيل مميز لسورتي الشمس والليل للشيخ د. ياسر الدوسري | عشاء الأربعاء 25-5-1446هـ',
    'qTCK9Q4_odw': 'تحبير مؤثرة لسورة الملك كاملة | د. ياسر الدوسري فجر الخميس 26-10-1446هـ',
    'D9ZN25miAHA': 'العِقدُ الآسِرْ لتلاوات الشيخ ياسر الدوسري | تلاوات شهر محرم لعام 1446هـ من الحرم المكي✨.',
    'nyDvKkEBixg': 'العِقدُ الآسِرْ لتلاوات الشيخ ياسر الدوسري | تلاوات شهر صفر لعام 1446هـ من الحرم المكي✨'
}

ROOT = os.path.dirname(__file__)
CATALOG_PATH = os.path.join(ROOT, "catalog.json")
STATE_PATH = os.path.join(ROOT, "sync_state.json")

def purge_local():
    print("=" * 75)
    print("🧹 PURGING NON-QURAN LESSONS FROM LOCAL CATALOG & SYNC STATE")
    print("=" * 75)
    
    # 1. Update Catalog
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)
        
    before_cat_len = len(catalog)
    cleaned_catalog = [
        item for item in catalog
        if not any(x in (item.get("id", "") + " " + item.get("youtube_id", "")) for x in NON_QURAN_IDS)
    ]
    for item in cleaned_catalog:
        yid = item.get("youtube_id", "")
        if yid in RESTORED_TITLES:
            item["title"] = RESTORED_TITLES[yid]
    removed_count = before_cat_len - len(cleaned_catalog)
    
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Catalog cleaned: removed {removed_count} items (remaining: {len(cleaned_catalog)} items)")
    
    # 2. Update Sync State (mark them as permanently excluded so sync never re-downloads them)
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)
        
    for vid, real_title in RESTORED_TITLES.items():
        key = f"yt_{vid}"
        if key in state:
            state[key]["title"] = real_title

    for vid in NON_QURAN_IDS:
        if vid == 'dgvsyr-ed5k':
            continue
        key = f"yt_{vid}"
        state[key] = {
            "id": key,
            "youtube_id": vid,
            "excluded": True,
            "reason": "non_quran_lesson_or_lecture",
            "archive_url": None
        }
        
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        
    print("✅ Sync state updated: marked target lessons as permanently excluded.")
    
    # 3. Regenerate aldosari_prayers.json
    print("\nRegenerating aldosari_prayers.json...")
    generate_collections.main()
    print("✅ aldosari_prayers.json regenerated successfully!")

if __name__ == "__main__":
    purge_local()
