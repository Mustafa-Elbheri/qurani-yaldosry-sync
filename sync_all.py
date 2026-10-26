import os
import sys
import argparse
import time
import crawler
import uploader

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

VALID_SECTIONS = ["prayers", "taraweeh", "quran", "editions", "miscellanies"]

def sync_section(section_name, target_category_name=None, max_items=None):
    """
    Crawls and uploads an entire section or a specific category within it.
    Supports resuming from sync_state.json automatically.
    """
    print(f"\n{'='*60}")
    print(f"Starting Sync for Section: [{section_name.upper()}]")
    print(f"{'='*60}")
    
    categories = crawler.get_section_categories(section_name)
    if not categories:
        print(f"No categories found for section {section_name}")
        return
        
    print(f"Found {len(categories)} categories in {section_name}:")
    for idx, c in enumerate(categories, 1):
        print(f"  {idx}. {c['category_name']}")
        
    state = uploader.load_state()
    total_uploaded = 0
    
    for c in categories:
        cat_name = c["category_name"]
        if target_category_name and target_category_name not in cat_name:
            continue
            
        print(f"\n>>> Processing Category: {cat_name} ...")
        raw_items = crawler.get_category_items(c["url"], section_name)
        print(f"  Found {len(raw_items)} items in {cat_name}.")
        
        for idx, item in enumerate(raw_items, 1):
            item_id = str(item["id"])
            if item_id in state and state[item_id].get("archive_url"):
                print(f"  [{idx}/{len(raw_items)}] Item {item_id} already synced: {state[item_id]['archive_url']}")
                continue
                
            print(f"  [{idx}/{len(raw_items)}] Fetching media for Item {item_id}: {item['title']} ...")
            media = crawler.get_item_media(item["url"])
            if not media["audio_url"]:
                print(f"    Warning: No audio found for {item_id}")
                continue
                
            full_item = {
                "id": item_id,
                "title": media["full_title"] or item["title"],
                "section": section_name,
                "category": cat_name,
                "page_url": item["url"],
                "source_audio_url": media["audio_url"],
                "youtube_url": media["youtube_url"],
                "thumbnail": item["thumbnail"]
            }
            
            res = uploader.upload_recitation_with_cover(full_item)
            if res:
                total_uploaded += 1
                state = uploader.load_state() # refresh state
                
            if max_items and total_uploaded >= max_items:
                print(f"\nReached max items limit ({max_items}). Stopping.")
                return
                
            time.sleep(1) # respectful delay between uploads
            
    print(f"\nFinished sync for section [{section_name}]. Newly uploaded: {total_uploaded} items.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync recitations from yaldosry.com to Archive.org section by section.")
    parser.add_argument("--section", choices=VALID_SECTIONS, default="prayers", help="Section to sync")
    parser.add_argument("--category", type=str, default=None, help="Filter by category name (e.g. '1448')")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of items to upload in this run")
    
    args = parser.parse_args()
    sync_section(args.section, args.category, args.limit)
