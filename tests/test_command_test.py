"""
Unit tests for explicit command pass-through, provider env injection, and the
cache-freshness manifest.

These cover the harness-generalization refinement: ltd no longer maintains a
named-harness registry. Instead the command is whatever the user types after
ltd's own options (`ltd [ltd-opts] <command...>`), both provider env families
are injected when the proxy is engaged, and package-runner invocations are
recorded to a manifest for the nightly cache warm.

Style mirrors tests/test_cli.py and tests/test_isolation_test.py (pytest-describe
describe_/it_ blocks, unittest.mock rather than the pytest-mock `mocker` fixture,
which is not in the dev dependency set).
"""

import argparse
from pathlib import Path
from unittest import mock

from lamp_the_djinn.cli import (
    create_parser,
    modify_config,
    record_manifest,
    resolve_command,
)
from lamp_the_djinn.harness import provider_env_all


def describe_command_parsing():
    """REMAINDER splits ltd's own options from the in-cage command."""

    def it_splits_ltd_opts_from_command():
        """ltd options before the command are parsed; the rest is the command."""
        parser = create_parser()
        args = parser.parse_args(["--model", "glm-5.2", "claude", "-p", "hi"])
        assert args.model == "glm-5.2"
        # The command's own -p is NOT stolen by ltd's -p/--port.
        assert args.command == ["claude", "-p", "hi"]
        assert args.port is None

    def it_treats_bare_runner_as_the_command():
        """A command with no leading ltd options is captured verbatim."""
        parser = create_parser()
        args = parser.parse_args(["npx", "@anthropic/claude"])
        assert args.command == ["npx", "@anthropic/claude"]

    def it_does_not_steal_command_flags_matching_ltd_flags():
        """ltd's -p stops at the first command token; later -p belongs to the command."""
        parser = create_parser()
        args = parser.parse_args(["-p", "8080", "claude", "-p", "prompt"])
        # ltd's own -p captured the port; the command keeps its own -p.
        assert args.port == ["8080"]
        assert args.command == ["claude", "-p", "prompt"]

    def it_leaves_command_empty_when_only_ltd_opts_given():
        """With no command tokens, command is empty (default applies later)."""
        parser = create_parser()
        args = parser.parse_args(["--safe-mode"])
        assert args.command == []
        assert args.safe_mode is True

    def it_has_no_harness_flag():
        """The named --harness flag was removed."""
        parser = create_parser()
        # Unknown option -> parser errors (SystemExit), proving it is gone.
        try:
            parser.parse_args(["--harness", "codex"])
        except SystemExit:
            pass
        else:  # pragma: no cover - guard
            raise AssertionError("--harness should no longer be a recognized flag")


def describe_resolve_command():
    """Precedence: explicit command > --shell > default claude."""

    def it_prefers_an_explicit_command():
        assert resolve_command(["claude", "-p", "hi"], "echo no", False) == ["claude", "-p", "hi"]

    def it_falls_back_to_default_claude():
        """Bare ltd (no command, no shell) defaults to skip-permissions claude."""
        assert resolve_command([], None, False) == ["claude", "--dangerously-skip-permissions"]

    def it_uses_plain_claude_in_safe_mode():
        """--safe-mode drops the skip-permissions flag."""
        assert resolve_command([], None, True) == ["claude"]

    def it_maps_shell_to_bash_c():
        """--shell CMD is equivalent to bash -c CMD when no command is given."""
        assert resolve_command([], "cat /workspace/x", False) == ["bash", "-c", "cat /workspace/x"]


def describe_provider_env_all():
    """Both provider families are emitted, pointed at the proxy."""

    def it_emits_both_families():
        env = provider_env_all("http://host.docker.internal:4000/v1", "glm-5.2", "k")
        assert env["OPENAI_BASE_URL"] == "http://host.docker.internal:4000/v1"
        assert env["OPENAI_API_KEY"] == "k"
        assert env["OPENAI_MODEL"] == "glm-5.2"
        assert env["ANTHROPIC_BASE_URL"] == "http://host.docker.internal:4000/v1"
        assert env["ANTHROPIC_AUTH_TOKEN"] == "k"
        assert env["ANTHROPIC_MODEL"] == "glm-5.2"

    def it_honors_anthropic_proxy_override():
        """LTD_ANTHROPIC_PROXY_URL overrides only the anthropic base URL."""
        with mock.patch.dict("os.environ", {"LTD_ANTHROPIC_PROXY_URL": "http://h:4000/anthropic"}):
            env = provider_env_all("http://h:4000/v1", "local", "k")
        assert env["OPENAI_BASE_URL"] == "http://h:4000/v1"
        assert env["ANTHROPIC_BASE_URL"] == "http://h:4000/anthropic"


def _bare_args() -> argparse.Namespace:
    """A minimal args namespace for modify_config (no extra features)."""
    return argparse.Namespace(
        build=False,
        ssh_key_file=None,
        gpg_key_id=None,
        git_user_name=None,
        git_user_email=None,
        gh_token=None,
        port=None,
        volume=None,
        env=None,
    )


def _run_args(config: dict) -> list[str]:
    return config.get("runArgs", [])


