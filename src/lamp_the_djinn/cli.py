"""CLI entry points for lamp-the-djinn."""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from . import harness as harness_mod

__all__ = ["main", "shell_remote"]


def get_embedded_devcontainer_dir() -> Path:
    """Get the path to embedded devcontainer files in the package."""
    return Path(__file__).parent / "devcontainer"


def detect_runtime(preferred: str) -> str:
    """Resolve which OCI runtime to hand to Docker (the "isolation seam").

    Queries Docker for its registered runtimes and reconciles the user's
    preference against what is actually installed.

    - preferred == "auto": prefer gVisor ("runsc") when it is installed,
      otherwise fall back to the stock "runc". This keeps default behavior
      unchanged on hosts that only have runc.
    - preferred is a concrete name (e.g. "runsc", "kata-runtime", "runc"):
      use it if Docker reports it, otherwise warn on stderr and fall back to
      "runc" so the run still proceeds.

    Robust to any docker failure (missing binary, daemon down, malformed
    output): always returns a usable runtime ("runc").
    """
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{json .Runtimes}}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            available: list[str] = []
        else:
            runtimes = json.loads(result.stdout.strip() or "{}")
            available = list(runtimes.keys()) if isinstance(runtimes, dict) else []
    except (OSError, ValueError):
        available = []

    if preferred == "auto":
        return "runsc" if "runsc" in available else "runc"

    if preferred in available:
        return preferred

    print(
        f"Warning: requested isolation runtime '{preferred}' is not registered with Docker; falling back to 'runc'.",
        file=sys.stderr,
    )
    return "runc"


def get_workspace_dir(instance_id: str) -> Path:
    """Get instance-specific workspace directory for devcontainer files.

    Each instance gets its own directory to prevent race conditions when
    multiple lamp-the-djinn instances run with different configurations.
    """
    return Path.home() / ".cache" / "lamp-the-djinn" / f"workspace-{instance_id}"


def extract_devcontainer_files(instance_id: str) -> Path:
    """Extract embedded devcontainer files to an instance-specific cache directory."""
    workspace_dir = get_workspace_dir(instance_id)
    devcontainer_dir = workspace_dir / ".devcontainer"
    devcontainer_dir.mkdir(parents=True, exist_ok=True)

    pkg_dir = get_embedded_devcontainer_dir()
    for f in pkg_dir.iterdir():
        if f.is_file() and f.name != "__init__.py" and not f.name.endswith(".pyc"):
            shutil.copy2(f, devcontainer_dir / f.name)

    return workspace_dir


def generate_ssh_config(runtime_dir: Path, ssh_key_name: str) -> Path:
    """Generate SSH config file for GitHub."""
    ssh_config = runtime_dir / "ssh_config"
    ssh_config.write_text(f"""Host github.com
  HostName github.com
  User git
  IdentityFile /home/node/.ssh/{ssh_key_name}
  IdentitiesOnly yes
""")
    # SSH requires strict permissions on config files
    ssh_config.chmod(0o644)
    return ssh_config


# Allowlist of names copied from the host ~/.claude into the strict-mode stage
# dir. Default-deny: anything NOT named here is never copied. In particular this
# excludes .credentials.json and any auth/token/credential-bearing file, so the
# untrusted agent never sees host credentials. `hooks` is included so the user's
# own hooks (e.g. the transcript-posting Stop hook) still run in strict mode --
# they execute against the disposable copy, so the agent can't persist changes
# to the host's hooks.
_CLAUDE_CONFIG_ALLOWLIST = ("settings.json", "CLAUDE.md", "commands", "agents", "skills", "hooks")


def stage_claude_config(home: Path, dest: Path) -> None:
    """Copy an allowlisted subset of host ``~/.claude`` config into ``dest``.

    Copies ONLY ``settings.json``, ``CLAUDE.md``, and the ``commands/``,
    ``agents/``, ``skills/`` dirs -- each only if it exists on the host. This is
    an allowlist (default-deny): unknown entries (including ``.credentials.json``
    or anything bearing ``credential``/``token``/``auth`` in its name) are never
    copied. The result is a disposable copy the cage can mount + freely mutate
    without touching the host or exposing host credentials.
    """
    src_root = home / ".claude"
    dest.mkdir(parents=True, exist_ok=True)

    for name in _CLAUDE_CONFIG_ALLOWLIST:
        src = src_root / name
        if not src.exists():
            continue
        target = dest / name
        if src.is_dir():
            shutil.copytree(src, target, dirs_exist_ok=True)
        else:
            shutil.copy2(src, target)


