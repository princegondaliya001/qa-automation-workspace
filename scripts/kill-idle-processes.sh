#!/bin/bash
# kill-idle-processes.sh — Kill stale Chrome/Waydroid/Weston processes consuming CPU
# Only runs when there are actually idle processes to clean up

set -uo pipefail

# Check if there are any Chrome or Waydroid processes to kill
CHROME_COUNT=$(pgrep -f 'chromium-browser/chrome' 2>/dev/null | wc -l)
WESTON_COUNT=$(pgrep -f 'weston' 2>/dev/null | wc -l)
WAYDROID_COUNT=$(pgrep -f 'waydroid' 2>/dev/null | wc -l)
ZOMBIE_COUNT=$(ps aux | grep -c '<defunct>' 2>/dev/null || echo 0)
MAESTRO_RUNNING=$(pgrep -f "maestro.cli.AppKt" 2>/dev/null | wc -l)

# If nothing to clean up, exit silently
TOTAL_IDLE=$((CHROME_COUNT + WESTON_COUNT + WAYDROID_COUNT + ZOMBIE_COUNT))
if [ "$TOTAL_IDLE" -eq 0 ] && [ "$MAESTRO_RUNNING" -eq 0 ]; then
    exit 0
fi

# If Maestro is running, only kill zombies (not Chrome/Waydroid)
if [ "$MAESTRO_RUNNING" -gt 0 ]; then
    if [ "$ZOMBIE_COUNT" -gt 0 ]; then
        echo "=== CPU Cleanup (Maestro active, only zombies) at $(date -Iseconds) ==="
        ps aux | grep '<defunct>' | grep -v grep | awk '{print $2}' | while read pid; do
            kill -9 $pid 2>/dev/null || true
        done
        echo "=== Zombie Cleanup Complete ==="
    fi
    exit 0
fi

echo "=== CPU Cleanup Started at $(date -Iseconds) ==="
echo "Idle processes found: Chrome=$CHROME_COUNT, Weston=$WESTON_COUNT, Waydroid=$WAYDROID_COUNT, Zombies=$ZOMBIE_COUNT"

# 1. Kill all Chrome processes (Maestro not running)
if [ "$CHROME_COUNT" -gt 0 ]; then
    echo "Killing $CHROME_COUNT Chrome processes..."
    pkill -9 -f 'chromium-browser' 2>/dev/null || true
    pkill -9 -f 'chrome_crashpad_handler' 2>/dev/null || true
fi

# 2. Kill zombie processes
if [ "$ZOMBIE_COUNT" -gt 0 ]; then
    echo "Killing $ZOMBIE_COUNT zombie processes..."
    ps aux | grep '<defunct>' | grep -v grep | awk '{print $2}' | while read pid; do
        kill -9 $pid 2>/dev/null || true
    done
fi

# 3. Kill Weston compositor
if [ "$WESTON_COUNT" -gt 0 ]; then
    echo "Killing Weston..."
    pkill -9 -f 'weston' 2>/dev/null || true
fi

# 4. Stop Waydroid session
if [ "$WAYDROID_COUNT" -gt 0 ]; then
    echo "Stopping Waydroid..."
    waydroid session stop 2>/dev/null || true
fi

# 5. Clean up Chrome temp profiles older than 30 min
TEMP_PROFILES=$(find /tmp -maxdepth 1 -name "org.chromium.Chromium.*" -type d -mmin +30 2>/dev/null | wc -l)
if [ "$TEMP_PROFILES" -gt 0 ]; then
    echo "Cleaning up $TEMP_PROFILES old Chrome temp profiles..."
    find /tmp -maxdepth 1 -name "org.chromium.Chromium.*" -type d -mmin +30 -exec rm -rf {} + 2>/dev/null || true
fi

echo "=== CPU Cleanup Complete at $(date -Iseconds) ==="
echo ""
