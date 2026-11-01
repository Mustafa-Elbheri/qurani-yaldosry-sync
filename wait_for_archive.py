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

def wait_for_archive_processing(identifier=IDENTIFIER, max_wait_seconds=3600, poll_interval=15):
    fixed_ip = get_fixed_runner_ip()
    print("=" * 75, flush=True)
    print("⏳ ARCHIVE.ORG FAST BATCH WATCHDOG (SAME RUNNER IP)", flush=True)
    print(f"Runner Fixed Direct Egress IP: {fixed_ip}", flush=True)
    print(f"Target Item: {identifier}", flush=True)
    print("Policy: Move to next machine immediately as soon as regular queue is clear (No waiting for derive.php).", flush=True)
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
            
            # Initial grace period (wait at least 30s to allow Archive S3 to queue the newly uploaded files)
            if elapsed_sec < 30:
                time.sleep(poll_interval)
                continue
                
            # Check 1: Regular file ingestion queue is completely empty (queued == 0)
            if queued == 0:
                zero_stable_count += 1
                if zero_stable_count >= 2:
                    print(f"\n✅ Regular Archive queue is completely empty (queued=0)! Batch files are 100% ingested.", flush=True)
                    print(f"Moving to next runner immediately without waiting for derive.php.", flush=True)
                    break
                else:
                    time.sleep(5)
                    continue
            else:
                zero_stable_count = 0
                
            # Check 2: Inspect active tasks - if no archive.php tasks exist, file ingestion is finished
            try:
                tasks = list(catalog.get_tasks(identifier, params={"catalog": 1, "limit": 20}))
                task_cmds = [getattr(t, "cmd", "") for t in tasks]
                has_file_ingestion = any(cmd == "archive.php" for cmd in task_cmds)
                if not has_file_ingestion:
                    print(f"\n✅ All file ingestion tasks (archive.php) are finished! Remaining tasks: {task_cmds}", flush=True)
                    print(f"Regular Archive queue is clear. Moving to next runner immediately without waiting for derive.php!", flush=True)
                    break
            except Exception:
                pass
                    
        except Exception as e:
            print(f"  [Watchdog Check Warning] {e}", flush=True)
            
        time.sleep(poll_interval)
        
    duration_min = round((time.time() - start_time) / 60, 2)
    print(f"🏁 Fast Watchdog concluded on runner IP {fixed_ip} after {duration_min} minutes.", flush=True)
    return True

if __name__ == "__main__":
    wait_for_archive_processing()
