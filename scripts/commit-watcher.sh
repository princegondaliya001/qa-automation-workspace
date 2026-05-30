#!/bin/bash
source /root/.openclaw/workspace/scripts/access-control.sh || exit 1
# commit-watcher.sh
# Runs every hour via cron. Checks all frontend repos for new commits.
# Uses Python helper for robust queue/state management.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="/root/.openclaw/workspace/state/commit-watcher.json"
QUEUE_FILE="/root/.openclaw/workspace/state/commit-queue.json"
REPO_BASE="/root/.openclaw/workspace/repos"
DISCORD_CHANNEL="1498991059227774986"

# Step 1: Fetch remote commits for all repos BEFORE checking
# This is critical — Prince pushes from his machine to GitHub,
# so the local clone must fetch to see new commits.
echo "=== Fetching remote commits at $(date -Iseconds) ==="
for repo_dir in "$REPO_BASE"/*/; do
    if [ -d "$repo_dir/.git" ]; then
        repo_name=$(basename "$repo_dir")
        # Skip non-frontend repos (agentmemory, etc.)
        if [ "$repo_name" = "agentmemory" ]; then
            continue
        fi
        current_branch=$(git -C "$repo_dir" branch --show-current 2>/dev/null || echo "main")
        echo "  Fetching $repo_name (branch: $current_branch)..."
        timeout 30 git -C "$repo_dir" fetch origin "$current_branch" 2>/dev/null || echo "    ⚠️ fetch failed for $repo_name"
    fi
done
echo "=== Fetch complete ==="
echo ""

# Step 2: Run the Python watcher (now sees remote commits)
python3 "$SCRIPT_DIR/commit-watcher-update.py" check "$STATE_FILE" "$QUEUE_FILE" "$REPO_BASE" "$DISCORD_CHANNEL"

# Step 3: If new commits detected, ensure repos are pulled to latest
if [ -f "$QUEUE_FILE" ]; then
    PENDING=$(python3 "$SCRIPT_DIR/queue-auto-process.py" check | grep -c '"has_pending": true' || true)
    if [ "$PENDING" -gt 0 ]; then
        echo "=== Pulling latest for repos with pending commits ==="
        for repo_dir in "$REPO_BASE"/*/; do
            if [ -d "$repo_dir/.git" ]; then
                repo_name=$(basename "$repo_dir")
                current_branch=$(git -C "$repo_dir" branch --show-current 2>/dev/null || echo "main")
                echo "  Pulling $repo_name ($current_branch)..."
                timeout 30 git -C "$repo_dir" pull origin "$current_branch" 2>/dev/null || echo "    ⚠️ pull failed for $repo_name"
            fi
        done
        echo "=== Pull complete ==="
    fi
fi

# Step 3: Auto-process simple changes (header labels, simple selectors)
# This runs immediately after queue creation for fast, no-agent processing
echo ""
echo "=== Auto-processing simple changes ==="
python3 "$SCRIPT_DIR/auto-process-simple-changes.py" || echo "  Some entries require agent processing"

echo ""
echo "=== Done at $(date -Iseconds) ==="
