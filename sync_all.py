import os
import sys
import argparse
import time
import crawler
import uploader

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
        cat_items = crawler.crawl_category(c)
        print(f"  Extracted {len(cat_items)} valid recitations from {cat_name}.")
        
        for item in cat_items:
            item_id = str(item["id"])
            if item_id in state and state[item_id].get("archive_url"):
                print(f"  - Item {item_id} already synced: {state[item_id]['archive_url']}")
                continue
                
            res = uploader.upload_recitation(item)
            if res:
                total_uploaded += 1
                
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
