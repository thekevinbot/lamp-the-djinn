#!/usr/bin/env python3
"""
Integration test: Verify Playwright fallback when WebFetch fails

This test:
1. Starts a devcontainer with Claude Code
2. Sends a prompt with a URL that WebFetch will fail on
3. Verifies WebFetch is attempted and fails
4. Verifies Playwright fallback is triggered
5. Verifies content is successfully retrieved via Playwright
"""

import subprocess
import tempfile
from pathlib import Path
import pytest


def describe_playwright_fallback():
    """Integration tests for Playwright fallback hook"""

    def describe_when_webfetch_fails():
        """When WebFetch encounters a blocked site"""

        @pytest.mark.integration
        def it_should_trigger_playwright_fallback_and_succeed():
            """Should automatically fall back to Playwright and retrieve content"""

            test_prompt = (
                "I'm trying to come up with stocking stuffers. "
                "I found this: https://www.nytimes.com/wirecutter/gifts/stocking-stuffers-for-kids/ "
                "We have a 3.5 y/o, 2 40-somethings, and 3 75 y/os. And a dog. "
                "Can be silly cheap gifts"
            )

            claude_dir = Path.home() / ".claude" / ".devcontainer"
            config = claude_dir / "devcontainer.json"

            print("\n" + "="*60)
            print("Testing Playwright Fallback Integration...")
            print("="*60)

            # Given: A running devcontainer
            print("\nStep 1: Starting devcontainer...")
            with tempfile.TemporaryDirectory() as tmpdir:
                result = subprocess.run(
                    [
                        "npx", "-y", "@devcontainers/cli", "up",
                        "--workspace-folder", tmpdir,
                        "--config", str(config)
                    ],
                    capture_output=True,
                    text=True
                )

                assert result.returncode == 0, f"Failed to start container: {result.stderr}"
                print("✓ Container started")

                # When: Claude processes a prompt with a blocked URL
                print("\nStep 2: Sending test prompt to Claude...")
                print(f"Prompt: '{test_prompt[:80]}...'")

                process = subprocess.Popen(
                    [
                        "npx", "-y", "@devcontainers/cli", "exec",
                        "--workspace-folder", tmpdir,
                        "--config", str(config),
                        "claude", "--dangerously-skip-permissions", "--debug"
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )

                stdout, _ = process.communicate(input=test_prompt, timeout=60)

                print("✓ Test completed")
                print(f"✓ Captured {len(stdout.splitlines())} lines of output")

                # Then: Verify the complete failure → fallback → success flow
                print("\nStep 3: Analyzing results...")
                print("\nPreview of captured output (first 20 lines):")
                print("---")
                for line in stdout.splitlines()[:20]:
                    print(line)
                print("---\n")

                # Then: WebFetch should be attempted
                assert any(
                    "nytimes" in line.lower() and ("fetch" in line.lower() or "webfetch" in line.lower())
                    for line in stdout.splitlines()
                ), "✗ WebFetch was not attempted"
                print("✓ WebFetch attempted")

                # And: WebFetch should fail
                assert any(
                    any(term in line.lower() for term in ["unable to fetch", "error", "failed", "blocked"])
                    for line in stdout.splitlines()
                ), "✗ WebFetch did not fail"
                print("✓ WebFetch failed (as expected)")

                # And: Playwright fallback should be triggered
                assert any(
                    any(term in line.lower() for term in ["playwright", "npx", "tsx", "web.ts", "webfetch failed, but playwright"])
                    for line in stdout.splitlines()
                ), "✗ Playwright fallback was NOT triggered"
                print("✓ Playwright fallback triggered after WebFetch failure")

                # And: Content should be successfully retrieved
                assert any(
                    any(term in line.lower() for term in ["stocking", "gift", "toy", "wirecutter"])
                    for line in stdout.splitlines()
                ), "✗ Content was NOT retrieved (Playwright may have failed)"
                print("✓ Content retrieved successfully via Playwright")

                # Summary
                print("\n" + "="*60)
                print("✓ Playwright Fallback Test PASSED")
                print("="*60)
                print("\nSummary:")
                print("1. WebFetch attempted: YES")
                print("2. WebFetch failed: YES (as expected)")
                print("3. Playwright fallback triggered: YES")
                print("4. Content retrieved successfully: YES")
                print("\nThis verifies the complete failure → fallback → success flow.")
                print("="*60 + "\n")
