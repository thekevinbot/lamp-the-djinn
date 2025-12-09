#!/bin/bash
# Test that folder name is correctly detected

# Create test directory
TEST_DIR=$(mktemp -d -t test-folder-XXXXXX)
cd "$TEST_DIR"

FOLDER_NAME=$(basename "$PWD")

if [[ "$FOLDER_NAME" == test-folder-* ]]; then
  echo "✓ Test 7: Folder Name Detection"
  cd /
  rm -rf "$TEST_DIR"
  exit 0
else
  echo "✗ Test 7: Folder Name Detection - incorrect folder name: $FOLDER_NAME"
  exit 1
fi
