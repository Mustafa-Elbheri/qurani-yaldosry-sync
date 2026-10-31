import os
import sys
import json
import re
import subprocess
import time
import threading
import socket
import requests
import uploader

# Universal TCP socket timeout: prevents any hung network connection from blocking forever
socket.setdefaulttimeout(120)

class ArchiveGlobalLimitExceeded(Exception):
    """Raised when Archive.org account reaches total_tasks_queued global_limit."""
    pass

ARCHIVE_UPLOAD_LOCK = threading.Lock()
PROXY_ROTATION_LOCK = threading.Lock()
LAST_ROTATION_TIME = 0

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Enforce direct connection for all Archive.org traffic (Fixed runner IP - anti-spam)
os.environ["NO_PROXY"] = "archive.org,*.archive.org,s3.us.archive.org,ia601904.us.archive.org,127.0.0.1,localhost,api.ipify.org"
os.environ["no_proxy"] = "archive.org,*.archive.org,s3.us.archive.org,ia601904.us.archive.org,127.0.0.1,localhost,api.ipify.org"

CHANNEL_VIDEOS_URL = "https://www.youtube.com/channel/UClncV9OLPto_MinRzGfjr2g/videos"

INTERCEPTION_KEYWORDS = [
    "429", "too many requests", "sign in to confirm", "not a bot", "bot detection",
    "automated queries", "captcha", "403 forbidden", "http error 403", "use --cookies",
    "confirm you're human", "blocked", "rate limit"
]

def is_youtube_blocked(output_text):
    """Detects whether YouTube returned a rate-limit, captcha, or bot block challenge."""
    if not output_text:
        return False
    low = output_text.lower()
    return any(kw in low for kw in INTERCEPTION_KEYWORDS)

def get_fixed_runner_ip():
    """Returns the native, fixed public IP of the runner machine (bypassing all proxies)."""
    try:
        r = requests.get("https://api.ipify.org", timeout=10, proxies={"http": None, "https": None})
        return r.text.strip()
    except Exception:
        return "Unknown"

def get_youtube_proxy_ip():
    """Returns the current YouTube egress IP routed through Cloudflare WARP proxy."""
    try:
        res = subprocess.run(
            ["curl", "-s", "--socks5-hostname", "127.0.0.1:40000", "--max-time", "10", "https://api.ipify.org"],
            capture_output=True, text=True, timeout=12
        )
        return res.stdout.strip()
    except Exception:
        return "Unknown"

def rotate_youtube_proxy(force_new_registration=False, min_interval=5):
    """
    Rotates the egress IP for YouTube by reconnecting Cloudflare WARP.
    - Changes YouTube egress IP per batch and whenever YouTube intercepts.
    - Leaves Archive.org upload IP completely untouched (direct fixed IP).
    """
    global LAST_ROTATION_TIME
    if not os.environ.get("GITHUB_ACTIONS"):
        return None
        
    with PROXY_ROTATION_LOCK:
        now = time.time()
        if now - LAST_ROTATION_TIME < min_interval:
            return get_youtube_proxy_ip()
            
        print("\n🔄 [YouTube IP Rotation] Rotating Cloudflare WARP proxy egress IP...", flush=True)
        try:
            subprocess.run(["warp-cli", "--accept-tos", "disconnect"], capture_output=True, text=True, timeout=15)
            time.sleep(2)
            
            if force_new_registration:
                print("🔄 [YouTube IP Rotation] Registering fresh WARP client identity for brand-new IP...", flush=True)
                subprocess.run(["warp-cli", "--accept-tos", "registration", "delete"], capture_output=True, text=True, timeout=15)
                time.sleep(1)
                subprocess.run(["warp-cli", "--accept-tos", "registration", "new"], capture_output=True, text=True, timeout=15)
                subprocess.run(["warp-cli", "--accept-tos", "mode", "proxy"], capture_output=True, text=True, timeout=15)
                subprocess.run(["warp-cli", "--accept-tos", "proxy", "port", "40000"], capture_output=True, text=True, timeout=15)
                
            subprocess.run(["warp-cli", "--accept-tos", "connect"], capture_output=True, text=True, timeout=15)
            time.sleep(3)
            
            new_ip = get_youtube_proxy_ip()
            LAST_ROTATION_TIME = time.time()
            print(f"✅ [YouTube IP Rotation] New Active YouTube Egress IP: {new_ip}\n", flush=True)
            return new_ip
        except Exception as e:
            print(f"⚠️ [YouTube IP Rotation Warning] {e}", flush=True)
            return None

