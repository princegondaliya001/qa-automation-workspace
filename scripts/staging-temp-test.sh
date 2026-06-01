#!/bin/bash
source /root/.openclaw/workspace/scripts/access-control.sh || exit 1
# Usage: ./scripts/staging-temp-test.sh <maestro_folder> <testUrl> <flow_path>
# Runs a Maestro flow against staging WITHOUT touching config.yaml
# Example: ./scripts/staging-temp-test.sh chromastudio https://style-transfer-git-dev-nextbasecores-projects.vercel.app chromastudio/tests/temp-test.yaml

set -euo pipefail

FOLDER="${1:-}"
TESTURL="${2:-}"
FLOW="${3:-}"

if [[ -z "$FOLDER" || -z "$TESTURL" || -z "$FLOW" ]]; then
    echo "Usage: $0 <maestro_folder> <testUrl> <flow_path>"
    echo "Example: $0 chromastudio https://style-transfer-git-dev-nextbasecores-projects.vercel.app chromastudio/tests/temp-test.yaml"
    exit 2
fi

STUDIO_ROOT="${MAESTRO_STUDIO_ROOT:-/root/.openclaw/workspace/repos/maestro-studio}"
FLOW_PATH="$STUDIO_ROOT/$FLOW"

if [[ ! -f "$FLOW_PATH" ]]; then
    echo "ERROR: Flow file not found: $FLOW_PATH"
    exit 2
fi

echo "Running Maestro flow against staging URL (config.yaml untouched):"
echo "  Folder:  $FOLDER"
echo "  TestUrl: $TESTURL"
echo "  Flow:    $FLOW_PATH"
echo ""

export PATH="/root/.maestro/bin:$PATH"

maestro test "$FLOW_PATH" --env baseUrl="$TESTURL"
