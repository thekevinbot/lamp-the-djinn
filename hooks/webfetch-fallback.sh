#!/bin/bash
# Hook: Fallback to Playwright when WebFetch fails
# Runs after WebFetch attempts, retries with Playwright on failure

# Read the tool use input/output from stdin
INPUT=$(cat)

# Extract the tool result to check for errors
TOOL_RESULT=$(echo "$INPUT" | jq -r '.tool_result // ""')
URL=$(echo "$INPUT" | jq -r '.tool_input.url // ""')

# Check if WebFetch failed (look for common error patterns)
if echo "$TOOL_RESULT" | grep -qi "unable to fetch\|error\|failed\|blocked\|403\|401"; then
    # WebFetch failed - try Playwright

    PROMPT=$(echo "$INPUT" | jq -r '.tool_input.prompt // "Extract all text content from this page"')

    # Try Playwright fetch
    PLAYWRIGHT_RESULT=$(npx -y tsx "$HOME/.claude/clanker/skills/web.ts" \
        "await page.goto('${URL}');
         const text = await page.evaluate(() => document.body.innerText);
         return { title: await page.title(), text: text.slice(0, 10000) };" 2>/dev/null)

    if [ $? -eq 0 ] && [ -n "$PLAYWRIGHT_RESULT" ]; then
        # Playwright succeeded - add as additional context
        cat << EOF
{
  "additionalToolResponseContext": "WebFetch failed, but Playwright successfully retrieved the content:\n\n---\n\nURL: ${URL}\n\nContent:\n${PLAYWRIGHT_RESULT}\n\n---\n\nYou can use this Playwright result to answer the user's question."
}
EOF
        exit 0
    fi
fi

# No error or Playwright failed - no additional context needed
echo "{}"
exit 0