def get_cookie_file():
    # Never use browser cookies in GitHub Actions to avoid datacenter bot challenge
    if os.environ.get("GITHUB_ACTIONS"):
        return None
    if os.path.exists("cookies.txt") and os.path.getsize("cookies.txt") > 0:
        return "cookies.txt"
    return None

def get_channel_long_videos(limit=50):
    """
    Fetches only long videos from the /videos tab.
    Completely ignores Shorts (shorts are in /shorts tab).
    """
    print(f"Fetching long videos from channel: {CHANNEL_VIDEOS_URL} ...", flush=True)
    cmd = [
        "yt-dlp",
        "--socket-timeout", "30",
        "--retries", "3",
        "--flat-playlist",
        "--dump-single-json",
        "--extractor-args", "youtube:player_client=visionos,mweb,web",
        "--playlist-items", f"1:{limit}"
    ]
    if os.environ.get("GITHUB_ACTIONS"):
        cmd.extend(["--proxy", "socks5://127.0.0.1:40000"])
    cookie_file = get_cookie_file()
    if cookie_file:
        cmd.extend(["--cookies", cookie_file])
    cmd.append(CHANNEL_VIDEOS_URL)
    
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=300)
        data = json.loads(proc.stdout)
        entries = data.get("entries", [])
        return entries
    except Exception as e:
        print(f"Error fetching channel videos: {e}", flush=True)
        return []

def get_playlist_videos(playlist_id, limit=None):
    """Fetch videos from a specific playlist."""
    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    print(f"Fetching playlist: {url} ...", flush=True)
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-single-json",
        "--extractor-args", "youtube:player_client=visionos,mweb,web"
    ]
    cookie_file = get_cookie_file()
    if cookie_file:
        cmd.extend(["--cookies", cookie_file])
    cmd.append(url)
    if limit:
        cmd.extend(["--playlist-items", f"1:{limit}"])
        
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    try:
        data = json.loads(proc.stdout)
        return data.get("entries", []), data.get("title", "")
    except Exception as e:
        print(f"Error fetching playlist: {e}", flush=True)
        return [], ""

