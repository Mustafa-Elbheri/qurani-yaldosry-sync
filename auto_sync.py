import os
import sys
import json
import time
import youtube_sync

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def auto_sync_youtube(limit=15):
    """
    Checks the official YouTube channel for the latest long recitations.
    Filters out Shorts and syncs new recitations to Archive.org automatically.
    """
    print(f"Starting YouTube auto-sync for Sheikh Yasser Al-Dosari channel (checking latest {limit} long videos)...")
    videos = youtube_sync.get_channel_long_videos(limit)
    if not videos:
        print("No videos fetched or channel is unreachable.")
        return
        
    print(f"Fetched {len(videos)} videos from channel. Processing new uploads...")
    new_synced = 0
    for v in videos:
        res = youtube_sync.sync_youtube_video(v)
        if res and res.get("uploaded_at"):
            new_synced += 1
            time.sleep(2)
            
    print(f"\nAuto-sync complete. Newly uploaded to Archive.org: {new_synced} items.")

if __name__ == "__main__":
    auto_sync_youtube()
