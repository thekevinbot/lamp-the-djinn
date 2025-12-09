#!/bin/bash
# Test context save workflow

RECORDS_DIR="$HOME/.claude/clanker/records"
TEST_DIR=$(mktemp -d)
cd "$TEST_DIR"

FOLDER_NAME=$(basename "$PWD")

# Create test content
echo "Test context content" > /tmp/test-context.md

# Run save script
bash ~/.claude/clanker/save-context.sh /tmp/test-context.md >/dev/null 2>&1

# Check if files were created
if [ -f "$RECORDS_DIR/${FOLDER_NAME}-latest.md" ] && \
   grep -q "Test context content" "$RECORDS_DIR/${FOLDER_NAME}-latest.md"; then
  echo "✓ Test 4: Save Context Workflow"
  # Cleanup
  rm "$RECORDS_DIR/${FOLDER_NAME}"*.md
  rm /tmp/test-context.md
  cd /
  rm -rf "$TEST_DIR"
  exit 0
else
  echo "✗ Test 4: Save Context Workflow - files not created correctly"
  exit 1
fi
