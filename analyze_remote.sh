#!/bin/bash
# Run audio analysis on remote Debian server (bifrost) via SSH
#
# Usage (from WSL bash):
#   ./analyze_remote.sh                    # Analyze all tracks in downloads/
#   ./analyze_remote.sh "Jeremy Soule"     # Analyze specific artist
#
# Prerequisites:
#   - SSH access to bifrost configured
#   - essentia installed on bifrost: pip install essentia
#   - This script copied to bifrost or run via SSH

set -e

REMOTE_HOST="bifrost"
LOCAL_PROJECT="/mnt/c/Users/wyrmwood/github/dropbox-playlists"
REMOTE_PROJECT="~/dropbox-playlists"
ARTIST="${1:-}"

echo "=== Remote Audio Analysis ==="
echo "Host: $REMOTE_HOST"
echo "Artist: ${ARTIST:-all}"
echo ""

# Step 1: Sync project files to remote
echo "Syncing project to $REMOTE_HOST..."
rsync -avz --exclude='.venv' --exclude='__pycache__' --exclude='.git' \
    "$LOCAL_PROJECT/" "$REMOTE_HOST:$REMOTE_PROJECT/"

# Step 2: Sync downloads (if they exist)
if [ -d "$LOCAL_PROJECT/downloads" ]; then
    echo "Syncing downloads..."
    rsync -avz "$LOCAL_PROJECT/downloads/" "$REMOTE_HOST:$REMOTE_PROJECT/downloads/"
fi

# Step 3: Run analysis on remote
echo "Running analysis on $REMOTE_HOST..."
if [ -n "$ARTIST" ]; then
    ssh "$REMOTE_HOST" "cd $REMOTE_PROJECT && python3 analyze_essentia.py --batch --simple --json 'downloads/$ARTIST'" > "$LOCAL_PROJECT/analysis_results.json"
else
    ssh "$REMOTE_HOST" "cd $REMOTE_PROJECT && python3 analyze_essentia.py --batch --simple --json downloads" > "$LOCAL_PROJECT/analysis_results.json"
fi

echo ""
echo "Results saved to: $LOCAL_PROJECT/analysis_results.json"
echo "Done!"
