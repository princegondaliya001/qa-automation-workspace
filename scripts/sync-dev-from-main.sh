#!/bin/bash
source /root/.openclaw/workspace/scripts/access-control.sh || exit 1
# sync-dev-from-main.sh
# Runs every 2 hours via cron. Checks if dev branch is behind main/master.
# If behind, pulls latest from main/master into dev branch and pushes to origin.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_BASE="/root/.openclaw/workspace/repos"
LOGS_DIR="/root/.openclaw/workspace/logs"
DISCORD_CHANNEL="1498991059227774986"

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="$LOGS_DIR/dev-sync-${TIMESTAMP}.log"
mkdir -p "$LOGS_DIR"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Dev Branch Sync Started at $(date -Iseconds) ==="

# Product registry: repo:local_path:main_branch
REPOS=(
    "chroma-studio-frontend-nextjs:$REPO_BASE/chroma-studio-frontend-nextjs:main"
    "max-v2:$REPO_BASE/max-v2:master"
    "remix-studio-nextjs:$REPO_BASE/remix-studio-nextjs:main"
    "deepswapper-ai-nextjs:$REPO_BASE/deepswapper-ai-nextjs:main"
    "faceswapper-ai:$REPO_BASE/faceswapper-ai:master"
    "ampere-sh:$REPO_BASE/ampere-sh:main"
)

SYNCED=0
SKIPPED=0
FAILED=0

for entry in "${REPOS[@]}"; do
    IFS=':' read -r REPO_NAME REPO_PATH MAIN_BRANCH <<< "$entry"
    
    echo ""
    echo "=== $REPO_NAME ==="
    
    if [ ! -d "$REPO_PATH/.git" ]; then
        echo "  ⚠️ Not a git repo, skipping"
        ((FAILED++)) || true
        continue
    fi
    
    cd "$REPO_PATH"
    
    # Fetch latest from origin
    echo "  Fetching origin..."
    git fetch origin 2>/dev/null || {
        echo "  ❌ Fetch failed, skipping"
        ((FAILED++)) || true
        continue
    }
    
    # Check if we are on dev branch locally
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    if [ "$CURRENT_BRANCH" != "dev" ]; then
        echo "  ⚠️ Not on dev branch (currently: $CURRENT_BRANCH), switching to dev..."
        git checkout dev 2>/dev/null || {
            echo "  ❌ Could not checkout dev branch"
            ((FAILED++)) || true
            continue
        }
    fi
    
    # Ensure dev branch tracks origin/dev
    git branch --set-upstream-to=origin/dev dev 2>/dev/null || true
    
    # Pull latest dev first (in case remote dev has new commits)
    echo "  Pulling latest dev..."
    git pull origin dev 2>/dev/null || echo "  ⚠️ Could not pull dev (might be up to date)"
    
    # Check if dev is behind main/master
    BEHIND=$(git rev-list --count dev..origin/$MAIN_BRANCH 2>/dev/null || echo "0")
    
    if [ "$BEHIND" -eq "0" ]; then
        echo "  ✅ Dev is up-to-date with $MAIN_BRANCH"
        ((SKIPPED++)) || true
        continue
    fi
    
    echo "  🔄 Dev is behind $MAIN_BRANCH by $BEHIND commit(s)"
    
    # Merge main/master into dev (not rebase, to keep history clean)
    echo "  Merging origin/$MAIN_BRANCH into dev..."
    if git merge origin/$MAIN_BRANCH -m "sync: merge $MAIN_BRANCH into dev ($BEHIND commits)" 2>/dev/null; then
        echo "  ✅ Merge successful"
        
        # Push updated dev to origin
        echo "  Pushing dev to origin..."
        if git push origin dev 2>/dev/null; then
            echo "  ✅ Pushed dev to origin"
            ((SYNCED++)) || true
            
            # Send Discord notification about sync
            python3 "$SCRIPT_DIR/discord-summary.py" custom \
                "🔄 **Dev Branch Synced: $REPO_NAME**\n\nMerged $BEHIND commit(s) from $MAIN_BRANCH into dev.\n\nDev branch is now up-to-date with production." \
                --webhook=1 2>/dev/null || echo "  ⚠️ Discord notification failed"
        else
            echo "  ❌ Push failed"
            ((FAILED++)) || true
        fi
    else
        echo "  ❌ Merge failed (conflicts?) — manual intervention needed"
        git merge --abort 2>/dev/null || true
        ((FAILED++)) || true
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  DEV SYNC RESULTS"
echo "════════════════════════════════════════════════════════════"
echo "  Repos synced:   $SYNCED"
echo "  Repos skipped:  $SKIPPED"
echo "  Repos failed:   $FAILED"
echo "  Log file:       $LOG_FILE"
echo "════════════════════════════════════════════════════════════"

# Send summary if any syncs happened
if [ $SYNCED -gt 0 ]; then
    python3 "$SCRIPT_DIR/discord-summary.py" custom \
        "📅 **Dev Sync Summary — $(date +%Y-%m-%d)**\n\nSynced $SYNCED repo(s) from main/master to dev.\nSkipped: $SKIPPED\nFailed: $FAILED\n\n**Log:** $LOG_FILE" \
        --webhook=2 2>/dev/null || echo "⚠️ Discord summary failed"
fi

echo "=== Done at $(date -Iseconds) ==="
