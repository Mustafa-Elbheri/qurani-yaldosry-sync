import os
import sys
import json
import re
import subprocess
import time
import requests
import internetarchive as ia

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

STATE_FILE = os.path.join(os.path.dirname(__file__), "sync_state.json")
CATALOG_FILE = os.path.join(os.path.dirname(__file__), "catalog.json")

SECTION_ITEMS = {
    "quran": "qurani-yasser-aldosari-mushaf",
    "prayers": "qurani-yasser-aldosari-prayers",
    "taraweeh": "qurani-yasser-aldosari-taraweeh",
    "editions": "qurani-yasser-aldosari-editions",
    "miscellanies": "qurani-yasser-aldosari-miscellanies"
}

SECTION_TITLES = {
    "quran": "المصاحف الكاملة والمرتلة - الشيخ د. ياسر الدوسري | تطبيق قرآني",
    "prayers": "تلاوات الفروض والحرم المكي - الشيخ د. ياسر الدوسري | تطبيق قرآني",
    "taraweeh": "تلاوات التراويح والتهجد - الشيخ د. ياسر الدوسري | تطبيق قرآني",
    "editions": "الإصدارات والختمات - الشيخ د. ياسر الدوسري | تطبيق قرآني",
    "miscellanies": "الخطب والمنوعات - الشيخ د. ياسر الدوسري | تطبيق قرآني"
}

# 114 Surahs mapping for clean naming and track indexing
SURAH_DICT = {
    "الفاتحة": (1, "Al-Fatihah"), "البقرة": (2, "Al-Baqarah"), "آل عمران": (3, "Ali-Imran"),
    "النساء": (4, "An-Nisa"), "المائدة": (5, "Al-Maidah"), "الأنعام": (6, "Al-Anam"),
    "الأعراف": (7, "Al-Araf"), "الأنفال": (8, "Al-Anfal"), "التوبة": (9, "At-Tawbah"),
    "يونس": (10, "Yunus"), "هود": (11, "Hud"), "يوسف": (12, "Yusuf"),
    "الرعد": (13, "Ar-Rad"), "إبراهيم": (14, "Ibrahim"), "الحجر": (15, "Al-Hijr"),
    "النحل": (16, "An-Nahl"), "الإسراء": (17, "Al-Isra"), "الكهف": (18, "Al-Kahf"),
    "مريم": (19, "Maryam"), "طه": (20, "Taha"), "الأنبياء": (21, "Al-Anbiya"),
    "الحج": (22, "Al-Hajj"), "المؤمنون": (23, "Al-Muminun"), "النور": (24, "An-Nur"),
    "الفرقان": (25, "Al-Furqan"), "الشعراء": (26, "Ash-Shuara"), "النمل": (27, "An-Naml"),
    "القصص": (28, "Al-Qasas"), "العنكبوت": (29, "Al-Ankabut"), "الروم": (30, "Ar-Rum"),
    "لقمان": (31, "Luqman"), "السجدة": (32, "As-Sajdah"), "الأحزاب": (33, "Al-Ahzab"),
    "سبأ": (34, "Saba"), "فاطر": (35, "Fatir"), "يس": (36, "Ya-Sin"),
    "الصافات": (37, "As-Saffat"), "ص": (38, "Sad"), "الزمر": (39, "Az-Zumar"),
    "غافر": (40, "Ghafir"), "فصلت": (41, "Fussilat"), "الشورى": (42, "Ash-Shura"),
    "الزخرف": (43, "Az-Zukhruf"), "الدخان": (44, "Ad-Dukhan"), "الجاثية": (45, "Al-Jathiyah"),
    "الأحقاف": (46, "Al-Ahqaf"), "محمد": (47, "Muhammad"), "الفتح": (48, "Al-Fath"),
    "الحجرات": (49, "Al-Hujurat"), "ق": (50, "Qaf"), "الذاريات": (51, "Adh-Dhariyat"),
    "الطور": (52, "At-Tur"), "النجم": (53, "An-Najm"), "القمر": (54, "Al-Qamar"),
    "الرحمن": (55, "Ar-Rahman"), "الواقعة": (56, "Al-Waqiah"), "الحديد": (57, "Al-Hadid"),
    "المجادلة": (58, "Al-Mujadilah"), "الحشر": (59, "Al-Hashr"), "الممتحنة": (60, "Al-Mumtahanah"),
    "الصف": (61, "As-Saff"), "الجمعة": (62, "Al-Jumuah"), "المنافقون": (63, "Al-Munafiqun"),
    "التغابن": (64, "At-Taghabun"), "الطلاق": (65, "At-Talaq"), "التحريم": (66, "At-Tahrim"),
    "الملك": (67, "Al-Mulk"), "القلم": (68, "Al-Qalam"), "الحاقة": (69, "Al-Haqqah"),
    "المعارج": (70, "Al-Maarij"), "نوح": (71, "Nuh"), "الجن": (72, "Al-Jinn"),
    "المزمل": (73, "Al-Muzzammil"), "المدثر": (74, "Al-Muddaththir"), "القيامة": (75, "Al-Qiyamah"),
    "الإنسان": (76, "Al-Insan"), "المرسلات": (77, "Al-Mursalat"), "النبأ": (78, "An-Naba"),
    "النازعات": (79, "An-Naziat"), "عبس": (80, "Abasa"), "التكوير": (81, "At-Takwir"),
    "الانفطار": (82, "Al-Infitar"), "المطففين": (83, "Al-Mutaffifin"), "الانشقاق": (84, "Al-Inshiqaq"),
    "البروج": (85, "Al-Buruj"), "الطارق": (86, "At-Tariq"), "الأعلى": (87, "Al-Ala"),
    "الغاشية": (88, "Al-Ghashiyah"), "الفجر": (89, "Al-Fajr"), "البلد": (90, "Al-Balad"),
    "الشمس": (91, "Ash-Shams"), "الليل": (92, "Al-Layl"), "الضحى": (93, "Ad-Duha"),
    "الشرح": (94, "Ash-Sharh"), "التين": (95, "At-Tin"), "العلق": (96, "Al-Alaq"),
    "القدر": (97, "Al-Qadr"), "البينة": (98, "Al-Bayyinah"), "الزلزلة": (99, "Az-Zalzalah"),
    "العاديات": (100, "Al-Adiyat"), "القارعة": (101, "Al-Qariah"), "التكاثر": (102, "At-Takathur"),
    "العصر": (103, "Al-Asr"), "الهمزة": (104, "Al-Humazah"), "الفيل": (105, "Al-Fil"),
    "قريش": (106, "Quraysh"), "الماعون": (107, "Al-Maun"), "الكوثر": (108, "Al-Kawthar"),
    "الكافرون": (109, "Al-Kafirun"), "النصر": (110, "An-Nasr"), "المسد": (111, "Al-Masad"),
    "الإخلاص": (112, "Al-Ikhlas"), "الفلق": (113, "Al-Falaq"), "الناس": (114, "An-Nas")
}