def describe_dual_env_injection():
    """modify_config injects both env families iff the proxy is engaged."""

    def it_injects_both_families_when_proxy_engaged(tmp_path: Path):
        config = modify_config(
            {"mounts": [], "runArgs": []},
            _bare_args(),
            tmp_path,
            proxy_url="http://host.docker.internal:4000/v1",
            model="glm-5.2",
            proxy_api_key="k",
        )
        run_args = _run_args(config)
        joined = " ".join(run_args)
        assert "OPENAI_BASE_URL=http://host.docker.internal:4000/v1" in run_args
        assert "OPENAI_MODEL=glm-5.2" in run_args
        assert "ANTHROPIC_BASE_URL=http://host.docker.internal:4000/v1" in run_args
        assert "ANTHROPIC_MODEL=glm-5.2" in run_args
        # host.docker.internal mapping is added so the cage can reach the proxy.
        assert "--add-host=host.docker.internal:host-gateway" in run_args
        assert "host" in joined

    def it_injects_no_provider_env_when_no_proxy(tmp_path: Path):
        config = modify_config(
            {"mounts": [], "runArgs": []},
            _bare_args(),
            tmp_path,
            proxy_url=None,
        )
        run_args = _run_args(config)
        assert not any(a.startswith("OPENAI_") or "OPENAI_" in a for a in run_args)
        assert not any(a.startswith("ANTHROPIC_") or "ANTHROPIC_" in a for a in run_args)
        assert "--add-host=host.docker.internal:host-gateway" not in run_args

    def it_adds_writable_auth_mount_always(tmp_path: Path):
        """The scoped, writable credential mount is present regardless of proxy."""
        config = modify_config(
            {"mounts": [], "runArgs": []},
            _bare_args(),
            tmp_path,
            proxy_url=None,
        )
        mounts = " ".join(config["mounts"])
        assert "/home/node/.config/ltd-auth" in mounts
        # NOT readonly -- this mount must be writable to persist credentials.
        auth_mount = next(m for m in config["mounts"] if "ltd-auth" in m)
        assert "readonly" not in auth_mount


def describe_path_identity_mounts():
    """Host dirs mount at their own paths inside the cage (path identity)."""

    def it_mounts_the_project_at_its_own_path(tmp_path: Path):
        proj = tmp_path / "proj"
        proj.mkdir()
        config = modify_config(
            {"mounts": [], "runArgs": []},
            _bare_args(),
            tmp_path,
            project_dir=proj,
        )
        # target == source == the real host path, not /workspace.
        assert config["workspaceMount"] == (f"source={proj},target={proj},type=bind,consistency=delegated")
        assert config["workspaceFolder"] == str(proj)
        assert "/workspace" not in config["workspaceMount"]

    def it_identity_mounts_a_bare_volume_path(tmp_path: Path):
        d = tmp_path / "bertha" / "app"
        d.mkdir(parents=True)
        args = _bare_args()
        args.volume = [str(d)]
        config = modify_config({"mounts": [], "runArgs": []}, args, tmp_path)
        resolved = str(Path(str(d)).resolve())
        assert f"{resolved}:{resolved}" in config["runArgs"]

    def it_preserves_an_explicit_host_colon_container_volume(tmp_path: Path):
        args = _bare_args()
        args.volume = ["/h/data:/container/data"]
        config = modify_config({"mounts": [], "runArgs": []}, args, tmp_path)
        assert "/h/data:/container/data" in config["runArgs"]

    def it_mounts_multiple_volumes(tmp_path: Path):
        a = tmp_path / "a"
        b = tmp_path / "b"
        a.mkdir()
        b.mkdir()
        args = _bare_args()
        args.volume = [str(a), str(b)]
        config = modify_config({"mounts": [], "runArgs": []}, args, tmp_path)
        for d in (a, b):
            r = str(Path(str(d)).resolve())
            assert f"{r}:{r}" in config["runArgs"]


def describe_record_manifest():
    """Conservative package-spec extraction from package-runner commands."""

    def it_records_npx_spec(tmp_path: Path):
        with mock.patch("pathlib.Path.home", return_value=tmp_path):
            record_manifest(["npx", "@anthropic/claude"])
        assert "@anthropic/claude" in self_check(tmp_path)

    def it_records_uvx_spec(tmp_path: Path):
        with mock.patch("pathlib.Path.home", return_value=tmp_path):
            record_manifest(["uvx", "aider"])
        assert "aider" in self_check(tmp_path)

    def it_skips_flags_to_find_the_package(tmp_path: Path):
        with mock.patch("pathlib.Path.home", return_value=tmp_path):
            record_manifest(["npx", "-y", "@openai/codex"])
        assert "@openai/codex" in self_check(tmp_path)

    def it_records_npm_install_and_uv_tool(tmp_path: Path):
        with mock.patch("pathlib.Path.home", return_value=tmp_path):
            record_manifest(["npm", "install", "prettier"])
            record_manifest(["uv", "tool", "install", "black"])
        lines = self_check(tmp_path)
        assert "prettier" in lines
        assert "black" in lines

    def it_ignores_non_runner_commands(tmp_path: Path):
        with mock.patch("pathlib.Path.home", return_value=tmp_path):
            record_manifest(["claude", "-p", "hi"])
            record_manifest([])
        assert self_check(tmp_path) == []

    def it_dedupes_repeated_specs(tmp_path: Path):
        with mock.patch("pathlib.Path.home", return_value=tmp_path):
            record_manifest(["uvx", "aider"])
            record_manifest(["uvx", "aider"])
        assert self_check(tmp_path).count("aider") == 1


def self_check(home: Path) -> list[str]:
    """Read manifest lines under a mocked HOME (helper for record_manifest tests)."""
    manifest = home / ".cache" / "lamp-the-djinn" / "harness-manifest.txt"
    if not manifest.exists():
        return []
    return manifest.read_text().splitlines()
