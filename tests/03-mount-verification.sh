#!/bin/bash
# Verify ~/.claude is mounted and writable

if [ -w ~/.claude/clanker/records/ ]; then
  echo "✓ Test 3: Mount Verification - records/ is writable"
  exit 0
else
  echo "✗ Test 3: Mount Verification - records/ not writable"
  exit 1
fi
