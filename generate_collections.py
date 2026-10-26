import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "catalog.json"
OUTPUT_PATH = ROOT / "aldosari_prayers.json"

RECITER = "ياسر الدوسري"
TITLE = "روائع الحرم"
SERVER = "https://archive.org/download/qurani-yasser-aldosari-prayers/"

SURAH_NAMES = [
    'الفاتحة', 'البقرة', 'آل عمران', 'النساء', 'المائدة', 'الأنعام', 'الأعراف', 'الأنفال', 'التوبة',
    'يونس', 'هود', 'يوسف', 'الرعد', 'إبراهيم', 'الحجر', 'النحل', 'الإسراء', 'الكهف', 'مريم', 'طه',
    'الأنبياء', 'الحج', 'المؤمنون', 'النور', 'الفرقان', 'الشعراء', 'النمل', 'القصص', 'العنكبوت', 'الروم',
    'لقمان', 'السجدة', 'الأحزاب', 'سبأ', 'فاطر', 'يس', 'الصافات', 'ص', 'الزمر', 'غافر', 'فصلت',
    'الشورى', 'الزخرف', 'الدخان', 'الجاثية', 'الأحقاف', 'محمد', 'الفتح', 'الحجرات', 'ق', 'الذاريات',
    'الطور', 'النجم', 'القمر', 'الرحمن', 'الواقعة', 'الحديد', 'المجادلة', 'الحشر', 'الممتحنة', 'الصف',
    'المنافقون', 'التغابن', 'الطلاق', 'التحريم', 'الملك', 'القلم', 'الحاقة', 'المعارج', 'نوح',
    'الجن', 'المزمل', 'المدثر', 'القيامة', 'الإنسان', 'المرسلات', 'النبأ', 'النازعات', 'عبس', 'التكوير',
    'الانفطار', 'المطففين', 'الانشقاق', 'البروج', 'الطارق', 'الأعلى', 'الغاشية', 'الفجر', 'البلد', 'الشمس',
    'الليل', 'الضحى', 'الشرح', 'التين', 'العلق', 'القدر', 'البينة', 'الزلزلة', 'العاديات', 'القارعة',
    'التكاثر', 'العصر', 'الهمزة', 'الفيل', 'قريش', 'الماعون', 'الكوثر', 'الكافرون', 'النصر', 'المسد',
    'الإخلاص', 'الفلق', 'الناس', 'الجمعة'
]

SPECIAL_SURAH = {'ص': 'سورة ص', 'ق': 'سورة ق', 'الجمعة': 'سورة الجمعة'}

