import os
import sys
import json
import time
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import youtube_sync
import uploader

socket.setdefaulttimeout(120)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

STATE_LOCK = threading.Lock()
STOP_SYNC = threading.Event()

def process_single_video(video_entry, progress_info):
    """Worker function to process and upload a single video."""
    if STOP_SYNC.is_set():
        return None
    video_id = video_entry.get("id")
    title = video_entry.get("title", "")
    
    # 1. Skip Shorts
    if "#shorts" in title.lower():
        return None
        
    # 2. Skip Khutbahs / Sermons / Lessons
    if video_id in youtube_sync.EXCLUDED_VIDEO_IDS or youtube_sync.is_khutbah(title):
        return None
        
    item_key = f"yt_{video_id}"
    
    # Check state with thread lock
    with STATE_LOCK:
        state = uploader.load_state()
        if item_key in state and state[item_key].get("archive_url"):
            progress_info["skipped"] += 1
            return None
            
    # Process sync
    try:
        t0 = time.time()
        record = youtube_sync.sync_youtube_video(video_entry)
        t_elapsed = round(time.time() - t0, 1)
        
        # Polite delay to avoid YouTube session rate-limits
        time.sleep(3)
        
        with STATE_LOCK:
            if record:
                progress_info["completed"] += 1
                total_done = progress_info["completed"]
                total_all = progress_info["total"]
                print(f"==> PROGRESS: [{total_done}/{total_all}] Finished in {t_elapsed}s | {title[:50]}...", flush=True)
            return record
    except youtube_sync.ArchiveGlobalLimitExceeded as e:
        print(f"\n[Archive.org Queue Cooldown Triggered] Server account limit reached: {e}. Pausing batch gracefully.", flush=True)
        STOP_SYNC.set()
        return None
    except Exception as e:
        print(f"Error processing video {video_id}: {e}", flush=True)
        return None

