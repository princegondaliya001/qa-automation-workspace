#!/bin/bash
source /root/.openclaw/workspace/scripts/access-control.sh || exit 1
# Daily All-Projects Maestro Test Runner
# Runs every day at 8 PM IST (14:30 UTC)
# Tests all production products with Maestro CLI — BOTH Desktop AND Mobile

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="/root/.openclaw/workspace"
REPO_BASE="$WORKSPACE_DIR/repos"
MAESTRO_REPO="$REPO_BASE/maestro-studio"
STATE_DIR="$WORKSPACE_DIR/state"
LOGS_DIR="$WORKSPACE_DIR/logs"
DISCORD_CHANNEL="1498991059227774986"

# Create timestamp for this run
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RUN_DIR="$STATE_DIR/maestro-daily-tests/$TIMESTAMP"
mkdir -p "$RUN_DIR"
mkdir -p "$LOGS_DIR"
LOG_FILE="$LOGS_DIR/daily-maestro-tests-${TIMESTAMP}.log"

# Cron-safe: use full path to maestro binary
MAESTRO_BIN="/root/.maestro/bin/maestro"
export PATH="/root/.maestro/bin:$PATH"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Daily Maestro Tests Started at $(date -Iseconds) ==="
echo "Testing all production products — DESKTOP + MOBILE"

# Product registry: folder_name:url
PRODUCTS=(
    "chromastudio:https://www.chromastudio.ai"
    "maxstudio:https://www.maxstudio.ai"
    "remixai:https://remixai.io"
    "faceswapper:https://faceswapper.ai"
    "deepswapper:https://www.deepswapper.com"
    "ampere:https://ampere.sh"
)

DESKTOP_PASS=0
DESKTOP_FAIL=0
MOBILE_PASS=0
MOBILE_FAIL=0
TOTAL_PRODUCTS=0

