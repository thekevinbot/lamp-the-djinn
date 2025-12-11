# Session Summary: Clanker CI/CD and Docker Improvements

## Latest Changes (This Session)

### Converted to Proper Python Package ✅
Clanker is now a proper Python package installable via `uvx` from GitHub.

**Package structure:**
```
src/clanker/
├── __init__.py
└── cli.py          # main() and install() entry points
```

**Entry points:**
- `clanker` → runs claude-code locally (expects .devcontainer/ in cwd or installed)
- `clanker-install` → downloads from GitHub, then runs clanker

### Usage

**Run directly from GitHub with uvx:**
```bash
uvx --from git+https://github.com/clankerbot/clanker clanker-install \
    --ssh-key-file ~/.ssh/id_ed25519_clanker \
    --git-user-name clankerbot \
    --git-user-email "248217931+clankerbot@users.noreply.github.com" \
    --gpg-key-id C567F8478F289CC4
```

**Local development (in clanker repo):**
```bash
cd ~/clanker
uvx --from . clanker --ssh-key-file ~/.ssh/id_ed25519_clanker
# OR
uv run clanker --ssh-key-file ~/.ssh/id_ed25519_clanker
```

**Updated fish function (`cc`):**
```fish
function cc
    uvx --from git+https://github.com/clankerbot/clanker clanker-install \
        --ssh-key-file ~/.ssh/id_ed25519_clanker \
        --git-user-name clankerbot \
        --git-user-email "248217931+clankerbot@users.noreply.github.com" \
        --gpg-key-id C567F8478F289CC4
end
```

### CLI Arguments

| Argument | Env Variable | Description |
|----------|--------------|-------------|
| `--ssh-key-file` | `CLANKER_SSH_KEY` | Path to SSH private key |
| `--git-user-name` | `CLANKER_GIT_USER_NAME` | Git user.name |
| `--git-user-email` | `CLANKER_GIT_USER_EMAIL` | Git user.email |
| `--gh-token` | `CLANKER_GH_TOKEN` | GitHub token |
| `--gpg-key-id` | `CLANKER_GPG_KEY_ID` | GPG key ID for signing |

Any additional arguments are passed through to `claude`.

---

## Previous Session Work

### 1. Container Tools - All Working ✅
- **uv/uvx**: Fixed installation using official `COPY --from=ghcr.io/astral-sh/uv:latest`
- **pnpm**: Installed via `corepack enable && corepack prepare pnpm@latest --activate`
- **Docker socket**: Added `--group-add` to runArgs for socket access

### 2. CI/CD Workflows ✅
- **test-container.yml**: Tests all tools (uv, pnpm, docker, claude, etc.) on every push
- **docker-publish.yml**: Fixed cache busting - now includes Dockerfile hash in cache key
- **lint.yml**: ShellCheck (passing), Hadolint (warnings only, `continue-on-error: true`)

### 3. Docker Socket Access
The CLI auto-detects the host's docker socket group ID and adds `--group-add <GID>` to runArgs dynamically.

**Important:** Container must be restarted after config changes take effect. The devcontainer CLI reuses existing containers.

### 4. GitHub Auth Issue (Not Fixed)
- `gh` CLI needs PAT with scopes: `repo`, `workflow`, `write:packages`
- Run: `gh auth login --with-token <<< "ghp_yourtoken"`

## Remaining TODOs

From `/workspace/TODO.md`:

```markdown
## CI/CD
- [ ] Automerge on CI check pass - configure GitHub branch protection + auto-merge
- [ ] Hadolint: review output and fix/ignore specific rules (currently non-blocking)

## GitHub Auth
- [ ] Create PAT for clankerbot - need token with scopes: repo, workflow, write:packages
- [ ] Run `gh auth login` with clankerbot token

## Blog Post (separate repo)
- [ ] Add "Baked-In Tools" section: pnpm, uv, Playwright, Docker socket
```

## Key Files

| File | Purpose |
|------|---------|
| `src/clanker/cli.py` | CLI entry points (main, install) |
| `pyproject.toml` | Package config with entry points |
| `.devcontainer/devcontainer.json` | Base devcontainer config |
| `.devcontainer/Dockerfile` | Container image with uv, pnpm, etc. |
| `.devcontainer/init-firewall.sh` | Network allowlist setup |
| `.devcontainer/whitelisted-domains.txt` | Allowed domains (33 total) |

## How to Set Up Automerge

1. Go to repo Settings → Branches → Add rule for `main`
2. Enable "Require status checks to pass before merging"
3. Select both "Test Container" and "Lint" workflows
4. Enable "Allow auto-merge" in repo Settings → General