def download_youtube_audio_and_thumb(video_id, output_base):
    """
    Downloads YouTube audio as MP3 and downloads HD thumbnail.
    Rotates YouTube proxy IP immediately if YouTube intercepts or rate-limits.
    Returns: (mp3_path, thumb_path)
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    mp3_path = f"{output_base}.mp3"
    thumb_path = f"{output_base}.jpg"
    
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        cmd_audio = [
            "yt-dlp",
            "--socket-timeout", "30",
            "--retries", "2",
            "--remote-components", "ejs:github",
            "--extractor-args", "youtube:player_client=visionos,mweb,web",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", f"{output_base}.%(ext)s"
        ]
        if os.environ.get("GITHUB_ACTIONS"):
            cmd_audio.extend(["--proxy", "socks5://127.0.0.1:40000"])
        cookie_file = get_cookie_file()
        if cookie_file:
            cmd_audio.extend(["--cookies", cookie_file])
            
        cmd_audio.append(video_url)
        
        res_audio = None
        try:
            res_audio = subprocess.run(cmd_audio, capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired:
            print(f"  [Timeout] yt-dlp timed out downloading audio for {video_id}", flush=True)
            
        if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1000:
            break
            
        err_output = ""
        if res_audio:
            err_output = f"{res_audio.stderr} {res_audio.stdout}"
            
        blocked = is_youtube_blocked(err_output)
        if blocked or not os.path.exists(mp3_path):
            if blocked:
                print(f"  🚨 [YouTube Interception Detected] (Attempt {attempt}/{max_attempts}) YouTube intercepted {video_id}!", flush=True)
            else:
                print(f"  ⚠️ [Download Incomplete] (Attempt {attempt}/{max_attempts}) Failed to produce audio for {video_id}.", flush=True)
                
            if attempt < max_attempts and os.environ.get("GITHUB_ACTIONS"):
                print("  🔄 [Action] Rotating YouTube egress IP immediately and retrying...", flush=True)
                rotate_youtube_proxy(force_new_registration=True)
                time.sleep(3)
                continue
                
    # Fallback without proxy (direct runner IP with BGUtil PO Token)
    if (not os.path.exists(mp3_path) or os.path.getsize(mp3_path) < 1000) and os.environ.get("GITHUB_ACTIONS"):
        print(f"  [Direct Fallback] Retrying {video_id} directly with PO Token provider...", flush=True)
        cmd_direct = [arg for arg in cmd_audio if arg != "--proxy" and arg != "socks5://127.0.0.1:40000"]
        try:
            subprocess.run(cmd_direct, capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired:
            pass

    if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) < 1000:
        print(f"  ERROR: Failed to download audio for {video_id} after all attempts.", flush=True)
        return None, None
        
    # Download highest quality thumbnail
    thumb_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    r = requests.get(thumb_url, timeout=10)
    if r.status_code != 200:
        thumb_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        r = requests.get(thumb_url, timeout=10)
        
    if r.status_code == 200:
        with open(thumb_path, "wb") as f:
            f.write(r.content)
            
    return mp3_path, thumb_path

KHUTBAH_KEYWORDS = [
    "خطبة", "الخطبة", "محاضرة", "كلمة", "درس", "خطبة الجمعة",
    "لقاء", "ندوة", "برنامج", "مؤتمر", "حوار", "تعليق"
]

def is_khutbah(title, category_name=""):
    """Returns True if the video is a sermon/speech, so it gets excluded permanently."""
    text = f"{title} {category_name}".strip()
    for kw in KHUTBAH_KEYWORDS:
        if kw in text:
            return True
    return False

def sync_youtube_video(video_entry, category_name="صلوات الحرم المكي"):
    """Sync a single YouTube video to Archive.org with full metadata."""
    video_id = video_entry.get("id")
    title = video_entry.get("title", "")
    
    # 1. Ignore Shorts permanently
    if "#shorts" in title.lower():
        print(f"Skipping Short (excluded): {title}", flush=True)
        return None
        
    # 2. Ignore Sermons/Khutbahs permanently
    if is_khutbah(title, category_name):
        print(f"Skipping Sermon/Khutbah (excluded permanently): {title}", flush=True)
        return None
        
    state = uploader.load_state()
    item_key = f"yt_{video_id}"
    
    if item_key in state and state[item_key].get("archive_url"):
        print(f"Skipping {item_key}: Already synced -> {state[item_key]['archive_url']}", flush=True)
        return state[item_key]
        
    print(f"\n[YouTube Sync] ID: {video_id} | Title: {title}", flush=True)
    temp_dir = os.environ.get("TEMP", ".")
    temp_base = os.path.join(temp_dir, f"yt_{video_id}")
    
    # Download audio and thumb
    print("  Downloading high-quality audio and HD thumbnail from YouTube...", flush=True)
    mp3_file, jpg_file = download_youtube_audio_and_thumb(video_id, temp_base)
    if not mp3_file:
        return None
        
    try:
        # Generate standard filenames
        item_dict = {
            "id": item_key,
            "title": title,
            "section": "prayers",
            "category": category_name
        }
        base_name, track, date_str, year_str = uploader.generate_standard_filenames(item_dict)
        remote_mp3 = f"{base_name}.mp3"
        remote_jpg = f"{base_name}.jpg"
        
        target_identifier = "qurani-yasser-aldosari-prayers"
        files_to_upload = {remote_mp3: mp3_file}
        if os.path.exists(jpg_file):
            files_to_upload[remote_jpg] = jpg_file
            
        metadata = {
            "title": title,
            "creator": "الشيخ د. ياسر الدوسري",
            "mediatype": "audio",
            "collection": "opensource_audio",
            "language": "ara",
            "date": date_str,
            "year": year_str,
            "subject": f"القرآن الكريم; تلاوات الحرم المكي; الشيخ د. ياسر الدوسري; صلوات الحرم; {category_name}",
            "description": f"تلاوة خاشعة للشيخ د. ياسر الدوسري من الحرم المكي الشريف لتطبيق قرآني - المصدر الرسمي: https://www.youtube.com/watch?v={video_id}"
        }
        
        import internetarchive as ia
        
        # Upload serialized across threads via Fixed Direct Runner IP
        with ARCHIVE_UPLOAD_LOCK:
            fixed_ip = get_fixed_runner_ip()
            print(f"  [Archive.org Direct Egress] Uploading to {target_identifier} via Fixed Runner IP: {fixed_ip} (Anti-Spam Fixed IP)...", flush=True)
            max_upload_retries = 5
            upload_success = False
            last_upload_err = None
            for attempt in range(1, max_upload_retries + 1):
                try:
                    ia.upload(
                        target_identifier,
                        files=files_to_upload,
                        metadata=metadata,
                        queue_derive=False,
                        verbose=False,
                        request_kwargs={"timeout": (15, 90)}
                    )
                    upload_success = True
                    time.sleep(3)
                    break
                except Exception as upload_err:
                    last_upload_err = upload_err
                    err_msg = str(upload_err).lower()
                    if "total_tasks_queued" in err_msg or "global_limit" in err_msg:
                        print(f"  [Archive.org Global Limit] Account task queue is at maximum server capacity: {upload_err}", flush=True)
                        raise ArchiveGlobalLimitExceeded(upload_err)
                    is_rate_limit = any(k in err_msg for k in ["bucket_tasks_queued", "reduce your request rate", "slow down", "503", "429", "rationed amount"])
                    if is_rate_limit:
                        wait_time = 45 * attempt
                        print(f"  [Archive.org Queue Saturated] Server task limit hit. Waiting {wait_time}s for queue to drain (Attempt {attempt}/{max_upload_retries})...", flush=True)
                        time.sleep(wait_time)
                    else:
                        if attempt == max_upload_retries:
                            break
                        print(f"  [Upload Warning] {upload_err}. Retrying in 15s (Attempt {attempt}/{max_upload_retries})...", flush=True)
                        time.sleep(15)
                        
            if not upload_success:
                print(f"  ERROR: Upload permanently failed after {max_upload_retries} attempts: {last_upload_err}", flush=True)
                raise last_upload_err
        
        archive_url = f"https://archive.org/download/{target_identifier}/{remote_mp3}"
        archive_cover = f"https://archive.org/download/{target_identifier}/{remote_jpg}" if os.path.exists(jpg_file) else ""
        file_size_mb = round(os.path.getsize(mp3_file) / (1024 * 1024), 2)
        
        record = {
            "id": item_key,
            "youtube_id": video_id,
            "title": title,
            "standard_name": base_name,
            "section": "prayers",
            "category": category_name,
            "track": track,
            "date": date_str,
            "year": year_str,
            "source_type": "youtube",
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
            "archive_url": archive_url,
            "archive_cover_url": archive_cover,
            "size_mb": file_size_mb,
            "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        state[item_key] = record
        uploader.save_state(state)
        
        catalog = uploader.load_catalog()
        catalog = [c for c in catalog if c.get("id") != item_key]
        catalog.append(record)
        uploader.save_catalog(catalog)
        
        print(f"  SUCCESS! Archive URL: {archive_url}", flush=True)
        return record
        
    finally:
        for p in [mp3_file, jpg_file]:
            if p and os.path.exists(p):
                try: os.remove(p)
                except Exception: pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync long videos from YouTube channel to Archive.org")
    parser.add_argument("--limit", type=int, default=50, help="Number of videos to sync (default: 50)")
    parser.add_argument("--playlist", type=str, default=None, help="Specific playlist ID to sync")
    args = parser.parse_args()
    
    if args.playlist:
        videos, p_title = get_playlist_videos(args.playlist, args.limit)
        if is_khutbah(p_title):
            print(f"Skipping entire playlist '{p_title}' because it contains sermons/khutbahs.", flush=True)
            sys.exit(0)
            
        print(f"Syncing {len(videos)} videos from playlist: {p_title}", flush=True)
        for v in videos:
            sync_youtube_video(v, category_name=p_title)
            time.sleep(2)
    else:
        videos = get_channel_long_videos(args.limit)
        print(f"Syncing latest {len(videos)} long videos...", flush=True)
        for v in videos:
            sync_youtube_video(v)
            time.sleep(2)
