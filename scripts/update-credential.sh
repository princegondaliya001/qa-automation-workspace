#!/bin/bash
# Update credentials safely
# Usage: ./update-credential.sh <name> <value>
# Example: ./update-credential.sh discord-webhook "https://new-url"

set -euo pipefail

CRED_DIR="/root/.openclaw/credentials"
NAME=$1
VALUE=$2

mkdir -p "$CRED_DIR"

# Update the credential
echo "$NAME=$VALUE" > "$CRED_DIR/.$NAME"
chmod 600 "$CRED_DIR/.$NAME"

echo "✅ Credential '$NAME' updated"
echo "📁 Stored at: $CRED_DIR/.$NAME"