def command_is_pi(command: list[str]) -> bool:
    """True if the command invokes the pi coding agent (directly or via npx/pnpm dlx)."""
    if not command:
        return False
    if command[0] == "pi":
        return True
    return any("pi-coding-agent" in tok for tok in command)


def stage_pi_config(dest: Path, proxy_url: str, model: str, api_key: str) -> None:
    """Stage a pi (@earendil-works/pi-coding-agent) config pointed at the proxy.

    pi selects providers via models.json (it ignores OPENAI_BASE_URL), so to drive
    it from the cage we write a `lamp` provider whose baseUrl is the proxy and make
    it the default -- a bare `pi` in the cage then talks to the local model.
    """
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "models.json").write_text(
        json.dumps(
            {
                "providers": {
                    "lamp": {
                        "baseUrl": proxy_url,
                        "api": "openai-completions",
                        "apiKey": api_key,
                        "models": [{"id": model, "input": ["text"]}],
                    }
                }
            },
            indent=2,
        )
    )
    (dest / "settings.json").write_text(json.dumps({"defaultProvider": "lamp", "defaultModel": model}, indent=2))


def modify_config(
    config: dict,
    args: argparse.Namespace,
    runtime_dir: Path,
    devcontainer_dir: Path | None = None,
    project_dir: Path | None = None,
    proxy_url: str | None = None,
    model: str | None = None,
    proxy_api_key: str | None = None,
    runtime: str = "runc",
    trusted: bool = False,
    claude_stage_dir: Path | None = None,
    pi_stage_dir: Path | None = None,
) -> dict:
    """Modify devcontainer config with user-specific settings."""

    # If --build flag, replace image with build config
    if args.build and devcontainer_dir:
        config.pop("image", None)
        config["build"] = {"dockerfile": "Dockerfile", "context": "."}

    # Mount the project at its OWN host path (path identity), so absolute paths the
    # agent emits (code, configs, logs, commits) stay valid on the host -- no
    # /workspace remap that makes agents hallucinate /app-style paths.
    if project_dir:
        config["workspaceMount"] = f"source={project_dir},target={project_dir},type=bind,consistency=delegated"
        config["workspaceFolder"] = str(project_dir)

    # Trust-tiered ~/.claude config exposure.
    #
    # First, strip any pre-existing /home/node/.claude mount (the embedded
    # devcontainer.json ships a live rw bind) and the old claude-code-config
    # readonly-replace block, so we can append exactly the mount(s) the chosen
    # trust tier wants -- same pattern as the ssh/gpg filtering below.
    if "mounts" in config:
        config["mounts"] = [
            m for m in config["mounts"] if "/home/node/.claude" not in m and "claude-code-config" not in m
        ]

    config.setdefault("mounts", [])
    if trusted:
        # TRUSTED: live read-write bind of the host ~/.claude -- the agent's
        # config writes (settings, hooks, CLAUDE.md) land on the host directly.
        # This is the historical behavior, now opt-in only.
        config["mounts"].append("source=${localEnv:HOME}/.claude,target=/home/node/.claude,type=bind")
    else:
        # STRICT (default): mount a disposable COPY of the allowlisted config
        # (staged on the host by stage_claude_config) at /home/node/.claude. It
        # is rw inside the cage but the host ~/.claude is untouched, so the
        # agent's config writes are discarded on exit.
        #
        # DEFERRED: vet-on-exit selective apply of the agent's config changes.
        # Strict mode currently just discards them (safe); propagating approved
        # changes back to the host is a follow-up.
        if claude_stage_dir is not None:
            config["mounts"].append(f"source={claude_stage_dir},target=/home/node/.claude,type=bind")
        # Transcripts/session history are DATA, not config: write them back so
        # session continuity (`--continue`) and the transcript hook keep working.
        # These nested rw binds overlay the copied .claude with the live host
        # data dirs. (settings/hooks/CLAUDE.md remain the copied, discard-on-exit
        # part; only this transcript data is write-back safe.) Mount each only if
        # the host path exists, so a fresh install doesn't fail on a missing dir.
        home = Path.home()
        if (home / ".claude" / "projects").exists():
            config["mounts"].append(
                "source=${localEnv:HOME}/.claude/projects,target=/home/node/.claude/projects,type=bind"
            )
        if (home / ".claude" / "history.jsonl").exists():
            config["mounts"].append(
                "source=${localEnv:HOME}/.claude/history.jsonl,target=/home/node/.claude/history.jsonl,type=bind"
            )

    # pi harness adapter: mount the staged pi config (its `lamp` provider points at
    # the proxy) at the cage's ~/.pi/agent so a bare `pi` uses the local model.
    if pi_stage_dir is not None:
        config.setdefault("mounts", [])
        config["mounts"].append(f"source={pi_stage_dir},target=/home/node/.pi/agent,type=bind")

    # Filter out existing SSH and GPG mounts
    if "mounts" in config:
        config["mounts"] = [m for m in config["mounts"] if ".ssh/" not in m and ".gnupg" not in m]

    # Add SSH mounts if key provided
    if args.ssh_key_file:
        ssh_key_path = Path(args.ssh_key_file).resolve()
        ssh_key_name = ssh_key_path.name
        ssh_config_path = generate_ssh_config(runtime_dir, ssh_key_name)

        config.setdefault("mounts", [])
        config["mounts"].append(f"source={ssh_key_path},target=/home/node/.ssh/{ssh_key_name},type=bind,readonly")
        config["mounts"].append(f"source={ssh_config_path},target=/home/node/.ssh/config,type=bind,readonly")

    # Add GPG mount if key ID provided
    if args.gpg_key_id:
        config.setdefault("mounts", [])
        config["mounts"].append("source=${localEnv:HOME}/.gnupg,target=/home/node/.gnupg,type=bind,readonly")

    # Machine-local firewall allowlist supplement. If the host has a
    # ~/.config/lamp-the-djinn/allowed-domains.txt, bind it read-only into the
    # cage where init-firewall.sh expects it. The firewall script resolves these
    # domains and adds them to the allowed-domains ipset (in addition to the
    # baked-in whitelist), letting a host opt extra domains through egress
    # without rebuilding the image.
    allowed_domains = Path.home() / ".config" / "lamp-the-djinn" / "allowed-domains.txt"
    if allowed_domains.exists():
        config.setdefault("mounts", [])
        config["mounts"].append(
            f"source={allowed_domains},target=/usr/local/share/ltd-allowed-domains.txt,type=bind,readonly"
        )

    # Read-only harness cache mount -- ONLY when the proxy is engaged AND the host
    # cache has actually been warmed by the trusted nightly refresh
    # (scripts/refresh-harness-cache.sh). Mounting an empty read-only cache and
    # pointing npm/uv at it would break npx/uvx (they can't write their exec dirs),
    # so until the cache is populated the cage uses its own writable cache plus the
    # registry allowlist. Once warmed, the cage uses the pre-vetted cooldown copy.
    harness_cache = Path.home() / ".cache" / "lamp-the-djinn" / "harness-cache"
    cache_warmed = harness_cache.is_dir() and any(harness_cache.iterdir())
    if proxy_url and cache_warmed:
        config.setdefault("mounts", [])
        config["mounts"].append(
            "source=${localEnv:HOME}/.cache/lamp-the-djinn/harness-cache,"
            "target=/home/node/.cache/ltd-harness,type=bind,readonly"
        )

    # WRITABLE credential-persistence mount. Harness sessions (e.g. an OAuth
    # token a harness writes after `login`) persist across runs via this volume.
    #
    # SECURITY PRINCIPLE: this mount is READ-WRITE and lives inside the cage, so
    # the untrusted agent can READ everything in it. Therefore persist ONLY
    # scoped/revocable credentials here. The model key never enters the cage --
    # it stays in the LiteLLM proxy on the host. The primary git identity stays
    # out too: push host-side, or supply a fine-grained, single-repo, revocable
    # PAT. See README "Credential persistence" for the full rationale.
    config.setdefault("mounts", [])
    config["mounts"].append(
        "source=${localEnv:HOME}/.cache/lamp-the-djinn/auth,target=/home/node/.config/ltd-auth,type=bind"
    )

    # Add docker run flags (ports, volumes, env vars) to runArgs
    config.setdefault("runArgs", [])

    # Per-cage memory cap (density default 2g). Strip any existing --memory=VALUE
    # or `--memory VALUE` pair from runArgs, then append our resolved cap.
    # --cpus / --pids-limit are left untouched.
    memory = getattr(args, "memory", None) or "2g"
    stripped_run_args: list[str] = []
    skip_next = False
    for run_arg in config["runArgs"]:
        if skip_next:
            skip_next = False
            continue
        if run_arg == "--memory":
            skip_next = True  # also drop the separate value token that follows
            continue
        if run_arg.startswith("--memory="):
            continue
        stripped_run_args.append(run_arg)
    config["runArgs"] = stripped_run_args
    config["runArgs"].append(f"--memory={memory}")

    # Isolation seam: when a stronger OCI runtime than the stock runc was
    # resolved (e.g. gVisor's runsc or kata-runtime), tell Docker to use it.
    # For plain runc we add nothing, leaving default behavior untouched.
    if runtime != "runc":
        config["runArgs"].extend(["--runtime", runtime])

    if args.port:
        for port_mapping in args.port:
            # Support both HOST:CONTAINER and just PORT (same for both)
            if ":" not in port_mapping:
                port_mapping = f"{port_mapping}:{port_mapping}"
            config["runArgs"].extend(["-p", port_mapping])
    if args.volume:
        for vol in args.volume:
            # Path identity: a bare path mounts at its own path inside the cage
            # (`/mnt/x` -> `/mnt/x`), read-write and live. An explicit
            # `host:container` mapping is honored as-is. Repeat -v for multiple dirs.
            mapping = vol if ":" in vol else f"{Path(vol).resolve()}:{Path(vol).resolve()}"
            config["runArgs"].extend(["-v", mapping])
    if args.env:
        for env_var in args.env:
            config["runArgs"].extend(["-e", env_var])

    # Provider env injection: wire whatever command runs in the cage to the
    # LiteLLM proxy on the host. We inject BOTH provider families (OPENAI_* and
    # ANTHROPIC_*) since the command is arbitrary and we cannot know its wire
    # format in advance; the harness reads whichever it understands.
    if proxy_url:
        # Point the in-container npm/uv caches at the read-only harness cache only
        # when it is warmed; otherwise leave the cage's default writable caches so
        # npx/uvx can fetch the harness fresh.
        if cache_warmed:
            config["runArgs"].extend(["-e", "UV_CACHE_DIR=/home/node/.cache/ltd-harness/uv"])
            config["runArgs"].extend(["-e", "npm_config_cache=/home/node/.cache/ltd-harness/npm"])

        api_key = proxy_api_key or "lamp-the-djinn"
        prov_env = harness_mod.provider_env_all(proxy_url, model or "local", api_key)
        for key, value in prov_env.items():
            config["runArgs"].extend(["-e", f"{key}={value}"])
        # The container reaches the host proxy via the docker bridge gateway.
        # On Linux host.docker.internal is not automatic, so map it explicitly.
        config["runArgs"].append("--add-host=host.docker.internal:host-gateway")

    # Build postStartCommand
    commands = ["sudo /usr/local/bin/init-firewall.sh"]

    if args.git_user_name:
        commands.append(f"git config --global user.name {shlex.quote(args.git_user_name)}")

    if args.git_user_email:
        commands.append(f"git config --global user.email {shlex.quote(args.git_user_email)}")

    if args.gpg_key_id:
        commands.append(f"git config --global user.signingkey {shlex.quote(args.gpg_key_id)}")
        commands.append("git config --global commit.gpgsign true")
        commands.append("git config --global gpg.program gpg")
        commands.append("gpg-connect-agent /bye >/dev/null 2>&1 || true")

    if args.gh_token:
        commands.append(f"echo {shlex.quote(args.gh_token)} | gh auth login --with-token")

    config["postStartCommand"] = " && ".join(commands)

    return config


