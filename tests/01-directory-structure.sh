#!/bin/bash
# Verify ~/.claude/clanker/records/ exists

if [ -d ~/.claude/clanker/records/ ]; then
  echo "✓ Test 1: Directory Structure"
  exit 0
else
  echo "✗ Test 1: Directory Structure - records/ not found"
  exit 1
fi
