#!/bin/bash
# Verify global CLAUDE.md exists and has auto-save instructions

if [ -f ~/.claude/CLAUDE.md ] && grep -q "Auto-Save Context" ~/.claude/CLAUDE.md; then
  echo "✓ Test 2: Global CLAUDE.md with auto-save instructions"
  exit 0
else
  echo "✗ Test 2: Global CLAUDE.md missing or incomplete"
  exit 1
fi
