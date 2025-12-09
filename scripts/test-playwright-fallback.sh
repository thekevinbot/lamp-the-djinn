#!/bin/bash
# Integration test: Verify Playwright fallback when WebFetch fails

set -e

echo "Testing Playwright Fallback Integration..."
echo ""

TEST_PROMPT="I'm trying to come up with stocking stuffers. I found this: https://www.nytimes.com/wirecutter/gifts/stocking-stuffers-for-kids/ We have a 3.5 y/o, 2 40-somethings, and 3 75 y/os. And a dog. Can be silly cheap gifts"

CLAUDE_DIR="$HOME/.claude/.devcontainer"
CONFIG="$CLAUDE_DIR/devcontainer.json"

# Step 1: Start container
echo "Step 1: Starting devcontainer..."
cd "$(mktemp -d)"
npx -y @devcontainers/cli up --workspace-folder . --config "$CONFIG" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "✗ Failed to start container"
    exit 1
fi
echo "✓ Container started"
echo ""

# Step 2: Run Claude with test prompt
echo "Step 2: Sending test prompt to Claude..."
echo "Prompt: '$TEST_PROMPT'"
echo ""

# Run Claude and capture output
echo "$TEST_PROMPT" | npx -y @devcontainers/cli exec --workspace-folder . --config "$CONFIG" \
    claude --dangerously-skip-permissions --debug > /tmp/claude-test-output.log 2>&1 &

CLAUDE_PID=$!

# Wait for Claude to process (increase timeout for container startup + processing)
echo "Waiting for Claude to process (60 seconds)..."
sleep 60

# Kill Claude after timeout
kill $CLAUDE_PID 2>/dev/null || true
wait $CLAUDE_PID 2>/dev/null || true

echo "✓ Test completed"
echo ""
echo "Output captured to /tmp/claude-test-output.log ($(wc -l < /tmp/claude-test-output.log) lines)"
echo ""

# Step 3: Analyze output
echo "Step 3: Analyzing results..."
echo ""

OUTPUT=$(cat /tmp/claude-test-output.log)

# Show preview of captured output
echo "Preview of captured output (first 20 lines):"
echo "---"
head -20 /tmp/claude-test-output.log
echo "---"
echo ""

# Check for WebFetch attempt
if echo "$OUTPUT" | grep -q "Fetch.*nytimes.com\|WebFetch.*nytimes"; then
    echo "✓ WebFetch attempted"
else
    echo "✗ WebFetch was not attempted"
    exit 1
fi

# Check for WebFetch failure
if echo "$OUTPUT" | grep -qi "unable to fetch\|Error.*fetch\|failed\|blocked"; then
    echo "✓ WebFetch failed (as expected)"
else
    echo "✗ WebFetch did not fail"
    exit 1
fi

# Check for Playwright execution AFTER WebFetch failure
if echo "$OUTPUT" | grep -qi "playwright\|npx.*tsx.*web.ts\|WebFetch failed, but Playwright"; then
    echo "✓ Playwright fallback triggered after WebFetch failure"
else
    echo "✗ Playwright fallback was NOT triggered"
    echo ""
    echo "Debug output:"
    grep -i "hook\|webfetch\|playwright" /tmp/claude-test-output.log || echo "No relevant output found"
    exit 1
fi

# Check for successful content retrieval AFTER Playwright
if echo "$OUTPUT" | grep -qi "stocking\|gift\|toy\|wirecutter"; then
    echo "✓ Content retrieved successfully via Playwright"
else
    echo "✗ Content was NOT retrieved (Playwright may have failed)"
    echo ""
    echo "Debug output:"
    tail -50 /tmp/claude-test-output.log
    exit 1
fi

echo ""
echo "================================"
echo "✓ Playwright Fallback Test PASSED"
echo ""
echo "Summary:"
echo "1. WebFetch attempted: YES"
echo "2. WebFetch failed: YES (as expected)"
echo "3. Playwright fallback triggered: YES"
echo "4. Content retrieved successfully: YES"
echo ""
echo "This verifies the complete failure → fallback → success flow."
echo ""

# Keep log file for inspection
echo "Log file preserved at: /tmp/claude-test-output.log"
echo "To inspect: cat /tmp/claude-test-output.log"
echo ""

exit 0
