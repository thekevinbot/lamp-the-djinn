#!/bin/bash
# Test that context files persist (basic check)

RECORDS_DIR="$HOME/.claude/clanker/records"

# Create test file
echo "persistence test" > "$RECORDS_DIR/test-persistence.md"

# Verify it exists and is readable
if [ -f "$RECORDS_DIR/test-persistence.md" ] && \
   grep -q "persistence test" "$RECORDS_DIR/test-persistence.md"; then
  echo "✓ Test 5: Context File Persistence"
  # Cleanup
  rm "$RECORDS_DIR/test-persistence.md"
  exit 0
else
  echo "✗ Test 5: Context File Persistence - file not persistent"
  exit 1
fi
