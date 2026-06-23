"""
Unit tests for trust-tiered ~/.claude config exposure, the per-cage memory
default, and the machine-local firewall allowlist supplement mount.

The cage no longer bind-mounts the host ~/.claude read-write by default. Strict
mode (default) mounts a disposable, allowlisted COPY so the agent never sees host
credentials and its config writes are discarded on exit; trusted mode (opt-in)
restores the live read-write bind. Style mirrors the other *_test.py unit suites
(pytest-describe describe_/it_ blocks, unittest.mock + tmp_path, no integration).
"""

import argparse
from pathlib import Path
from unittest import mock

from lamp_the_djinn.cli import (
    apply_env_defaults,
    create_parser,
    modify_config,
    stage_claude_config,
)


def _bare_args(**overrides) -> argparse.Namespace:
    """A minimal args namespace for modify_config (strict, no extra features)."""
    base = dict(
        build=False,
        ssh_key_file=None,
        gpg_key_id=None,
        git_user_name=None,
        git_user_email=None,
        gh_token=None,
        port=None,
        volume=None,
        env=None,
        trusted=False,
        memory=None,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def _mounts(config: dict) -> list[str]:
    return config.get("mounts", [])


def _run_args(config: dict) -> list[str]:
    return config.get("runArgs", [])


def _make_claude_home(home: Path) -> Path:
    """Populate a fake ~/.claude with allowlisted config + planted secrets."""
    claude = home / ".claude"
    claude.mkdir(parents=True, exist_ok=True)
    (claude / "settings.json").write_text('{"theme": "dark"}')
    (claude / "CLAUDE.md").write_text("# project memory")
    (claude / "commands").mkdir()
    (claude / "commands" / "foo.md").write_text("do foo")
    (claude / "agents").mkdir()
    (claude / "skills").mkdir()
    # Secrets that must NEVER be copied.
    (claude / ".credentials.json").write_text('{"oauth": "SECRET"}')
    (claude / "auth-token.json").write_text("TOKEN")
    return claude


def describe_stage_claude_config():
    """Allowlist copy: config in, credentials never."""

    def it_copies_allowlisted_config_only(tmp_path: Path):
        home = tmp_path / "home"
        _make_claude_home(home)
        dest = tmp_path / "stage"

        stage_claude_config(home, dest)

        assert (dest / "settings.json").read_text() == '{"theme": "dark"}'
        assert (dest / "CLAUDE.md").read_text() == "# project memory"
        assert (dest / "commands" / "foo.md").read_text() == "do foo"

    def it_never_copies_credentials_or_tokens(tmp_path: Path):
        home = tmp_path / "home"
        _make_claude_home(home)
        dest = tmp_path / "stage"

        stage_claude_config(home, dest)

        # Default-deny: anything outside the allowlist is absent, in particular
        # credential/token-bearing files.
        assert not (dest / ".credentials.json").exists()
        assert not (dest / "auth-token.json").exists()
        copied = {p.name for p in dest.iterdir()}
        assert not any("credential" in n or "token" in n or "auth" in n for n in copied)

    def it_is_a_noop_for_missing_source_dir(tmp_path: Path):
        """No ~/.claude on the host -> dest is created but empty (no error)."""
        home = tmp_path / "empty-home"
        dest = tmp_path / "stage"

        stage_claude_config(home, dest)

        assert dest.exists()
        assert list(dest.iterdir()) == []

    def it_copies_only_existing_allowlist_entries(tmp_path: Path):
        """Allowlist entries absent on the host are simply skipped."""
        home = tmp_path / "home"
        claude = home / ".claude"
        claude.mkdir(parents=True)
        (claude / "settings.json").write_text("{}")
        dest = tmp_path / "stage"

        stage_claude_config(home, dest)

        assert (dest / "settings.json").exists()
        assert not (dest / "CLAUDE.md").exists()
        assert not (dest / "commands").exists()


def describe_strict_claude_mount():
    """Default (strict): mount the staged COPY, write back only transcript data."""

    def it_mounts_the_stage_dir_not_the_host_claude(tmp_path: Path):
        stage = tmp_path / "stage"
        stage.mkdir()
        # An embedded-style live rw host .claude bind that must be filtered out.
        config = {
            "mounts": ["source=${localEnv:HOME}/.claude,target=/home/node/.claude,type=bind"],
            "runArgs": [],
        }
        with mock.patch("pathlib.Path.home", return_value=tmp_path / "home"):
            config = modify_config(config, _bare_args(), tmp_path, trusted=False, claude_stage_dir=stage)

        mounts = _mounts(config)
        # The .claude root mount source is the stage dir, NOT the host config.
        assert f"source={stage},target=/home/node/.claude,type=bind" in mounts
        # No LIVE rw bind of the host ~/.claude root.
        assert "source=${localEnv:HOME}/.claude,target=/home/node/.claude,type=bind" not in mounts

    def it_writes_back_transcript_data_when_host_paths_exist(tmp_path: Path):
        home = tmp_path / "home"
        (home / ".claude" / "projects").mkdir(parents=True)
        (home / ".claude" / "history.jsonl").write_text("{}\n")
        stage = tmp_path / "stage"
        stage.mkdir()

        with mock.patch("pathlib.Path.home", return_value=home):
            config = modify_config(
                {"mounts": [], "runArgs": []},
                _bare_args(),
                tmp_path,
                trusted=False,
                claude_stage_dir=stage,
            )

        mounts = _mounts(config)
        assert "source=${localEnv:HOME}/.claude/projects,target=/home/node/.claude/projects,type=bind" in mounts
        assert (
            "source=${localEnv:HOME}/.claude/history.jsonl,target=/home/node/.claude/history.jsonl,type=bind" in mounts
        )

    def it_omits_transcript_mounts_when_host_paths_absent(tmp_path: Path):
        home = tmp_path / "home"
        home.mkdir()
        stage = tmp_path / "stage"
        stage.mkdir()

        with mock.patch("pathlib.Path.home", return_value=home):
            config = modify_config(
                {"mounts": [], "runArgs": []},
                _bare_args(),
                tmp_path,
                trusted=False,
                claude_stage_dir=stage,
            )

        mounts = " ".join(_mounts(config))
        assert "/home/node/.claude/projects" not in mounts
        assert "/home/node/.claude/history.jsonl" not in mounts


def describe_trusted_claude_mount():
    """Opt-in trusted: live read-write bind of the host ~/.claude."""

    def it_mounts_the_live_host_claude_rw(tmp_path: Path):
        with mock.patch("pathlib.Path.home", return_value=tmp_path / "home"):
            config = modify_config(
                {"mounts": [], "runArgs": []},
                _bare_args(trusted=True),
                tmp_path,
                trusted=True,
                claude_stage_dir=None,
            )

        mounts = _mounts(config)
        assert "source=${localEnv:HOME}/.claude,target=/home/node/.claude,type=bind" in mounts
        # No readonly qualifier -- trusted is read-write.
        claude_mount = next(m for m in mounts if "/home/node/.claude,type=bind" in m)
        assert "readonly" not in claude_mount


def describe_memory_density():
    """Per-cage memory cap: 2g default, --memory override, no duplicates."""

    def it_defaults_to_2g(tmp_path: Path):
        with mock.patch("pathlib.Path.home", return_value=tmp_path / "home"):
            config = modify_config(
                {"mounts": [], "runArgs": ["--memory=8g", "--cpus=4", "--pids-limit=500"]},
                _bare_args(),
                tmp_path,
                trusted=False,
                claude_stage_dir=tmp_path / "stage",
            )

        run_args = _run_args(config)
        assert "--memory=2g" in run_args
        # The old 8g cap is gone; exactly one --memory remains.
        assert "--memory=8g" not in run_args
        assert sum(1 for a in run_args if a.startswith("--memory")) == 1
        # --cpus / --pids-limit untouched.
        assert "--cpus=4" in run_args
        assert "--pids-limit=500" in run_args

    def it_honors_the_memory_override(tmp_path: Path):
        with mock.patch("pathlib.Path.home", return_value=tmp_path / "home"):
            config = modify_config(
                {"mounts": [], "runArgs": ["--memory=8g"]},
                _bare_args(memory="4g"),
                tmp_path,
                trusted=False,
                claude_stage_dir=tmp_path / "stage",
            )

        run_args = _run_args(config)
        assert "--memory=4g" in run_args
        assert sum(1 for a in run_args if a.startswith("--memory")) == 1

    def it_strips_separate_token_memory_pair(tmp_path: Path):
        """A `--memory VALUE` pair (two tokens) is removed, not just --memory=VALUE."""
        with mock.patch("pathlib.Path.home", return_value=tmp_path / "home"):
            config = modify_config(
                {"mounts": [], "runArgs": ["--memory", "8g", "--cpus=4"]},
                _bare_args(),
                tmp_path,
                trusted=False,
                claude_stage_dir=tmp_path / "stage",
            )

        run_args = _run_args(config)
        assert "8g" not in run_args
        assert "--memory" not in run_args  # bare token form gone
        assert "--memory=2g" in run_args
        assert "--cpus=4" in run_args


def describe_allowlist_supplement_mount():
    """Machine-local domains file is bind-mounted read-only when present."""

    def it_mounts_the_supplement_file_when_present(tmp_path: Path):
        home = tmp_path / "home"
        cfg = home / ".config" / "lamp-the-djinn"
        cfg.mkdir(parents=True)
        domains = cfg / "allowed-domains.txt"
        domains.write_text("example.internal\n")

        with mock.patch("pathlib.Path.home", return_value=home):
            config = modify_config(
                {"mounts": [], "runArgs": []},
                _bare_args(),
                tmp_path,
                trusted=False,
                claude_stage_dir=tmp_path / "stage",
            )

        mount = next(m for m in _mounts(config) if "ltd-allowed-domains.txt" in m)
        assert f"source={domains}" in mount
        assert "target=/usr/local/share/ltd-allowed-domains.txt" in mount
        assert "readonly" in mount

    def it_omits_the_supplement_mount_when_absent(tmp_path: Path):
        home = tmp_path / "home"
        home.mkdir()

        with mock.patch("pathlib.Path.home", return_value=home):
            config = modify_config(
                {"mounts": [], "runArgs": []},
                _bare_args(),
                tmp_path,
                trusted=False,
                claude_stage_dir=tmp_path / "stage",
            )

        assert not any("ltd-allowed-domains.txt" in m for m in _mounts(config))


def describe_trusted_flag_and_env():
    """--trusted defaults False; LTD_TRUSTED opts in via apply_env_defaults."""

    def it_defaults_trusted_false():
        parser = create_parser()
        args = parser.parse_args([])
        assert args.trusted is False

    def it_sets_trusted_from_flag():
        parser = create_parser()
        args = parser.parse_args(["--trusted"])
        assert args.trusted is True

    def it_reads_trusted_from_env():
        parser = create_parser()
        args = parser.parse_args([])
        with mock.patch.dict("os.environ", {"LTD_TRUSTED": "1"}, clear=False):
            apply_env_defaults(args)
        assert args.trusted is True

    def it_reads_memory_from_env():
        parser = create_parser()
        args = parser.parse_args([])
        with mock.patch.dict("os.environ", {"LTD_MEMORY": "4g"}, clear=False):
            apply_env_defaults(args)
        assert args.memory == "4g"
