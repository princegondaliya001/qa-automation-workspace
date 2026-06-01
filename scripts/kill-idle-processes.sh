#!/bin/bash
# kill-idle-processes.sh — Kill stale Chrome/Waydroid/Weston processes consuming CPU

set -uo pipefail

echo "=== CPU Cleanup Started at $(date -Iseconds) ==="

# 1. Kill Chrome renderer processes that are NOT actively used by Maestro
#    (if Maestro is running, keep Chrome alive; otherwise kill all)
MAESTRO_RUNNING=$(pgrep -f "maestro.cli.AppKt" 2>/dev/null | wc -l)
CHROME_COUNT=$(pgrep -f 'chromium-browser/chrome' 2>/dev/null | wc -l)

if [ "$CHROME_COUNT" -gt 0 ]; then
    if [ "$MAESTRO_RUNNING" -eq 0 ]; then
        echo "Maestro not running. Killing all Chrome processes..."
        pkill -9 -f 'chromium-browser' 2>/dev/null || true
        pkill -9 -f 'chrome_crashpad_handler' 2>/dev/null || true
    else
        echo "Maestro is running ($MAESTRO_RUNNING instances). Keeping Chrome alive."
    fi
fi

# 2. Kill Chrome zombie processes (defunct)
ZOMBIE_COUNT=$(ps aux | grep -c '<defunct>' 2>/dev/null || echo 0)
if [ "$ZOMBIE_COUNT" -gt 0 ]; then
    echo "Killing $ZOMBIE_COUNT zombie processes..."
    ps aux | grep '<defunct>' | grep -v grep | awk '{print $2}' | while read pid; do
        kill -9 $pid 2>/dev/null || true
    done
fi

# 3. Kill Weston compositor if no Maestro running
WESTON_RUNNING=$(pgrep -f 'weston' 2>/dev/null | wc -l)
if [ "$WESTON_RUNNING" -gt 0 ] && [ "$MAESTRO_RUNNING" -eq 0 ]; then
    echo "Killing Weston (no Maestro tests)..."
    pkill -9 -f 'weston' 2>/dev/null || true
fi

# 4. Stop Waydroid session if idle (no Maestro)
WAYDROID_RUNNING=$(pgrep -f 'waydroid' 2>/dev/null | wc -l)
if [ "$WAYDROID_RUNNING" -gt 0 ] && [ "$MAESTRO_RUNNING" -eq 0 ]; then
    echo "Stopping Waydroid session..."
    waydroid session stop 2>/dev/null || true
fi

# 5. Clean up Chrome temp profiles older than 30 min
TEMP_PROFILES=$(find /tmp -maxdepth 1 -name "org.chromium.Chromium.*" -type d -mmin +30 2>/dev/null | wc -l)
if [ "$TEMP_PROFILES" -gt 0 ]; then
    echo "Cleaning up $TEMP_PROFILES old Chrome temp profiles..."
    find /tmp -maxdepth 1 -name "org.chromium.Chromium.*" -type d -mmin +30 -exec rm -rf {} + 2>/dev/null || true
fi

# 6. Kill Chrome crashpad handlers
CRASHPAD_COUNT=$(pgrep -f 'chrome_crashpad_handler' 2>/dev/null | wc -l)
if [ "$CRASHPAD_COUNT" -gt 0 ]; then
    echo "Killing $CRASHPAD_COUNT crashpad handlers..."
    pkill -9 -f 'chrome_crashpad_handler' 2>/dev/null || true
fi

echo "=== CPU Cleanup Complete at $(date -Iseconds) ==="
echo ""