def resolve_command(command: list[str], shell_cmd: str | None, safe_mode: bool) -> list[str]:
    """Decide what to run inside the cage.

    Precedence: explicit command > --shell CMD > default claude. The default
    preserves today's bare-`ltd` behavior: `claude --dangerously-skip-permissions`
    normally, or plain `claude` under --safe-mode (permission prompts on).
    `--shell CMD` is a convenience equal to `bash -c CMD`.
    """
    if command:
        return list(command)
    if shell_cmd:
        return ["bash", "-c", shell_cmd]
    if safe_mode:
        return ["claude"]
    return ["claude", "--dangerously-skip-permissions"]


def record_manifest(command: list[str]) -> None:
    """Record a harness package spec to the cache-freshness manifest.

    If the command is `npx <pkg>` / `npm ... <pkg>` or `uvx <pkg>` /
    `uv tool ... <pkg>`, append the first obvious (non-flag) package token to
    ``~/.cache/lamp-the-djinn/harness-manifest.txt`` (deduped). The trusted
    nightly refresh (scripts/refresh-harness-cache.sh) reads this file to warm
    the read-only harness cache with packages users actually invoke.

    Conservative by design: records only the first non-flag arg after the
    package-runner token, and only for the runners above. Anything else is a
    no-op.
    """
    if not command:
        return

    runner = command[0]
    rest = command[1:]

    if runner in ("npx", "uvx"):
        # `npx <pkg>` / `uvx <pkg>`: first non-flag arg is the package spec.
        pkg = _first_non_flag(rest)
    elif runner == "npm" and rest and rest[0] in ("install", "i", "exec", "x"):
        # `npm install/exec <pkg>`: spec follows the subcommand.
        pkg = _first_non_flag(rest[1:])
    elif runner == "uv" and rest and rest[0] == "tool":
        # `uv tool install/run <pkg>`: spec follows `tool <subcommand>`.
        pkg = _first_non_flag(rest[2:]) if len(rest) > 1 else None
    else:
        return

    if not pkg:
        return

    manifest = Path.home() / ".cache" / "lamp-the-djinn" / "harness-manifest.txt"
    manifest.parent.mkdir(parents=True, exist_ok=True)

    existing = manifest.read_text().splitlines() if manifest.exists() else []
    if pkg in existing:
        return

    with manifest.open("a") as f:
        f.write(f"{pkg}\n")


