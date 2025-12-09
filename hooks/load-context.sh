#!/bin/bash
# Hook script: Load global instructions and previous context
# Called by UserPromptSubmit hook

FOLDER_NAME=$(basename "$PWD")
CONTEXT_FILE="$HOME/.claude/clanker/records/${FOLDER_NAME}/latest.md"
GLOBAL_INSTRUCTIONS="$HOME/.claude/CLAUDE.md"

# Build output to inject into conversation
OUTPUT=""

# 1. Always load global instructions
if [ -f "$GLOBAL_INSTRUCTIONS" ]; then
    OUTPUT+="<global-instructions>
$(cat "$GLOBAL_INSTRUCTIONS")
</global-instructions>

"
fi

# 2. Check for and load existing context
if [ -f "$CONTEXT_FILE" ]; then
    OUTPUT+="<previous-context>
Previous conversation found for folder: $FOLDER_NAME

$(cat "$CONTEXT_FILE")
</previous-context>

---

📝 **Previous session loaded.** Please:
1. Briefly acknowledge we're continuing from a previous session
2. Summarize the key things we were working on
3. Ask if I want to continue that work or start something new

"
fi

# Output content (will be prepended to user's message)
if [ -n "$OUTPUT" ]; then
    echo "$OUTPUT"
fi

exit 0