def start_bulk_sync(max_workers=1, limit=50):
    """Starts strictly sequential sync (1-by-1) for the channel in batches of 50."""
    print("=" * 75, flush=True)
    print(f"🚀 STARTING CLOUD BULK SYNC (BATCH SIZE: {limit} | ZERO LOCAL BANDWIDTH)", flush=True)
    print("=" * 75, flush=True)
    
    fixed_runner_ip = youtube_sync.get_fixed_runner_ip()
    print(f"📍 Archive.org Fixed Direct Egress IP: {fixed_runner_ip} (Anti-Spam Fixed IP)", flush=True)
    
    # 0. PRE-FLIGHT CHECK: Archive.org Queue Health Gate
    # Do NOT touch YouTube or start any downloads if Archive.org is congested!
    print("Checking Archive.org queue health before touching YouTube...", flush=True)
    queued, running = youtube_sync.get_archive_queue_summary("qurani-yasser-aldosari-prayers")
    if queued is not None:
        print(f"Archive.org Bucket Queue: {queued} queued, {running} running (Safe Threshold: <= 25)", flush=True)
        if queued > 25:
            print(f"⚠️ Archive.org queue is congested ({queued} tasks queued > threshold 25).", flush=True)
            print(f"🛑 HALTING: Will NOT touch or download from YouTube while Archive.org is congested.", flush=True)
            print(f"Waiting gently for Archive.org cluster to drain queue below 25...", flush=True)
            wait_start = time.time()
            while queued > 25:
                time.sleep(30)
                queued, running = youtube_sync.get_archive_queue_summary("qurani-yasser-aldosari-prayers")
                if queued is None:
                    break
                elapsed = int(time.time() - wait_start)
                print(f"  [Queue Gate | {elapsed}s] {queued} queued, {running} running...", flush=True)
                if elapsed > 1800:
                    print("Queue did not drain within 30 minutes. Exiting cleanly to allow Archive.org to breathe.", flush=True)
                    return
            print("✅ Archive.org queue is now clean! Safe to proceed with YouTube downloads.", flush=True)
    
    # Fetch all video IDs across the entire channel
    print("Fetching channel catalog from YouTube (excluding shorts)...", flush=True)
    all_videos = youtube_sync.get_channel_long_videos(limit=2500)
    
    # Filter out khutbahs, lessons, and shorts in advance
    filtered_videos = []
    for v in all_videos:
        vid = v.get("id", "")
        title = v.get("title", "")
        if "#shorts" not in title.lower() and vid not in youtube_sync.EXCLUDED_VIDEO_IDS and not youtube_sync.is_khutbah(title):
            filtered_videos.append(v)
            
    print(f"Total pure Quran recitations found on channel: {len(filtered_videos)}", flush=True)
    
    # Check already synced
    state = uploader.load_state()
    pending = [v for v in filtered_videos if f"yt_{v.get('id')}" not in state]
    already_done = len(filtered_videos) - len(pending)
    print(f"Already synced previously: {already_done} items.", flush=True)
    print(f"Total remaining items to upload: {len(pending)} items.\n", flush=True)
    
    if not pending:
        print("🎉 Everything is already synced! All channel recitations are on Archive.org.", flush=True)
        return
        
    # Enforce batch size (Requirement 1: 50 recitations)
    batch_limit = limit if limit is not None else 50
    batch_items = pending[:batch_limit]
    
    print("=" * 75, flush=True)
    print(f"🎯 BATCH INITIALIZATION: Preparing {len(batch_items)} recitations", flush=True)
    
    # Requirement 4: Rotate YouTube Proxy IP at the beginning of each batch
    rotated_yt_ip = youtube_sync.rotate_youtube_proxy(force_new_registration=False)
    print(f"🌐 Dynamic YouTube Egress IP for this Batch: {rotated_yt_ip or 'Direct/Local'}", flush=True)
    print(f"🛡️ Fixed Archive.org Upload IP: {fixed_runner_ip} (Native Direct Runner IP)", flush=True)
    print("=" * 75, flush=True)
    
    progress_info = {
        "completed": already_done,
        "skipped": already_done,
        "total": len(filtered_videos)
    }
    
    start_time = time.time()
    
    if max_workers <= 1:
        print(f"🚀 Running STRICTLY SEQUENTIAL sync (1-by-1, 0 parallel threads) for {len(batch_items)} items.", flush=True)
        print("🛡️ Pacing: 5-second polite buffer between uploads to eliminate Archive.org 503 SlowDown.\n", flush=True)
        for idx, v in enumerate(batch_items, 1):
            if STOP_SYNC.is_set():
                print(f"\n🛑 Archive queue limit hit or stop signal active. Halting sequential batch at item {idx-1}/{len(batch_items)}.", flush=True)
                break
                
            v_title = v.get("title", "")[:50]
            print(f"\n--- [Item {idx}/{len(batch_items)}] Starting sequential processing: {v_title}... ---", flush=True)
            try:
                record = process_single_video(v, progress_info)
            except Exception as e:
                print(f"Error on item {idx}: {e}", flush=True)
                
            if STOP_SYNC.is_set():
                break
                
            if idx < len(batch_items):
                print("⏳ Sleeping 5s before next item to maintain healthy Archive.org pacing...", flush=True)
                time.sleep(5)
    else:
        print(f"Launching {max_workers} parallel cloud workers for safe upload pacing...\n", flush=True)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_single_video, v, progress_info): v for v in batch_items}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Worker exception: {e}", flush=True)
                
    total_time_mins = round((time.time() - start_time) / 60, 2)
    new_in_this_run = progress_info["completed"] - progress_info["skipped"]
    with open("last_run_stats.json", "w", encoding="utf-8") as f:
        json.dump({
            "new_synced": new_in_this_run,
            "total": progress_info["completed"],
            "queue_limited": STOP_SYNC.is_set()
        }, f)
        
    print("\n" + "=" * 75, flush=True)
    print(f"🏁 BATCH OF {len(batch_items)} COMPLETED in {total_time_mins} minutes!", flush=True)
    print(f"Newly uploaded in this run: {new_in_this_run} items.", flush=True)
    print(f"Total recitations in Archive.org: {progress_info['completed']}", flush=True)
    print("=" * 75, flush=True)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Strictly Sequential Sync in Batches of 50")
    parser.add_argument("--workers", type=int, default=1, help="Number of concurrent workers (default: 1 for sequential)")
    parser.add_argument("--limit", type=int, default=50, help="Limit number of videos to sync per batch (default: 50)")
    args = parser.parse_args()
    
    start_bulk_sync(max_workers=args.workers, limit=args.limit)