def _first_non_flag(args: list[str]) -> str | None:
    """Return the first argument that does not start with '-', or None."""
    for a in args:
        if not a.startswith("-"):
            return a
    return None


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Run any coding agent in a sandboxed devcontainer. "
        "The command after ltd's own options is run inside the cage: "
        "ltd [ltd-opts] <command...>",
        epilog=(
            "Examples:\n"
            '  ltd claude -p "fix the failing test"\n'
            "  ltd npx @anthropic/claude\n"
            "  ltd --model glm-5.2 aider\n"
            "  ltd                       # bare: runs claude --dangerously-skip-permissions\n"
            "\n"
            "Everything after ltd's options is the command to run in the cage; the "
            "command's own flags (e.g. -p) are passed through untouched."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--ssh-key-file", help="Path to SSH private key")
    parser.add_argument("--git-user-name", help="Git user.name")
    parser.add_argument("--git-user-email", help="Git user.email")
    parser.add_argument("--gh-token", help="GitHub token")
    parser.add_argument("--gpg-key-id", help="GPG key ID for signing")
    parser.add_argument(
        "--build", action="store_true", help="Build from local Dockerfile instead of using pre-built image"
    )
    parser.add_argument(
        "--model", default=None, help="Model name passed to the harness via the LiteLLM proxy (default: local)"
    )
    parser.add_argument(
        "--proxy-url",
        default=None,
        help="LiteLLM proxy base URL. If set, the harness is wired to it. "
        "Defaults to http://host.docker.internal:4000/v1 when a proxy is in use",
    )
    parser.add_argument(
        "--runtime",
        default=None,
        help="OCI isolation runtime for Docker (the isolation seam): "
        "'auto' (default, uses gVisor/runsc when installed else runc), "
        "or a concrete name like 'runsc', 'kata-runtime', 'runc'. "
        "Env: LTD_RUNTIME",
    )
    parser.add_argument(
        "--trusted",
        action="store_true",
        help="Expose the host ~/.claude config READ-WRITE (live bind) instead of a "
        "disposable copy. Governs config exposure only -- not runtime or firewall. "
        "Default (strict) mounts an allowlisted copy so the agent never sees host "
        "credentials and its config writes are discarded on exit. Env: LTD_TRUSTED",
    )
    parser.add_argument(
        "--memory",
        default=None,
        metavar="LIMIT",
        help="Per-cage memory cap passed to docker (default: 2g). Env: LTD_MEMORY",
    )
    parser.add_argument("--shell", metavar="CMD", help="Run a shell command instead of the harness (for testing)")
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="Run the harness with permission prompts enabled (more interruptions, extra safety)",
    )
    # Docker run flags - passed directly to runArgs
    parser.add_argument(
        "-p",
        "--port",
        action="append",
        metavar="HOST:CONTAINER",
        help="Map a port from host to container (can be specified multiple times)",
    )
    parser.add_argument(
        "-v",
        "--volume",
        action="append",
        metavar="DIR",
        help="Mount a host dir into the cage at its OWN path (identity), e.g. "
        "-v /mnt/bertha/app; or HOST:CONTAINER for an explicit target. Repeatable.",
    )
    parser.add_argument(
        "-e",
        "--env",
        action="append",
        metavar="VAR=VALUE",
        help="Set environment variable (can be specified multiple times)",
    )
    # The command to run inside the cage. REMAINDER captures everything after
    # ltd's own options verbatim, so the command's own flags (-p, -v, ...) are
    # NOT stolen by ltd's -p/-v/-e. Empty => default claude (see resolve_command).
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        metavar="command...",
        help='Command to run in the cage, e.g. `claude -p "hi"` or `npx @anthropic/claude`. '
        "Default: claude --dangerously-skip-permissions",
    )
    return parser


