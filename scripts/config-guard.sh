#!/bin/bash
source /root/.openclaw/workspace/scripts/access-control.sh || exit 1
# Pre-commit guard: prevents staging URLs from being committed to maestro-studio
# Usage: ./scripts/config-guard.sh
# Exit 1 if any product suite config.yaml contains a staging URL, 0 otherwise

set -euo pipefail

STUDIO_ROOT="${MAESTRO_STUDIO_ROOT:-/root/.openclaw/workspace/repos/maestro-studio}"

# Production URLs that are allowed
PRODUCTION_PATTERNS="www.chromastudio.ai|www.maxstudio.ai|remixai.io|faceswapper.ai|deepswapper.com|ampere.sh|localhost"

# Staging URLs that must NOT be committed
STAGING_PATTERNS="style-transfer-git-dev|max-v2-git-dev|remixai-git-dev|faceswapper-ai-git-dev|deepswapper-ai-git-dev|ampere-sh-.*-git-dev|vercel\\.app"

check_file() {
    local file="$1"
    local matches
    # Lines containing baseUrl or url:
    matches="$(grep -Eh "baseUrl|url:" "$file" 2>/dev/null || true)"
    if [[ -z "$matches" ]]; then
        return 0
    fi
    # Filter out production URLs and localhost
    local suspicious
    suspicious="$(echo "$matches" | grep -Ev "$PRODUCTION_PATTERNS" || true)"
    # From the remaining, check if any match staging patterns
    local leaked
    leaked="$(echo "$suspicious" | grep -E "$STAGING_PATTERNS" || true)"
    if [[ -n "$leaked" ]]; then
        echo "ERROR: Staging URL detected in $file"
        echo "$leaked"
        return 1
    fi
    return 0
}

found=0

# Check all config.yaml files under maestro-studio
while IFS= read -r -d '' file; do
    if ! check_file "$file"; then
        found=1
    fi
done < <(find "$STUDIO_ROOT" -type f -name "config.yaml" -print0)

if [[ "$found" -eq 1 ]]; then
    echo ""
    echo "ABORT: Staging URL(s) detected in config.yaml files."
    echo "Run 'git checkout -- <path>/config/config.yaml' to revert, or investigate why a staging URL is present."
    exit 1
fi

echo "PASS: No staging URLs in any config.yaml"
exit 0
