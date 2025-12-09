#!/bin/bash
# Test host-container sync (run inside container)

RECORDS_DIR="$HOME/.claude/clanker/records"

# Create file
echo "sync test $(date +%s)" > "$RECORDS_DIR/sync-test.md"

# Verify it exists
if [ -f "$RECORDS_DIR/sync-test.md" ]; then
  echo "✓ Test 6: Host-Container Sync (check host to verify)"
  echo "  File created: $RECORDS_DIR/sync-test.md"
  echo "  Verify this file exists on host machine"
  # Note: Don't cleanup - let user verify on host, then manually delete
  exit 0
else
  echo "✗ Test 6: Host-Container Sync - file not created"
  exit 1
fi
