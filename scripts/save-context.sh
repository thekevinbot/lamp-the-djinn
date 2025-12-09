#!/bin/bash
# Usage: save-context.sh <content-file>
# Saves content to records with proper naming

FOLDER_NAME=$(basename "$PWD")
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
RECORDS_DIR="$HOME/.claude/clanker/records/$FOLDER_NAME"

mkdir -p "$RECORDS_DIR"

# Save as latest
cp "$1" "$RECORDS_DIR/latest.md"

# Save timestamped backup
cp "$1" "$RECORDS_DIR/${TIMESTAMP}.md"

echo "Context saved to:"
echo "  - $RECORDS_DIR/latest.md"
echo "  - $RECORDS_DIR/${TIMESTAMP}.md"
