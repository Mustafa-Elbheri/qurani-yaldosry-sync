import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "catalog.json"
OUTPUT_PATH = ROOT / "aldosari_prayers.json"

RECITER = "ياسر الدوسري"
TITLE = "روائع الحرم"
SERVER = "https://archive.org/download/qurani-yasser-aldosari-prayers/"

def clean_title(title):
    t = re.sub(r'(القارئ|الشيخ)?\s*(د\.\s*)?ياسر\s+الدوسري', '', title)
    t = re.sub(r'للغرّيد', '', t)
    t = re.sub(r'للغريد', '', t)
    t = re.sub(r'[\U00010000-\U0010ffff]', '', t)
    t = t.replace('\u2764\ufe0f', '').replace('\u2764', '').replace('!', '').replace('؟', '')
    t = re.sub(r'\s+', ' ', t).strip(' |-_')
    return t

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
            "name": clean_title(it.get("title", "")),
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
    print(f"Generated {OUTPUT_PATH.name} with {len(tracks)} tracks.")

if __name__ == "__main__":
    main()
