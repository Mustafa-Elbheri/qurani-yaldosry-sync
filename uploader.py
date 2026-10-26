import os
import json
import subprocess
import time
import requests
import internetarchive as ia

STATE_FILE = os.path.join(os.path.dirname(__file__), "sync_state.json")
CATALOG_FILE = os.path.join(os.path.dirname(__file__), "catalog.json")

SECTION_ITEMS = {
    "prayers": "qurani-yasser-aldosari-prayers",
    "taraweeh": "qurani-yasser-aldosari-taraweeh",
    "quran": "qurani-yasser-aldosari-mushaf",
    "editions": "qurani-yasser-aldosari-editions",
    "miscellanies": "qurani-yasser-aldosari-miscellanies"
}

SECTION_TITLES = {
    "prayers": "تلاوات الفروض والحرم المكي - الشيخ د. ياسر الدوسري | تطبيق قرآني",
    "taraweeh": "تلاوات التراويح والتهجد - الشيخ د. ياسر الدوسري | تطبيق قرآني",
    "quran": "المصاحف الكاملة والمرتلة - الشيخ د. ياسر الدوسري | تطبيق قرآني",
    "editions": "الإصدارات والختمات - الشيخ د. ياسر الدوسري | تطبيق قرآني",
    "miscellanies": "الخطب والمنوعات - الشيخ د. ياسر الدوسري | تطبيق قرآني"
}

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

def download_audio_curl(source_url, dest_path):
    """Download audio file using curl with resume and timeout."""
    cmd = ["curl.exe", "-s", "-L", "--max-time", "60", source_url, "-o", dest_path]
    res = subprocess.run(cmd)
    if res.returncode == 0 and os.path.exists(dest_path) and os.path.getsize(dest_path) > 10000:
        return True
    return False

def upload_recitation(item_dict):
    """Upload a single recitation to Archive.org and update catalog."""
    state = load_state()
    catalog = load_catalog()
    
    item_id = str(item_dict["id"])
    section = item_dict.get("section", "prayers")
    target_identifier = SECTION_ITEMS.get(section, "qurani-yasser-aldosari-prayers")
    item_title = item_dict["title"]
    source_url = item_dict["source_audio_url"]
    
    # Check if already uploaded
    if item_id in state and state[item_id].get("archive_url"):
        print(f"Skipping {item_id}: Already uploaded -> {state[item_id]['archive_url']}")
        return state[item_id]
        
    print(f"\n[Processing ID {item_id}] {item_title}")
    
    # 1. Download audio file
    raw_filename = source_url.split("/")[-1].split("?")[0]
    local_temp_file = os.path.join(os.environ.get("TEMP", "."), f"yaldosry_{item_id}_{raw_filename}")
    remote_filename = f"{item_id}_{raw_filename}"
    
    print(f"  Downloading from {source_url} ...")
    success = download_audio_curl(source_url, local_temp_file)
    if not success:
        print(f"  ERROR: Failed to download audio from {source_url}")
        return None
        
    file_size_mb = round(os.path.getsize(local_temp_file) / (1024 * 1024), 2)
    print(f"  Downloaded: {file_size_mb} MB")
    
    # 2. Upload to Archive.org
    print(f"  Uploading to Archive.org [{target_identifier}] as '{remote_filename}' ...")
    item_metadata = {
        "title": SECTION_TITLES.get(section, "تلاوات الشيخ د. ياسر الدوسري"),
        "creator": "الشيخ د. ياسر الدوسري",
        "mediatype": "audio",
        "collection": "opensource_audio",
        "description": "تسجيلات وتلاوات الشيخ د. ياسر الدوسري إمام وخطيب المسجد الحرام لتطبيق قرآني",
        "language": "ara"
    }
    
    file_metadata = {
        "title": item_title,
        "creator": "الشيخ د. ياسر الدوسري",
        "album": item_dict.get("category", section),
        "track": item_id
    }
    
    try:
        r = ia.upload(
            target_identifier,
            files={remote_filename: local_temp_file},
            metadata=item_metadata,
            queue_derive=False,
            verbose=False
        )
        
        archive_url = f"https://archive.org/download/{target_identifier}/{remote_filename}"
        print(f"  SUCCESS! Archive URL: {archive_url}")
        
        # 3. Save to state and catalog
        record = {
            "id": item_id,
            "title": item_title,
            "section": section,
            "category": item_dict.get("category", ""),
            "page_url": item_dict.get("page_url", ""),
            "source_audio_url": source_url,
            "archive_url": archive_url,
            "youtube_url": item_dict.get("youtube_url", ""),
            "thumbnail": item_dict.get("thumbnail", ""),
            "size_mb": file_size_mb,
            "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        state[item_id] = record
        save_state(state)
        
        # Update catalog list
        catalog = [c for c in catalog if str(c.get("id")) != item_id]
        catalog.append(record)
        save_catalog(catalog)
        
        return record
        
    except Exception as e:
        print(f"  ERROR during archive upload: {e}")
        return None
    finally:
        # 4. Clean up temp file
        if os.path.exists(local_temp_file):
            try:
                os.remove(local_temp_file)
            except Exception:
                pass

if __name__ == "__main__":
    print("Uploader module ready.")
