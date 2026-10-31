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
    'HbpmP8Rgkrs', 'dgvsyr_ed5k', 'u0b312zRzDk', '5jqyRZaml7o', 'hu9CBlHuhjs'
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
    cleaned_catalog = [item for item in catalog if not any(x in item.get("id", "") for x in NON_QURAN_IDS)]
    removed_count = before_cat_len - len(cleaned_catalog)
    
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Catalog cleaned: removed {removed_count} items (remaining: {len(cleaned_catalog)} items)")
    
    # 2. Update Sync State (mark them as permanently excluded so sync never re-downloads them)
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)
        
    for vid in NON_QURAN_IDS:
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
