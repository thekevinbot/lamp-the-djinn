#!/bin/bash
set -euo pipefail

# Domain approval wrapper for browser automation
# Prompts user for approval, persists to file, and updates firewall
#
# Usage: approve-domain.sh <domain> [--check-only]
#
# Exit codes:
#   0 - domain is approved (or was just approved)
#   1 - domain was denied or error occurred
#   2 - invalid usage

ALLOWED_DOMAINS_FILE="${ALLOWED_DOMAINS_FILE:-$HOME/.claude/.allowed-browser-domains}"

usage() {
    echo "Usage: $0 <domain> [--check-only]" >&2
    echo "" >&2
    echo "Options:" >&2
    echo "  --check-only  Only check if domain is approved, don't prompt" >&2
    exit 2
}

if [ $# -lt 1 ]; then
    usage
fi

DOMAIN="$1"
CHECK_ONLY=false

if [ "${2:-}" = "--check-only" ]; then
    CHECK_ONLY=true
fi

# Validate domain format
if [[ ! "$DOMAIN" =~ ^[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?$ ]]; then
    echo "ERROR: Invalid domain format: $DOMAIN" >&2
    exit 1
fi

# Ensure the allowed domains file exists
mkdir -p "$(dirname "$ALLOWED_DOMAINS_FILE")"
touch "$ALLOWED_DOMAINS_FILE"

# Check if domain is already approved
if grep -qxF "$DOMAIN" "$ALLOWED_DOMAINS_FILE" 2>/dev/null; then
    # Already approved - ensure it's in the firewall (IPs may have changed)
    if command -v sudo &>/dev/null && [ -x /usr/local/bin/add-domain-to-firewall.sh ]; then
        sudo /usr/local/bin/add-domain-to-firewall.sh "$DOMAIN" >/dev/null 2>&1 || true
    fi
    exit 0
fi

# If check-only mode, domain is not approved
if [ "$CHECK_ONLY" = true ]; then
    exit 1
fi

# Prompt user for approval
echo "" >&2
echo "═══════════════════════════════════════════════════════" >&2
echo "  Browser wants to access: $DOMAIN" >&2
echo "═══════════════════════════════════════════════════════" >&2
echo "" >&2
read -p "Allow access to $DOMAIN? [y/N] " -n 1 -r REPLY </dev/tty >&2
echo "" >&2

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Denied access to $DOMAIN" >&2
    exit 1
fi

# Add to allowed domains file
echo "$DOMAIN" >> "$ALLOWED_DOMAINS_FILE"
echo "Added $DOMAIN to allowed domains" >&2

# Add to firewall
if command -v sudo &>/dev/null && [ -x /usr/local/bin/add-domain-to-firewall.sh ]; then
    if sudo /usr/local/bin/add-domain-to-firewall.sh "$DOMAIN" >&2; then
        echo "Firewall updated for $DOMAIN" >&2
    else
        echo "Warning: Failed to update firewall for $DOMAIN" >&2
    fi
fi

exit 0
