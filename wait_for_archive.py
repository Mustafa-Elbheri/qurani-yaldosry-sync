import os
import sys
import time
import requests
import internetarchive as ia

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Enforce direct connection for all Archive.org traffic (Fixed runner IP)
os.environ["NO_PROXY"] = "archive.org,*.archive.org,s3.us.archive.org,ia601904.us.archive.org,127.0.0.1,localhost,api.ipify.org"
os.environ["no_proxy"] = "archive.org,*.archive.org,s3.us.archive.org,ia601904.us.archive.org,127.0.0.1,localhost,api.ipify.org"

IDENTIFIER = "qurani-yasser-aldosari-prayers"

def get_fixed_runner_ip():
    try:
        r = requests.get("https://api.ipify.org", timeout=10, proxies={"http": None, "https": None})
        return r.text.strip()
    except Exception:
        return "Unknown"

def wait_for_archive_processing(identifier=IDENTIFIER, max_wait_seconds=3600, poll_interval=20):
    fixed_ip = get_fixed_runner_ip()
    print("=" * 75, flush=True)
    print("⏳ ARCHIVE.ORG BATCH PROCESSING WATCHDOG (SAME RUNNER IP)", flush=True)
    print(f"Runner Fixed Direct Egress IP: {fixed_ip}", flush=True)
    print(f"Target Item: {identifier}", flush=True)
    print("Holding machine alive on this SAME IP until Archive.org finishes all tasks for this batch...", flush=True)
    print("=" * 75, flush=True)
    
    session = ia.get_session()
    catalog = ia.Catalog(session)
    start_time = time.time()
    zero_stable_count = 0
    
    while True:
        elapsed_sec = int(time.time() - start_time)
        if elapsed_sec > max_wait_seconds:
            print(f"\n⚠️ Maximum wait limit reached ({max_wait_seconds}s). Moving to catalog update.", flush=True)
            break
            
        try:
            summary = catalog.get_summary(identifier)
            queued = summary.get("queued", 0)
            running = summary.get("running", 0)
            
            print(f"[{elapsed_sec:4d}s elapsed | Fixed IP: {fixed_ip}] Tasks status: {running} running, {queued} queued", flush=True)
            
            if queued == 0 and running == 0:
                zero_stable_count += 1
                if zero_stable_count >= 2:
                    print(f"\n✅ All Archive.org tasks processed to completion on this runner IP ({fixed_ip})!", flush=True)
                    break
                else:
                    time.sleep(5)
                    continue
            else:
                zero_stable_count = 0
                
            # Inspect active tasks
            try:
                tasks = list(catalog.get_tasks(identifier, params={"catalog": 1, "limit": 10}))
                task_cmds = [getattr(t, "cmd", "") for t in tasks]
                # If no file-ingestion (archive.php) tasks are queued or running, file moves are done
                has_file_ingestion = any(cmd == "archive.php" for cmd in task_cmds)
                if not has_file_ingestion and queued <= 2 and running == 0:
                    print(f"\nℹ️ Only non-ingestion background tasks remain ({task_cmds}). Batch file ingestion is 100% finished!", flush=True)
                    break
            except Exception:
                pass
                    
        except Exception as e:
            print(f"  [Watchdog Check Warning] {e}", flush=True)
            
        time.sleep(poll_interval)
        
    duration_min = round((time.time() - start_time) / 60, 2)
    print(f"🏁 Watchdog concluded on runner IP {fixed_ip} after {duration_min} minutes.", flush=True)
    return True

if __name__ == "__main__":
    wait_for_archive_processing()
