import os
import sys
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import youtube_sync
import uploader

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
        
    # 2. Skip Khutbahs / Sermons
    if youtube_sync.is_khutbah(title):
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
                print(f"==> PROGRESS: [{total_done}/{total_all}] Finished in {t_elapsed}s | {title[:50]}...")
            return record
    except youtube_sync.ArchiveGlobalLimitExceeded as e:
        print(f"\n[Archive.org Queue Cooldown Triggered] Server account limit reached: {e}. Pausing batch gracefully.")
        STOP_SYNC.set()
        return None
    except Exception as e:
        print(f"Error processing video {video_id}: {e}")
        return None

def start_bulk_sync(max_workers=3, limit=None):
    """Starts high-speed parallel sync for the entire channel."""
    print("=" * 70)
    print("🚀 STARTING HIGH-SPEED BULK SYNC (PARALLEL WORKERS)")
    print("=" * 70)
    
    # Fetch all video IDs across the entire channel
    print("Fetching channel catalog from YouTube (excluding shorts)...")
    all_videos = youtube_sync.get_channel_long_videos(limit=2500)
    
    # Filter out khutbahs and shorts in advance
    filtered_videos = []
    for v in all_videos:
        title = v.get("title", "")
        if "#shorts" not in title.lower() and not youtube_sync.is_khutbah(title):
            filtered_videos.append(v)
            
    print(f"Total pure Quran recitations found on channel: {len(filtered_videos)}")
    
    # Check already synced
    state = uploader.load_state()
    pending = [v for v in filtered_videos if f"yt_{v.get('id')}" not in state]
    already_done = len(filtered_videos) - len(pending)
    print(f"Already synced previously: {already_done} items.")
    print(f"Total remaining items to upload: {len(pending)} items.\n")
    
    if not pending:
        print("🎉 Everything is already synced! All channel recitations are on Archive.org.")
        return
        
    # Take requested batch size from pending
    if limit:
        batch_items = pending[:limit]
    else:
        batch_items = pending
        
    print(f"Processing this batch of {len(batch_items)} recitations...")
    
    progress_info = {
        "completed": already_done,
        "skipped": already_done,
        "total": len(filtered_videos)
    }
    
    print(f"Launching {max_workers} parallel workers for maximum speed...\n")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_video, v, progress_info): v for v in batch_items}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Worker exception: {e}")
                
    total_time_mins = round((time.time() - start_time) / 60, 2)
    new_in_this_run = progress_info["completed"] - progress_info["skipped"]
    with open("last_run_stats.json", "w", encoding="utf-8") as f:
        json.dump({"new_synced": new_in_this_run, "total": progress_info["completed"]}, f)
        
    print("\n" + "=" * 70)
    print(f"🏁 BULK SYNC COMPLETED in {total_time_mins} minutes!")
    print(f"Newly uploaded in this run: {new_in_this_run} items.")
    print(f"Total recitations in Archive.org: {progress_info['completed']}")
    print("=" * 70)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="High-Speed Parallel Bulk Sync")
    parser.add_argument("--workers", type=int, default=3, help="Number of concurrent workers (default: 3)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of videos to sync")
    args = parser.parse_args()
    
    start_bulk_sync(max_workers=args.workers, limit=args.limit)