DEFAULT_COVER_URL = "http://yaldosry.com/img/youtube/thumbnail.jpg"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def load_catalog():
    if os.path.exists(CATALOG_FILE):
        try:
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_catalog(catalog):
    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

def download_file_curl(url, dest_path):
    cmd = ["curl.exe", "-s", "-L", "--max-time", "60", url, "-o", dest_path]
    res = subprocess.run(cmd)
    if res.returncode == 0 and os.path.exists(dest_path) and os.path.getsize(dest_path) > 500:
        return True
    return False

def extract_surah_info(title):
    """Detect Surah number and English name from Arabic title."""
    for s_name, (s_num, s_en) in SURAH_DICT.items():
        if s_name in title:
            return s_num, s_name, s_en
    return None, None, None

def extract_date_info(title, category_name=""):
    """Extract date and year from title or category."""
    # Look for Hijri date like 7-1-1448 or 1448
    match = re.search(r'(\d{1,2})-(\d{1,2})-(\d{4})', title)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}", year
        
    year_match = re.search(r'(14\d{2})', title) or re.search(r'(14\d{2})', category_name)
    if year_match:
        y = year_match.group(1)
        return y, y
        
    return "1445", "1445"

def generate_standard_filenames(item_dict):
    """
    Generate professional, Archive.org-compliant filenames and metadata.
    Example Quran: 001_Surah_Al-Fatihah.mp3 & 001_Surah_Al-Fatihah.jpg
    Example Prayer: 1448-01-07_Fajr_Al-Imran.mp3 & 1448-01-07_Fajr_Al-Imran.jpg
    """
    section = item_dict.get("section", "prayers")
    title = item_dict.get("title", "")
    item_id = str(item_dict["id"])
    category = item_dict.get("category", "")
    
    date_str, year_str = extract_date_info(title, category)
    
    if section == "quran":
        s_num, s_ar, s_en = extract_surah_info(title)
        if s_num:
            base_name = f"{s_num:03d}_Surah_{s_en}"
            track = str(s_num)
        else:
            base_name = f"quran_{item_id}"
            track = item_id
    elif section == "prayers":
        # Extract prayer type
        prayer_type = "Prayer"
        if "فجر" in title: prayer_type = "Fajr"
        elif "مغرب" in title: prayer_type = "Maghrib"
        elif "عشاء" in title: prayer_type = "Isha"
        elif "ظهر" in title: prayer_type = "Dhuhr"
        elif "عصر" in title: prayer_type = "Asr"
        
        _, _, s_en = extract_surah_info(title)
        surah_tag = f"_{s_en}" if s_en else ""
        base_name = f"{date_str}_{prayer_type}{surah_tag}_{item_id}"
        track = item_id
    elif section == "taraweeh":
        base_name = f"Taraweeh_{date_str}_{item_id}"
        track = item_id
    else:
        base_name = f"{section}_{item_id}"
        track = item_id
        
    return base_name, track, date_str, year_str

