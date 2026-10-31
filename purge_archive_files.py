import os
import sys
import json
import internetarchive as ia

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Enforce direct connection for all Archive.org traffic
os.environ["NO_PROXY"] = "archive.org,*.archive.org,s3.us.archive.org,ia601904.us.archive.org,127.0.0.1,localhost,api.ipify.org"
os.environ["no_proxy"] = "archive.org,*.archive.org,s3.us.archive.org,ia601904.us.archive.org,127.0.0.1,localhost,api.ipify.org"

IDENTIFIER = "qurani-yasser-aldosari-prayers"

NON_QURAN_IDS = {
    'Cq3lwri7118', 'Mj6mRgAplbY', 'CsE1KpMXPjU', 'UuM1ph5thgQ',
    'HbpmP8Rgkrs', 'dgvsyr_ed5k', 'u0b312zRzDk', '5jqyRZaml7o', 'hu9CBlHuhjs'
}

def purge_from_archive():
    print("=" * 75)
    print("🧹 PURGING NON-QURAN LESSONS AND SPEECHES FROM ARCHIVE.ORG")
    print(f"Target Identifier: {IDENTIFIER}")
    print("=" * 75)

    item = ia.get_item(IDENTIFIER)
    all_files = list(item.get_files())
    
    files_to_delete = []
    for f in all_files:
        for vid in NON_QURAN_IDS:
            if vid in f.name:
                files_to_delete.append(f.name)
                
    files_to_delete = sorted(list(set(files_to_delete)))
    print(f"Found {len(files_to_delete)} files on Archive.org to delete:")
    for fn in files_to_delete:
        print(f" - {fn}")
        
    if not files_to_delete:
        print("✅ No target files found on Archive.org. Already clean!")
        return True

    print(f"\nProceeding to delete {len(files_to_delete)} files with cascade_delete=True...")
    try:
        resp = ia.delete(
            IDENTIFIER,
            files=files_to_delete,
            cascade_delete=True,
            verbose=True
        )
        print("✅ Files successfully deleted from Archive.org!")
        return True
    except Exception as e:
        print(f"❌ Error deleting files from Archive.org: {e}")
        return False

if __name__ == "__main__":
    purge_from_archive()
