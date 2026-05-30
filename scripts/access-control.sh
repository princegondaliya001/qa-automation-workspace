#!/bin/bash
# User Access Control for Testing Automation
# Only authorized users can run critical scripts

set -euo pipefail

AUTH_FILE="/root/.openclaw/workspace/.authorized-users"
CURRENT_USER=$(whoami)

# If auth file doesn't exist, create default with safe users
if [ ! -f "$AUTH_FILE" ]; then
    cat > "$AUTH_FILE" << 'EOF'
# Authorized users for testing automation
# Only these users can run critical scripts
prince
root
qa-tester
EOF
    chmod 600 "$AUTH_FILE"
fi

# Read allowed users (skip comments and blank lines)
ALLOWED_USERS=$(grep -v '^#' "$AUTH_FILE" | grep -v '^$' | tr '\n' ',')

if [[ ! ",${ALLOWED_USERS}," =~ ",${CURRENT_USER}," ]]; then
    echo "❌ ERROR: User '$CURRENT_USER' is NOT authorized to run this script"
    echo "Authorized users: ${ALLOWED_USERS%,}"
    echo ""
    echo "To add a user: echo 'username' >> $AUTH_FILE"
    exit 1
fi

echo "✅ User '$CURRENT_USER' authorized"
