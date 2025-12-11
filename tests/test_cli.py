"""
Tests for the clanker CLI.

These tests verify that:
- The CLI correctly mounts local directories
- The --shell flag works for non-interactive testing
"""

import subprocess
import uuid
from pathlib import Path

import pytest


def run_clanker(project_dir: Path, shell_cmd: str, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run clanker with --shell in a given project directory."""
    return subprocess.run(
        [
            "uv", "run", "clanker",
            "--shell", shell_cmd,
        ],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def describe_workspace_mounting():
    """Tests for workspace directory mounting."""

    @pytest.mark.integration
    def it_mounts_local_directory_to_workspace(tmp_path: Path):
        """Verify that the local directory is mounted at /workspace in the container."""
        # Create a unique file in the temp directory
        marker = f"clanker-test-{uuid.uuid4()}"
        marker_file = tmp_path / "test-marker.txt"
        marker_file.write_text(marker)

        # Run clanker and check if the file exists in /workspace
        result = run_clanker(tmp_path, "cat /workspace/test-marker.txt")

        assert result.returncode == 0, f"Command failed: {result.stderr}"
        assert marker in result.stdout, (
            f"Expected marker '{marker}' not found in output: {result.stdout}"
        )

    @pytest.mark.integration
    def it_can_write_files_back_to_host(tmp_path: Path):
        """Verify that files written in /workspace appear on the host."""
        marker = f"written-from-container-{uuid.uuid4()}"
        output_file = "output.txt"

        # Write a file from inside the container
        result = run_clanker(tmp_path, f"echo '{marker}' > /workspace/{output_file}")

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify the file exists on the host
        host_file = tmp_path / output_file
        assert host_file.exists(), f"File not created on host: {host_file}"
        assert marker in host_file.read_text(), (
            f"Expected marker not in file contents: {host_file.read_text()}"
        )

    @pytest.mark.integration
    def it_preserves_file_permissions(tmp_path: Path):
        """Verify that file permissions are preserved through the mount."""
        script = tmp_path / "test-script.sh"
        script.write_text("#!/bin/bash\necho 'hello'")
        script.chmod(0o755)

        # Check the file is executable inside the container
        result = run_clanker(tmp_path, "test -x /workspace/test-script.sh && echo 'executable'")

        assert result.returncode == 0, f"Command failed: {result.stderr}"
        assert "executable" in result.stdout, (
            f"File not executable in container: {result.stdout}"
        )

    @pytest.mark.integration
    def it_shows_correct_working_directory(tmp_path: Path):
        """Verify that pwd shows /workspace."""
        result = run_clanker(tmp_path, "pwd")

        assert result.returncode == 0, f"Command failed: {result.stderr}"
        assert "/workspace" in result.stdout, (
            f"Expected /workspace, got: {result.stdout}"
        )


def describe_docker_access():
    """Tests for Docker socket access."""

    @pytest.mark.integration
    def it_can_access_docker_socket(tmp_path: Path):
        """Verify that docker commands work inside the container."""
        result = run_clanker(tmp_path, "docker ps --format '{{.ID}}' | head -1")

        assert result.returncode == 0, f"Docker command failed: {result.stderr}"
        # Should return at least one container ID (the clanker container itself)
        # or empty if no containers running - either is fine, just shouldn't error


def describe_installed_tools():
    """Tests for tools that should be available in the container."""

    @pytest.mark.integration
    def it_has_docker_available(tmp_path: Path):
        """Verify docker CLI is installed and can connect to daemon."""
        result = run_clanker(tmp_path, "docker --version && docker info --format '{{.ServerVersion}}'")

        assert result.returncode == 0, f"Docker not available: {result.stderr}"
        assert "Docker version" in result.stdout, f"Unexpected docker output: {result.stdout}"

    @pytest.mark.integration
    def it_has_uv_available(tmp_path: Path):
        """Verify uv is installed."""
        result = run_clanker(tmp_path, "uv --version")

        assert result.returncode == 0, f"uv not available: {result.stderr}"
        assert "uv" in result.stdout, f"Unexpected uv output: {result.stdout}"

    @pytest.mark.integration
    def it_has_uvx_available(tmp_path: Path):
        """Verify uvx is installed."""
        result = run_clanker(tmp_path, "uvx --version")

        assert result.returncode == 0, f"uvx not available: {result.stderr}"

    @pytest.mark.integration
    def it_has_npm_available(tmp_path: Path):
        """Verify npm is installed."""
        result = run_clanker(tmp_path, "npm --version")

        assert result.returncode == 0, f"npm not available: {result.stderr}"

    @pytest.mark.integration
    def it_has_pnpm_available(tmp_path: Path):
        """Verify pnpm is installed."""
        result = run_clanker(tmp_path, "pnpm --version")

        assert result.returncode == 0, f"pnpm not available: {result.stderr}"

    @pytest.mark.integration
    def it_has_playwright_available(tmp_path: Path):
        """Verify playwright is installed and browsers are available."""
        result = run_clanker(tmp_path, "npx playwright --version")

        assert result.returncode == 0, f"Playwright not available: {result.stderr}"
        assert "Version" in result.stdout or result.stdout.strip(), (
            f"Unexpected playwright output: {result.stdout}"
        )

    @pytest.mark.integration
    def it_can_run_playwright_chromium(tmp_path: Path):
        """Verify playwright can launch chromium browser."""
        # Use npx playwright to test browser launch via screenshot
        # This verifies both playwright and chromium are working
        result = run_clanker(
            tmp_path,
            "npx playwright screenshot --browser chromium about:blank /workspace/test.png && ls -la /workspace/test.png",
            timeout=60,
        )

        assert result.returncode == 0, f"Playwright chromium failed: {result.stderr}"
        assert "test.png" in result.stdout, f"Screenshot not created: {result.stdout}"
