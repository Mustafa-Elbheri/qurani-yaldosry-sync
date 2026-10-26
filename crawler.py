import os
import json
import re
import subprocess
from bs4 import BeautifulSoup

BASE_URL = "http://yaldosry.com"

def fetch_html(url):
    """Fetch URL using curl.exe with HTTP/1.1 for speed and stability."""
    cmd = ["curl.exe", "-s", "--http1.1", "--no-keepalive", "--max-time", "20", url]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=False, check=True)
        return proc.stdout.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def get_section_categories(section_name):
    """Get all subcategories (e.g. years or albums) for a section."""
    url = f"{BASE_URL}/{section_name}"
    html = fetch_html(url)
    soup = BeautifulSoup(html, 'html.parser')
    
    categories = []
    seen = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if f'/{section_name}/c/' in href and href not in seen:
            seen.add(href)
            cat_name = a.get_text(strip=True)
            categories.append({
                "section": section_name,
                "category_name": cat_name,
                "url": href
            })
    return categories

def get_category_items(cat_url, section_name):
    """Get all recitation items in a category."""
    html = fetch_html(cat_url)
    soup = BeautifulSoup(html, 'html.parser')
    
    items = []
    seen = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if f'/{section_name}/' in href and '/c/' not in href and href not in seen:
            h6 = a.find('h6')
            title = h6.get_text(strip=True) if h6 else a.get_text(strip=True)
            if title and re.search(r'\d+$', href):
                seen.add(href)
                item_id = re.search(r'(\d+)$', href).group(1)
                
                # Check for image thumbnail
                img = a.find('img')
                thumbnail = img['src'] if img and 'src' in img.attrs else ""
                
                items.append({
                    "id": item_id,
                    "title": title,
                    "url": href,
                    "thumbnail": thumbnail
                })
    return items

def get_item_media(item_url):
    """Extract audio MP3 URL and YouTube link from a single recitation page."""
    html = fetch_html(item_url)
    soup = BeautifulSoup(html, 'html.parser')
    
    source = soup.find('source')
    audio_url = source['src'] if source else None
    
    if not audio_url:
        dl_a = soup.find('a', href=lambda h: h and h.endswith('.mp3'))
        if dl_a:
            audio_url = dl_a['href']
            
    iframe = soup.find('iframe')
    youtube_url = iframe['src'] if iframe else None
    
    h2 = soup.find('h2', class_='title')
    full_title = h2.get_text(strip=True) if h2 else None
    
    return {
        "audio_url": audio_url,
        "youtube_url": youtube_url,
        "full_title": full_title
    }

def crawl_category(cat_dict):
    """Crawl all items inside one category and extract media links."""
    section = cat_dict["section"]
    cat_name = cat_dict["category_name"]
    cat_url = cat_dict["url"]
    
    print(f"Crawling [{section}] -> {cat_name} ({cat_url})...")
    raw_items = get_category_items(cat_url, section)
    print(f"  Found {len(raw_items)} items. Extracting audio links...")
    
    full_items = []
    for idx, item in enumerate(raw_items, 1):
        media = get_item_media(item["url"])
        if media["audio_url"]:
            full_item = {
                "id": item["id"],
                "title": media["full_title"] or item["title"],
                "section": section,
                "category": cat_name,
                "page_url": item["url"],
                "source_audio_url": media["audio_url"],
                "youtube_url": media["youtube_url"],
                "thumbnail": item["thumbnail"]
            }
            full_items.append(full_item)
            print(f"    [{idx}/{len(raw_items)}] {full_item['title'][:40]}... -> OK")
        else:
            print(f"    [{idx}/{len(raw_items)}] {item['title'][:40]}... -> NO AUDIO")
            
    return full_items

if __name__ == "__main__":
    import sys
    sec = sys.argv[1] if len(sys.argv) > 1 else "prayers"
    cats = get_section_categories(sec)
    print(f"Found {len(cats)} categories in section '{sec}'")
    for c in cats:
        print(f" - {c['category_name']}: {c['url']}")