def apply_env_defaults(args: argparse.Namespace) -> None:
    """Apply environment variable defaults to args."""
    args.ssh_key_file = args.ssh_key_file or os.environ.get("LTD_SSH_KEY")
    args.git_user_name = args.git_user_name or os.environ.get("LTD_GIT_USER_NAME")
    args.git_user_email = args.git_user_email or os.environ.get("LTD_GIT_USER_EMAIL")
    args.gh_token = args.gh_token or os.environ.get("LTD_GH_TOKEN")
    args.gpg_key_id = args.gpg_key_id or os.environ.get("LTD_GPG_KEY_ID")
    args.model = args.model or os.environ.get("LTD_MODEL") or "local"
    args.proxy_url = args.proxy_url or os.environ.get("LTD_PROXY_URL")
    # Proxy auth: LiteLLM master key. Defaults to the project's literal placeholder.
    args.proxy_api_key = os.environ.get("LTD_PROXY_API_KEY", "lamp-the-djinn")
    # Isolation runtime preference. "auto" picks gVisor when installed, else runc,
    # so stock-Docker hosts (runc-only) keep their existing behavior.
    args.runtime = args.runtime or os.environ.get("LTD_RUNTIME") or "auto"
    # Trust tier for ~/.claude CONFIG exposure (default strict). Opt-in only.
    args.trusted = args.trusted or bool(os.environ.get("LTD_TRUSTED"))
    # Per-cage memory cap. Falls back to the 2g default inside modify_config.
    args.memory = args.memory or os.environ.get("LTD_MEMORY")


