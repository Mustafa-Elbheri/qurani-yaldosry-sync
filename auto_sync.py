import os
import sys
import json
import time
import requests
from bs4 import BeautifulSoup
import uploader

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://yaldosry.com"

def check_and_sync_recent():
    """Fetch the latest recitations from the homepage and upload any new ones to Archive.org."""
    print("Checking for recent recitations on yaldosry.com...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ar,en-US;q=0.7,en;q=0.3"
    }
    
    try:
        res = requests.get(BASE_URL, headers=headers, timeout=20)
        res.raise_for_status()
    except Exception as e:
        print(f"Error connecting to {BASE_URL}: {e}")
        return
        
    soup = BeautifulSoup(res.text, "html.parser")
    recent_box = soup.find("div", {"id": "tab-recent"})
    if not recent_box:
        print("Could not find '#tab-recent' block.")
        return
        
    state = uploader.load_state()
    items_to_sync = []
    
    for li in recent_box.find_all("li", class_="item"):
        a_tag = li.find("a")
        if not a_tag or not a_tag.get("href"):
            continue
        item_url = a_tag["href"]
        item_id_match = item_url.split("/")[-1]
        
        # Check if already processed
        if item_id_match in state and state[item_id_match].get("archive_url"):
            continue
            
        h6 = li.find("h6")
        title = h6.get_text(strip=True) if h6 else "تلاوة جديدة"
        
        img = li.find("img")
        thumbnail = img["src"] if img and "src" in img.attrs else ""
        
        # Determine section (e.g. prayers or taraweeh)
        section = "prayers"
        if "taraweeh" in item_url:
            section = "taraweeh"
        elif "quran" in item_url:
            section = "quran"
            
        items_to_sync.append({
            "id": item_id_match,
            "title": title,
            "url": item_url,
            "thumbnail": thumbnail,
            "section": section
        })
        
    if not items_to_sync:
        print("No new recitations found. Everything is up to date!")
        return
        
    print(f"Found {len(items_to_sync)} new recitations to sync.")
    for item in items_to_sync:
        print(f"Fetching media for item {item['id']} ({item['url']})...")
        try:
            r_item = requests.get(item["url"], headers=headers, timeout=20)
            soup_item = BeautifulSoup(r_item.text, "html.parser")
            source = soup_item.find("source")
            audio_url = source["src"] if source else None
            
            if not audio_url:
                dl = soup_item.find("a", href=lambda h: h and h.endswith(".mp3"))
                if dl:
                    audio_url = dl["href"]
                    
            if not audio_url:
                print(f"Skipping {item['id']}: no audio found.")
                continue
                
            iframe = soup_item.find("iframe")
            youtube_url = iframe["src"] if iframe else None
            
            item_payload = {
                "id": item["id"],
                "title": item["title"],
                "section": item["section"],
                "category": "الصوتيات الحديثة",
                "page_url": item["url"],
                "source_audio_url": audio_url,
                "youtube_url": youtube_url,
                "thumbnail": item["thumbnail"]
            }
            
            uploader.upload_recitation(item_payload)
            time.sleep(2)
        except Exception as e:
            print(f"Error processing item {item['id']}: {e}")

if __name__ == "__main__":
    check_and_sync_recent()
