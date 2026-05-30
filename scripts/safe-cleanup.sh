#!/bin/bash
source /root/.openclaw/workspace/scripts/access-control.sh || exit 1
# safe-cleanup.sh - Clean old temp files, screenshots, logs
# Run daily via cron. Keeps recent files (7 days), removes old ones.

set -euo pipefail

STATE_DIR="/root/.openclaw/workspace/state"
LOGS_DIR="/root/.openclaw/workspace/logs"
REPOS_DIR="/root/.openclaw/workspace/repos"

# Log file for this cleanup run
CLEANUP_LOG="$STATE_DIR/cleanup-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$CLEANUP_LOG") 2>&1

echo "=== Cleanup started at $(date -Iseconds) ==="

# 1. Clean old screenshots (>7 days)
find "$STATE_DIR" -name "*.png" -type f -mtime +7 -print -delete 2>/dev/null || true

# 2. Clean old temp test directories (>3 days)
find "$STATE_DIR" -type d -name "temp-*" -mtime +3 -print -exec rm -rf {} + 2>/dev/null || true
find "$STATE_DIR" -type d -name "*test*" -mtime +3 -print -exec rm -rf {} + 2>/dev/null || true

# 3. Clean old log files (>7 days)
find "$LOGS_DIR" -name "*.log" -type f -mtime +7 -print -delete 2>/dev/null || true
find "$STATE_DIR" -name "*.log" -type f -mtime +7 -print -delete 2>/dev/null || true

# 4. Clean safe-cleanup-trash (delete trash >7 days + oversized files >100MB immediately)
if [ -d "$STATE_DIR/safe-cleanup-trash" ]; then
    # Delete old trash (>7 days)
    find "$STATE_DIR/safe-cleanup-trash" -type d -mtime +7 -print -exec rm -rf {} + 2>/dev/null || true
    find "$STATE_DIR/safe-cleanup-trash" -type f -mtime +7 -print -delete 2>/dev/null || true
    # Delete oversized files in trash immediately (>100MB — already in trash, safe)
    find "$STATE_DIR/safe-cleanup-trash" -type f -size +100M -print -delete 2>/dev/null || true
fi

# 5. Clean maestro-daily-tests old runs (>7 days)
if [ -d "$STATE_DIR/maestro-daily-tests" ]; then
    find "$STATE_DIR/maestro-daily-tests" -type d -mtime +7 -print -exec rm -rf {} + 2>/dev/null || true
fi

# 6. Clean maestro-generation-rotation old runs (>7 days)
if [ -d "$STATE_DIR/maestro-generation-rotation" ]; then
    find "$STATE_DIR/maestro-generation-rotation" -type d -mtime +7 -print -exec rm -rf {} + 2>/dev/null || true
fi

# 7. Clean chromium profile backups (keep last 5)
if [ -d "$STATE_DIR/chromium-profile-backups" ]; then
    ls -t "$STATE_DIR/chromium-profile-backups" | tail -n +6 | while read f; do
        rm -rf "$STATE_DIR/chromium-profile-backups/$f"
    done
fi

# 8. Clean old queue/trigger files
find "$STATE_DIR" -name "commit-watcher-trigger" -mtime +1 -delete 2>/dev/null || true

# 10. Clean empty directories (recursively, excluding .git)
find "$STATE_DIR" -type d -empty ! -path "*/.git/*" -print -delete 2>/dev/null || true
find "$LOGS_DIR" -type d -empty ! -path "*/.git/*" -print -delete 2>/dev/null || true

# 11. Report disk usage after cleanup
echo ""
echo "=== Disk usage after cleanup ==="
du -sh "$STATE_DIR" 2>/dev/null || true
echo ""
echo "=== Cleanup completed at $(date -Iseconds) ==="