def make_dignified_title(raw):
    t = re.sub(r'[\U00010000-\U0010ffff]', '', raw)
    t = t.replace('❤️', '').replace('🕋', '').replace('🤍', '').replace('‏', '').strip()
    
    # 1. Date/Prayer part from pipe or regex
    date_part = ''
    if '|' in t:
        parts = t.split('|')
        candidate = parts[-1].strip()
        candidate = re.sub(r'(?:القارئ|الشيخ)?\s*(?:د\.\s*)?ياسر\s+الدوسري', '', candidate).strip(' -|')
        if any(w in candidate for w in ['فجر', 'مغرب', 'عشاء', 'ظهر', 'عصر', 'تراويح', 'تهجد', 'ليلة', '144', '143', 'رمضان', 'الجمعة', 'السبت', 'الأحد', 'الاثنين', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']):
            date_part = candidate
            t = parts[0].strip()
            
    if not date_part:
        m = re.search(r'((?:فجر|مغرب|عشاء|ظهر|عصر|تراويح|تهجد|ليلة)?\s*(?:الأحد|الاثنين|الإثنين|الثلاثاء|الأربعاء|الخميس|الجمعة|السبت)?\s*(?:\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{1,2}\s+رمضان|\d{1,2}[-/]\d{1,2}|14\d{2}\s*هـ?))', t)
        if m:
            date_part = m.group(1).strip()
            t = t.replace(date_part, '').strip()

    date_part = date_part.replace('فجرية', 'فجر').replace('عشائية', 'عشاء').strip(' -|:')
    
    search_text = re.sub(r'﴿[^﴾]*﴾', '', t)
    search_text = search_text.replace('أحسن القصص', '')
    
    found_surahs = []
    for s in SURAH_NAMES:
        if s in SPECIAL_SURAH:
            if SPECIAL_SURAH[s] in search_text:
                found_surahs.append(s)
        else:
            if re.search(r'(?:سورة|لسورة|سورتي)\s+(?:و)?' + re.escape(s), search_text):
                found_surahs.append(s)
                
    # Second pass for conjunctions
    for s in SURAH_NAMES:
        if s not in found_surahs:
            if s in SPECIAL_SURAH:
                if SPECIAL_SURAH[s] in search_text:
                    found_surahs.append(s)
            else:
                if re.search(r'(?:سورتي|وسورة|و)\s*' + re.escape(s), search_text):
                    found_surahs.append(s)
                
    if not found_surahs:
        for s in SURAH_NAMES:
            if s in SPECIAL_SURAH:
                if SPECIAL_SURAH[s] in search_text:
                    found_surahs.append(s)
            else:
                if re.search(r'(?:^|[^\u0621-\u064A])(?:و)?' + re.escape(s) + r'(?:$|[^\u0621-\u064A])', search_text):
                    found_surahs.append(s)
                    
    found_surahs.sort(key=lambda s: search_text.find(s))
    
    prefix = ''
    if 'خواتيم' in t: prefix = 'خواتيم '
    elif 'أوائل' in t or 'اول سورة' in t or 'أول سورة' in t: prefix = 'أوائل '
    elif 'آيات من' in t: prefix = 'آيات من '
    
    verses_match = re.search(r'(\d{1,3}\s*[-–]\s*\d{1,3})', t)
    verses_str = f' ({verses_match.group(1)})' if verses_match else ''
    
    surah_str = ''
    if len(found_surahs) == 1:
        surah_str = f'{prefix}سورة {found_surahs[0]}{verses_str}'
    elif len(found_surahs) == 2:
        surah_str = f'{prefix}سورتي {found_surahs[0]} و{found_surahs[1]}'
    elif len(found_surahs) > 2:
        surah_str = f'{prefix}سور ' + ' و'.join(found_surahs[:3])
        
    components = []
    if surah_str:
        components.append(surah_str)
    elif t:
        clean_t = re.sub(r'(?:القارئ|الشيخ)?\s*(?:د\.\s*)?ياسر\s+الدوسري', '', t)
        clean_t = re.sub(r'للغرّيد|للغريد|تلاوة\s+(?:جميلة|ماتعة|رائعة|مهيبة|هادئة|بديعة|خاشعة|مؤثرة|نادرة|مصوّرة)?', '', clean_t)
        clean_t = re.sub(r'\s+', ' ', clean_t).strip(' -|:!؟')
        if clean_t:
            components.append(clean_t)
            
    if date_part:
        components.append(date_part)
        
    components.append('الشيخ د. ياسر الدوسري')
    return ' - '.join(components)

def sort_key(it):
    return (it.get('date') or '0000', it.get('uploaded_at') or '')

def main():
    if not CATALOG_PATH.exists():
        print(f"Error: {CATALOG_PATH} not found")
        return
        
    items = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    prayers = [it for it in items if it.get("section") == "prayers" and it.get("archive_url")]
    prayers.sort(key=sort_key, reverse=True)
    
    tracks = []
    for idx, it in enumerate(prayers, 1):
        tracks.append({
            "number": idx,
            "name": make_dignified_title(it.get("title", "")),
            "url": it.get("archive_url")
        })
        
    collection = {
        "reciter": RECITER,
        "name": TITLE,
        "server": SERVER,
        "unit": "تلاوة",
        "tracks": tracks
    }
    
    OUTPUT_PATH.write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {OUTPUT_PATH.name} with {len(tracks)} dignified tracks.")

if __name__ == "__main__":
    main()