def run_devcontainer(
    config_path: Path,
    workspace_dir: Path,
    project_dir: Path,
    command: list[str] | None = None,
    shell_cmd: str | None = None,
    safe_mode: bool = False,
    instance_id: str | None = None,
) -> None:
    """Run the devcontainer with the resolved command.

    The command is whatever the user typed after ltd's own options. Precedence:
    explicit command > --shell CMD > default claude (see resolve_command).

    Each invocation uses a unique instance ID for both the config directory
    and container label, allowing multiple clanker instances to run simultaneously.
    """
    devcontainer_cmd = ["npx", "-y", "@devcontainers/cli"]

    # Use provided instance ID or generate one (for backwards compatibility)
    if instance_id is None:
        instance_id = uuid.uuid4().hex[:12]
    id_label = f"clanker.instance={instance_id}"

    run_cmd = resolve_command(command or [], shell_cmd, safe_mode)

    print(f"Starting devcontainer (instance {instance_id}, command: {' '.join(run_cmd)})...")

    up_cmd = devcontainer_cmd + [
        "up",
        "--workspace-folder",
        str(project_dir),
        "--config",
        str(config_path),
        "--id-label",
        id_label,
    ]

    subprocess.run(up_cmd, check=True)

    exec_cmd = (
        devcontainer_cmd
        + [
            "exec",
            "--workspace-folder",
            str(project_dir),
            "--config",
            str(config_path),
            "--id-label",
            id_label,
        ]
        + run_cmd
    )

    # Use execvp to replace process for clean TTY passthrough
    os.execvp("npx", exec_cmd)