# Test a product for both desktop and mobile
run_tests() {
    local FOLDER=$1
    local URL=$2
    local PRODUCT_NAME=$3
    
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  $PRODUCT_NAME"
    echo "╚══════════════════════════════════════════════════════════════╝"
    
    # --- DESKTOP TEST ---
    echo ""
    echo "  [DESKTOP] $PRODUCT_NAME"
    if [ -d "$MAESTRO_REPO/$FOLDER/flows/masters" ]; then
        DESKTOP_SMOKE=$(find "$MAESTRO_REPO/$FOLDER/flows/masters" -name "*master-auth*" -o -name "*master-home*" -o -name "*master-smoke*" | grep -v "ios\|mobile" | head -1)
        
        if [ -n "$DESKTOP_SMOKE" ]; then
            echo "    Running: $(basename "$DESKTOP_SMOKE")"
            if "$MAESTRO_BIN" test "$DESKTOP_SMOKE" --env baseUrl="$URL" 2>&1 | tee "$RUN_DIR/$FOLDER-desktop.log"; then
                echo "    ✅ DESKTOP PASS"
                DESKTOP_PASS=$((DESKTOP_PASS + 1))
            else
                echo "    ❌ DESKTOP FAIL"
                DESKTOP_FAIL=$((DESKTOP_FAIL + 1))
            fi
        else
            echo "    ⚠️ No desktop master test found"
        fi
    else
        echo "    ⚠️ No desktop flows folder"
    fi
    
    # --- MOBILE TEST ---
    echo ""
    echo "  [MOBILE] $PRODUCT_NAME"
    
    # Check for mobile-specific folder
    if [ -d "$MAESTRO_REPO/$FOLDER/mobile/flows/masters" ]; then
        MOBILE_SMOKE=$(find "$MAESTRO_REPO/$FOLDER/mobile/flows/masters" -name "*master*" | head -1)
        if [ -n "$MOBILE_SMOKE" ]; then
            echo "    Running: $(basename "$MOBILE_SMOKE")"
            if "$MAESTRO_BIN" test "$MOBILE_SMOKE" --env baseUrl="$URL" 2>&1 | tee "$RUN_DIR/$FOLDER-mobile.log"; then
                echo "    ✅ MOBILE PASS"
                MOBILE_PASS=$((MOBILE_PASS + 1))
            else
                echo "    ❌ MOBILE FAIL"
                MOBILE_FAIL=$((MOBILE_FAIL + 1))
            fi
        else
            echo "    ⚠️ No mobile master test found"
        fi
    elif [ -d "$MAESTRO_REPO/$FOLDER/mobile/flows/scenarios" ]; then
        # Try scenario-based mobile test
        MOBILE_SMOKE=$(find "$MAESTRO_REPO/$FOLDER/mobile/flows/scenarios" -name "*smoke*" -o -name "*waydroid*" | head -1)
        if [ -n "$MOBILE_SMOKE" ]; then
            echo "    Running: $(basename "$MOBILE_SMOKE")"
            if "$MAESTRO_BIN" test "$MOBILE_SMOKE" --env baseUrl="$URL" 2>&1 | tee "$RUN_DIR/$FOLDER-mobile.log"; then
                echo "    ✅ MOBILE PASS"
                MOBILE_PASS=$((MOBILE_PASS + 1))
            else
                echo "    ❌ MOBILE FAIL"
                MOBILE_FAIL=$((MOBILE_FAIL + 1))
            fi
        else
            echo "    ⚠️ No mobile scenario test found"
        fi
    elif [ -f "$MAESTRO_REPO/$FOLDER/tests/*mobile*smoke.yaml" ]; then
        # Fallback to tests/ folder mobile smoke
        MOBILE_SMOKE=$(ls "$MAESTRO_REPO/$FOLDER/tests/"*mobile*smoke.yaml 2>/dev/null | head -1)
        if [ -n "$MOBILE_SMOKE" ]; then
            echo "    Running: $(basename "$MOBILE_SMOKE")"
            if "$MAESTRO_BIN" test "$MOBILE_SMOKE" --env baseUrl="$URL" 2>&1 | tee "$RUN_DIR/$FOLDER-mobile.log"; then
                echo "    ✅ MOBILE PASS"
                MOBILE_PASS=$((MOBILE_PASS + 1))
            else
                echo "    ❌ MOBILE FAIL"
                MOBILE_FAIL=$((MOBILE_FAIL + 1))
            fi
        else
            echo "    ⚠️ No mobile smoke test found"
        fi
    else
        echo "    ⚠️ No mobile flows folder"
    fi
    
    TOTAL_PRODUCTS=$((TOTAL_PRODUCTS + 1))
}

# Run tests for all products
for product in "${PRODUCTS[@]}"; do
    IFS=':' read -r FOLDER URL <<< "$product"
    run_tests "$FOLDER" "$URL" "$FOLDER"
done

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  DAILY TEST RESULTS"
echo "════════════════════════════════════════════════════════════════"
echo "  Products tested: $TOTAL_PRODUCTS"
echo "  Desktop: $DESKTOP_PASS passed, $DESKTOP_FAIL failed"
echo "  Mobile:  $MOBILE_PASS passed, $MOBILE_FAIL failed"
echo "  Total:   $((DESKTOP_PASS + MOBILE_PASS)) passed, $((DESKTOP_FAIL + MOBILE_FAIL)) failed"
echo "  Run dir: $RUN_DIR"
echo "════════════════════════════════════════════════════════════════"

# Send Discord summary — dual webhook format
# Webhook 1: Full technical details | Webhook 2: Clean summary only
python3 "$WORKSPACE_DIR/scripts/discord-summary.py" \
    daily \
    "$(date +%Y-%m-%d)" \
    "$DESKTOP_PASS" \
    "$DESKTOP_FAIL" \
    "$MOBILE_PASS" \
    "$MOBILE_FAIL" \
    "$TOTAL_PRODUCTS" \
    "$RUN_DIR" \
    "$RUN_DIR" \
    || echo "⚠️ Discord summary failed"

# If failures, trigger Captain Hook alert
TOTAL_FAIL=$((DESKTOP_FAIL + MOBILE_FAIL))
if [ $TOTAL_FAIL -gt 0 ]; then
    echo ""
    echo "🚨 $TOTAL_FAIL failures detected. Captain Hook will alert."
fi

echo "=== Done at $(date -Iseconds) ==="
