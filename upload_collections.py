import os
import sys
import time
import requests
import json
from pathlib import Path
import internetarchive as ia

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Enforce direct connection for all Archive.org traffic (Fixed runner IP - anti-spam)
os.environ["NO_PROXY"] = "archive.org,*.archive.org,s3.us.archive.org,ia601904.us.archive.org,127.0.0.1,localhost,api.ipify.org"
os.environ["no_proxy"] = "archive.org,*.archive.org,s3.us.archive.org,ia601904.us.archive.org,127.0.0.1,localhost,api.ipify.org"

def get_fixed_runner_ip():
    try:
        r = requests.get("https://api.ipify.org", timeout=10, proxies={"http": None, "https": None})
        return r.text.strip()
    except Exception:
        return "Unknown"

ROOT = Path(__file__).resolve().parent
JSON_FILE = ROOT / "aldosari_prayers.json"
IDENTIFIER = "qurani-yasser-aldosari-prayers"

def upload_catalog_with_resilience():
    if not JSON_FILE.exists():
        print(f"Error: {JSON_FILE} not found!", flush=True)
        sys.exit(1)
        
    fixed_ip = get_fixed_runner_ip()
    print(f"Preparing to upload {JSON_FILE.name} ({JSON_FILE.stat().st_size} bytes) to {IDENTIFIER}...", flush=True)
    print(f"Runner Fixed Direct Egress IP: {fixed_ip} (Archive.org Anti-Spam Fixed IP)", flush=True)
    
    # Verify local file order first
    data = json.loads(JSON_FILE.read_text(encoding="utf-8"))
    tracks = data.get("tracks", [])
    print(f"Local tracks count: {len(tracks)}", flush=True)
    if tracks:
        print(f"Track #1: {tracks[0]['number']} - {tracks[0]['name']}", flush=True)
        print(f"Track #{len(tracks)}: {tracks[-1]['number']} - {tracks[-1]['name']}", flush=True)
        
    max_attempts = 20
    for attempt in range(1, max_attempts + 1):
        print(f"\n[Attempt {attempt}/{max_attempts}] Uploading to Archive.org via Fixed IP {fixed_ip}...", flush=True)
        try:
            item = ia.get_item(IDENTIFIER)
            resp = item.upload_file(
                str(JSON_FILE),
                key=JSON_FILE.name,
                queue_derive=False,
                verbose=True,
                retries=5,
                retries_sleep=15,
                request_kwargs={"timeout": (15, 60)}
            )
            print("✅ Upload completed successfully!", flush=True)
            
            # Verify live content
            print("Verifying uploaded catalog on Archive.org...", flush=True)
            time.sleep(3)
            verify_url = f"https://archive.org/download/{IDENTIFIER}/{JSON_FILE.name}"
            v_resp = requests.get(verify_url, timeout=30, headers={"Cache-Control": "no-cache"}, proxies={"http": None, "https": None})
            if v_resp.status_code == 200:
                v_data = v_resp.json()
                v_tracks = v_data.get("tracks", [])
                print(f"Verified live track count: {len(v_tracks)}", flush=True)
                if v_tracks:
                    print(f"Live Track #1: {v_tracks[0]['number']} - {v_tracks[0]['name']}", flush=True)
                    print(f"Live Track #{len(v_tracks)}: {v_tracks[-1]['number']} - {v_tracks[-1]['name']}", flush=True)
                return True
            else:
                print(f"Warning: HTTP {v_resp.status_code} when verifying {verify_url}", flush=True)
                return True
        except Exception as e:
            err = str(e)
            print(f"Upload attempt {attempt} failed: {err}", flush=True)
            if any(term in err.lower() for term in ["bucket_tasks_queued", "503", "slowdown", "reduce your request rate"]):
                backoff = min(30 * attempt, 180)
                print(f"Archive.org queue busy. Sleeping {backoff}s before retry...", flush=True)
                time.sleep(backoff)
            else:
                print("Sleeping 15s before retry...", flush=True)
                time.sleep(15)
                
    print(f"❌ Failed to upload after {max_attempts} attempts.", flush=True)
    return False

if __name__ == "__main__":
    success = upload_catalog_with_resilience()
    if not success:
        sys.exit(1)