def upload_recitation_with_cover(item_dict):
    """
    Strict Archive.org Upload Implementation:
    1. Downloads MP3 file.
    2. Downloads and uploads high-resolution JPG cover alongside the MP3.
    3. Names files with standardized, meaningful filenames.
    4. Attaches full required metadata (date, year, creator, language, subject, description).
    5. Updates sync_state and catalog.
    """
    state = load_state()
    catalog = load_catalog()
    
    item_id = str(item_dict["id"])
    section = item_dict.get("section", "prayers")
    target_identifier = SECTION_ITEMS.get(section, "qurani-yasser-aldosari-prayers")
    item_title = item_dict["title"]
    source_audio_url = item_dict["source_audio_url"]
    
    # Check if already processed
    if item_id in state and state[item_id].get("archive_url"):
        print(f"Skipping {item_id}: Already uploaded -> {state[item_id]['archive_url']}")
        return state[item_id]
        
    base_name, track, date_str, year_str = generate_standard_filenames(item_dict)
    remote_mp3_name = f"{base_name}.mp3"
    remote_jpg_name = f"{base_name}.jpg"
    
    print(f"\n[Processing {section.upper()}] ID: {item_id} | Name: {remote_mp3_name}")
    print(f"  Title: {item_title}")
    print(f"  Date: {date_str} (Year: {year_str}) | Track: {track}")
    
    # Local temporary paths
    temp_dir = os.environ.get("TEMP", ".")
    local_mp3_path = os.path.join(temp_dir, f"temp_{item_id}.mp3")
    local_jpg_path = os.path.join(temp_dir, f"temp_{item_id}.jpg")
    
    # 1. Download MP3
    print(f"  Downloading audio from: {source_audio_url} ...")
    if not download_file_curl(source_audio_url, local_mp3_path):
        print(f"  ERROR: Failed to download audio from {source_audio_url}")
        return None
    file_size_mb = round(os.path.getsize(local_mp3_path) / (1024 * 1024), 2)
    
    # 2. Download Cover Image
    cover_url = item_dict.get("thumbnail") or DEFAULT_COVER_URL
    print(f"  Downloading cover image from: {cover_url} ...")
    has_cover = download_file_curl(cover_url, local_jpg_path)
    
    # 3. Prepare Upload Dictionary
    files_to_upload = {
        remote_mp3_name: local_mp3_path
    }
    if has_cover:
        files_to_upload[remote_jpg_name] = local_jpg_path
        
    # 4. Strict Archive.org Metadata (Compliant with policy & anti-spam)
    item_metadata = {
        "title": SECTION_TITLES.get(section, "تلاوات الشيخ د. ياسر الدوسري"),
        "creator": "الشيخ د. ياسر الدوسري",
        "mediatype": "audio",
        "collection": "opensource_audio",
        "language": "ara",
        "date": date_str,
        "year": year_str,
        "subject": f"القرآن الكريم; الشيخ د. ياسر الدوسري; {item_dict.get('category', section)}; تلاوات خاشعة; ترتيل; الحرم المكي",
        "description": f"تسجيلات وتلاوات الشيخ د. ياسر الدوسري إمام وخطيب المسجد الحرام لتطبيق قرآني - قسم {item_dict.get('category', section)}"
    }
    
    print(f"  Uploading to Archive.org [{target_identifier}] with cover image & strict metadata...")
    try:
        ia.upload(
            target_identifier,
            files=files_to_upload,
            metadata=item_metadata,
            queue_derive=False,
            verbose=False
        )
        
        archive_url = f"https://archive.org/download/{target_identifier}/{remote_mp3_name}"
        archive_thumb_url = f"https://archive.org/download/{target_identifier}/{remote_jpg_name}" if has_cover else ""
        print(f"  SUCCESS!")
        print(f"    Audio: {archive_url}")
        if archive_thumb_url:
            print(f"    Cover: {archive_thumb_url}")
            
        record = {
            "id": item_id,
            "title": item_title,
            "standard_name": base_name,
            "section": section,
            "category": item_dict.get("category", ""),
            "track": track,
            "date": date_str,
            "year": year_str,
            "page_url": item_dict.get("page_url", ""),
            "source_audio_url": source_audio_url,
            "archive_url": archive_url,
            "archive_cover_url": archive_thumb_url,
            "youtube_url": item_dict.get("youtube_url", ""),
            "size_mb": file_size_mb,
            "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        state[item_id] = record
        save_state(state)
        
        catalog = [c for c in catalog if str(c.get("id")) != item_id]
        catalog.append(record)
        save_catalog(catalog)
        
        return record
        
    except Exception as e:
        print(f"  ERROR uploading to Archive.org: {e}")
        return None
    finally:
        # Clean up local temporary files
        for p in [local_mp3_path, local_jpg_path]:
            if os.path.exists(p):
                try: os.remove(p)
                except Exception: pass

if __name__ == "__main__":
    print("Enhanced uploader with cover images and strict metadata ready.")
