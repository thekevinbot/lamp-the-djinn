"""
A single-file `-v` mount under the cage home must leave its Docker-created parent
directories WRITABLE by the cage user, against the DEPLOYED `ltd`.

THE BUG THIS PINS. The natural way to hand pi just its provider config without
leaking the sibling `auth.json` is to mount one file:

    ltd -v ~/.pi/agent/models.json  npx -y @earendil-works/pi-coding-agent ...

ltd home-remaps that to `-v /home/node/.pi/agent/models.json`. But Docker, asked
to bind-mount a FILE whose parent directories do not exist in the image, creates
the whole parent chain (`/home/node/.pi`, `/home/node/.pi/agent`) owned by ROOT.
The cage runs as `node` (uid 1000), so pi's very first action -- creating its
session dir, `mkdir /home/node/.pi/agent/sessions/<id>` -- dies with
`EACCES: permission denied`. Mounting the whole `~/.pi` DIRECTORY sidesteps this
(the mount point itself inherits the host dir's ownership) but drags `auth.json`
into the cage, defeating the point of scoping. So the scoped single-file mount
MUST work: the parent dirs ltd causes Docker to create have to end up owned by
the cage user.

WHY A PURE FILESYSTEM PROBE (no model, no proxy). The fault is ownership of the
auto-created parents, nothing to do with a model turn. So this cell mounts a
single file under `$HOME` and then, in the cage, tries the exact operation pi
fails on -- `mkdir -p <home>/agent/sessions/probe` -- and asserts it succeeds.
A bare `ltd ... <cmd>` with no `--model`/`LTD_*` engages no proxy, so this needs
only Docker + a deployed ltd. It is RED on the shipped binary today (the mkdir
hits EACCES) and goes GREEN only once ltd makes those parents node-owned.

DEPLOY SKEW / OWN THE PRECONDITION -- same discipline as the rest of tests/e2e:
we exercise the installed `ltd` CONSOLE SCRIPT (never `uv run` against `src/`),
and we stage the triggering state ourselves under an isolated dir beneath the
REAL `$HOME` (the home-remap only fires for a `$HOME`-relative path; a /tmp path
would mount path-identity and pass even on the broken binary). Nothing here
depends on the developer's real `~/.pi`.

ENVIRONMENT -- local-only e2e (needs Docker; never runs in CI). `LTD_BIN`
overrides which deployed ltd is exercised. The cell skips loudly when Docker or a
deployed ltd is absent.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.e2e]

# The mount-and-probe command typed exactly as a user would: create the session
# dir pi creates, inside the agent dir whose parent was auto-made by the mount.
SENTINEL = "MKDIR_OK"


def _ltd_binary() -> str | None:
    """Resolve the DEPLOYED `ltd`, excluding the venv shadow. See agent_matrix_test.py."""
    override = os.environ.get("LTD_BIN")
    if override:
        return override
    venv_bin = (Path(sys.prefix) / "bin").resolve()
    search = os.pathsep.join(
        p for p in os.environ.get("PATH", "").split(os.pathsep) if p and Path(p).resolve() != venv_bin
    )
    return shutil.which("ltd", path=search) or shutil.which("lamp-the-djinn", path=search)


def _require_infra() -> str:
    """Skip unless Docker and a deployed ltd are present (no proxy needed here).
    Returns the ltd binary path and prints which artifact will run."""
    if shutil.which("docker") is None:
        pytest.skip("docker not available")
    ltd = _ltd_binary()
    if ltd is None:
        pytest.skip("ltd/lamp-the-djinn console script not installed on PATH (set LTD_BIN)")
    # A wrong-binary e2e is how the EROFS bug shipped green; always say which ran.
    print(f"\n[e2e] exercising deployed artifact: {ltd}")
    return ltd


@pytest.fixture
def reap_cages():
    """Reap ONLY the cage containers this test creates (see agent_matrix_test.py)."""

    def snapshot() -> set[str]:
        r = subprocess.run(
            ["docker", "ps", "-aq", "--filter", "label=clanker.instance"],
            capture_output=True,
            text=True,
        )
        return set(r.stdout.split())

    before = snapshot()
    yield
    new = snapshot() - before
    for cid in new:
        subprocess.run(["docker", "rm", "-f", cid], capture_output=True, text=True)
    if new:
        print(f"[e2e] reaped {len(new)} cage container(s): {sorted(new)}")


def describe_mounting_a_single_file_under_the_cage_home():
    """`ltd -v ~/<dir>/agent/models.json <cmd>`: the auto-created parents must be
    writable by the cage user, or pi cannot make its session dir."""

    def it_leaves_the_created_parent_dirs_writable_by_the_cage_user(reap_cages):
        ltd = _require_infra()
        # MUST live under $HOME: only a home-relative bare `-v` triggers ltd's
        # host->cage HOME remap, which is what makes Docker create the parents.
        probe = f".ltd-e2e-mount-probe-{os.getpid()}"
        cfg_root = Path.home() / probe
        host_file = cfg_root / "agent" / "models.json"
        try:
            host_file.parent.mkdir(parents=True, exist_ok=True)
            host_file.write_text("{}\n")  # any bytes -- a real file, so Docker mounts a file not a dir

            # ltd home-remaps the bare `-v` to /home/node/<probe>/agent/models.json,
            # so the cage path mirrors the host path under the cage user's HOME.
            cage_agent_dir = f"/home/node/{probe}/agent"
            # The exact thing pi does on session create, reduced to its essence.
            mkdir_probe = f"mkdir -p {cage_agent_dir}/sessions/probe && echo {SENTINEL}"

            argv = [
                ltd,
                "--runtime",
                "runc",
                "-v",
                str(host_file),  # bare, home-relative, single FILE -> root-owned parents
                "sh",
                "-c",
                mkdir_probe,
            ]
            result = subprocess.run(
                argv,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                env={**os.environ},
                timeout=600,
            )
        finally:
            shutil.rmtree(cfg_root, ignore_errors=True)

        combined = f"{result.stdout}\n{result.stderr}"
        denied = "permission denied" in combined.lower() or "eacces" in combined.lower()
        assert SENTINEL in result.stdout, (
            "scoped single-file mount left the auto-created parent dir non-writable by the cage "
            f"user -- `mkdir {cage_agent_dir}/sessions/probe` did not succeed (rc={result.returncode}, "
            f"permission-denied seen: {denied}). This is the EACCES that breaks "
            f"`ltd -v ~/.pi/agent/models.json npx ... pi`.\n{combined}"
        )