IMAGE_NAME = "ghcr.io/thekevinbot/lamp-the-djinn:latest"


def get_container_info(image_name: str) -> dict:
    """Get container build info from Docker image labels.

    Returns dict with 'build_time' and 'source' keys.
    """
    result = subprocess.run(
        [
            "docker",
            "image",
            "inspect",
            image_name,
            "--format",
            '{{index .Config.Labels "org.opencontainers.image.created"}}|'
            '{{index .Config.Labels "org.opencontainers.image.source.type"}}',
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"build_time": "unknown", "source": "unknown"}

    parts = result.stdout.strip().split("|")
    build_time = parts[0] if parts[0] else "unknown"
    source = parts[1] if len(parts) > 1 and parts[1] else "local"

    return {"build_time": build_time, "source": source}


def print_container_info(image_name: str) -> None:
    """Print container build information on startup."""
    info = get_container_info(image_name)

    source_display = "GitHub Container Registry (ghcr.io)" if info["source"] == "ghcr.io" else "Local build"
    build_time_display = info["build_time"] if info["build_time"] != "unknown" else "Unknown"

    print(f"Container image: {image_name}")
    print(f"  Built: {build_time_display}")
    print(f"  Source: {source_display}")
    print()


def check_docker_accessible() -> None:
    """Check if Docker is running and accessible. Exit with error if not."""
    result = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if result.returncode != 0:
        print(
            "\n"
            "╔════════════════════════════════════════════════════════════════╗\n"
            "║  ERROR: Docker is not running or not accessible               ║\n"
            "╠════════════════════════════════════════════════════════════════╣\n"
            "║  lamp-the-djinn requires Docker to run.                       ║\n"
            "║                                                                ║\n"
            "║  Please ensure:                                               ║\n"
            "║    1. Docker is installed                                     ║\n"
            "║    2. Docker daemon is running                                ║\n"
            "║    3. You have permission to access Docker                    ║\n"
            "║       (try: sudo usermod -aG docker $USER)                    ║\n"
            "╚════════════════════════════════════════════════════════════════╝\n",
            file=sys.stderr,
        )
        sys.exit(1)


def pull_docker_image_if_needed() -> None:
    """Pull the Docker image if not already present."""
    result = subprocess.run(["docker", "image", "inspect", IMAGE_NAME], capture_output=True)
    if result.returncode != 0:
        print("Pulling Docker image...")
        subprocess.run(["docker", "pull", IMAGE_NAME], check=True)


def main() -> None:
    """
    Main entry point - runs a command (the harness) in a sandboxed devcontainer.

    The command is whatever the user types after ltd's own options:
    `ltd [ltd-opts] <command...>`. With no command, defaults to claude.

    Uses embedded devcontainer files from the package.
    With --build, builds from Dockerfile. Without, uses pre-built image.
    """
    parser = create_parser()
    args = parser.parse_args()

    # Detect whether the user explicitly engaged the proxy feature (via flags,
    # env, or by giving an explicit command) BEFORE apply_env_defaults coalesces
    # everything to defaults. This keeps the bare-default case (plain `ltd`, no
    # command, no proxy) behaving exactly as before: no provider env is injected
    # and the proxy URL stays unset, so it just runs claude.
    proxy_engaged = any(
        [
            args.proxy_url is not None,
            args.model is not None,
            bool(args.command),
            os.environ.get("LTD_PROXY_URL"),
            os.environ.get("LTD_MODEL"),
        ]
    )

    apply_env_defaults(args)

    # Record any package-runner command (npx/uvx/etc.) to the cache-freshness
    # manifest so the trusted nightly refresh can warm it ahead of time.
    record_manifest(args.command)

    # Determine the proxy URL. When the proxy is engaged but no explicit URL was
    # given, default to the host bridge gateway (reached via --add-host below).
    proxy_url = args.proxy_url
    if proxy_url is None and proxy_engaged:
        proxy_url = "http://host.docker.internal:4000/v1"

    if args.ssh_key_file and not Path(args.ssh_key_file).exists():
        print(f"Error: SSH key not found at {args.ssh_key_file}", file=sys.stderr)
        sys.exit(1)

    # Check Docker is running before proceeding
    check_docker_accessible()

    # Resolve the isolation runtime against what Docker actually has registered.
    # Default ("auto") yields runc on stock Docker (no --runtime flag added) and
    # only switches to gVisor when runsc is genuinely installed.
    runtime = detect_runtime(args.runtime)
    print(f"Isolation runtime: {runtime}")

    # Pull image if not building locally and image doesn't exist
    if not args.build:
        pull_docker_image_if_needed()
        print_container_info(IMAGE_NAME)
    else:
        print("Container image: Local build (--build flag)")
        print()

    # Capture current working directory (the project to mount)
    project_dir = Path.cwd().resolve()

    # Generate unique instance ID early - used for both cache dir and container ID
    instance_id = uuid.uuid4().hex[:12]

    # Extract embedded devcontainer files to instance-specific cache directory
    # This prevents race conditions when multiple instances run concurrently
    cache_dir = extract_devcontainer_files(instance_id)
    devcontainer_dir = cache_dir / ".devcontainer"
    source_config = devcontainer_dir / "devcontainer.json"

    # Setup runtime directory for SSH config etc (shared, not instance-specific)
    runtime_dir = Path.home() / ".claude" / "lamp-the-djinn-runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    # Ensure the writable credential-persistence dir exists on the host before
    # we bind-mount it into the cage. Contents are readable by the untrusted
    # agent, so only scoped/revocable credentials belong here (see README).
    auth_dir = Path.home() / ".cache" / "lamp-the-djinn" / "auth"
    auth_dir.mkdir(parents=True, exist_ok=True)

    # Strict mode (default): stage a disposable, allowlisted copy of the host
    # ~/.claude config into this instance's cache dir and mount THAT instead of
    # the live host config. Trusted mode skips this and binds the host directly.
    claude_stage_dir: Path | None = None
    if not args.trusted:
        claude_stage_dir = cache_dir / "claude-config-stage"
        stage_claude_config(Path.home(), claude_stage_dir)

    # Harness adapter: pi configures via models.json (not OPENAI_BASE_URL), so when
    # the proxy is engaged and the command is pi, stage a pi config whose default
    # provider points at the proxy, and mount it at the cage's ~/.pi/agent.
    pi_stage_dir: Path | None = None
    if proxy_url and command_is_pi(args.command):
        pi_stage_dir = cache_dir / "pi-agent-stage"
        stage_pi_config(pi_stage_dir, proxy_url, args.model or "local", args.proxy_api_key)

    # Load and modify config
    config = json.loads(source_config.read_text())
    config = modify_config(
        config,
        args,
        runtime_dir,
        devcontainer_dir,
        project_dir,
        proxy_url=proxy_url,
        model=args.model,
        proxy_api_key=args.proxy_api_key,
        runtime=runtime,
        trusted=args.trusted,
        claude_stage_dir=claude_stage_dir,
        pi_stage_dir=pi_stage_dir,
    )

    # Write modified config back to the temp devcontainer dir
    runtime_config = devcontainer_dir / "devcontainer.json"
    runtime_config.write_text(json.dumps(config, indent=2))

    run_devcontainer(
        runtime_config,
        cache_dir,
        project_dir,
        args.command,
        args.shell,
        args.safe_mode,
        instance_id,
    )


def shell_remote() -> None:
    """Alias for main() - for lamp-the-djinn-remote entry point."""
    main()
