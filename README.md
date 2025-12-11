# ClankerCage

Devcontainer setup and testing infrastructure for Claude Code.

## Overview

ClankerCage provides:
- **Easy Setup** - One-command devcontainer installation
- **Testing Infrastructure** - Automated validation suite
- **Helper Scripts** - Utilities for setup and testing
- **Plugin Ecosystem** - Works with scribble-pad and browser-fallback plugins

## Quick Setup

### Recommended: Install via uvx (safer)

```bash
uvx clankercage
```

This uses Python's package manager with integrity verification. Install [uv](https://docs.astral.sh/uv/) first if needed.

### Alternative: curl|bash (convenience)

> **Security Warning:** The `curl|bash` pattern executes remote code without verification.
> If the repository is compromised, your system could be compromised. For security-conscious
> users, we recommend reviewing the script first or using the `uvx` method above.

```bash
# Review the script first (recommended):
curl -s https://raw.githubusercontent.com/clankerbot/clankercage/main/scripts/claude-code.sh | less

# Then run it:
bash <(curl -s https://raw.githubusercontent.com/clankerbot/clankercage/main/scripts/claude-code.sh)
```

This script:
- Pulls the pre-built Docker image from GitHub Container Registry
- Downloads devcontainer configuration files
- Converts Claude Code's docker volume to bind mount
- Starts the devcontainer with proper permissions
- Makes `~/.claude` accessible from host and container

## Directory Structure

After running the setup script:

```
~/.claude/
├── .devcontainer/           # Configuration (managed by setup script)
│   ├── devcontainer.json    # Downloaded from repo
│   └── ssh_config           # Generated with your SSH key path
└── .allowed-browser-domains # Approved domains for browser automation
```

Clean and minimal - just the devcontainer config.

## Installation

### Option 1: uvx (Recommended)

```bash
uvx clankercage
```

### Option 2: curl|bash

See [security warning above](#alternative-curlbash-convenience) before using this method.

```bash
bash <(curl -s https://raw.githubusercontent.com/clankerbot/clankercage/main/scripts/claude-code.sh)
```

## How It Works

### Devcontainer Setup

ClankerCage modifies the default Claude Code devcontainer to use a bind mount instead of a volume:

**Before:**
```json
{
  "mounts": [
    "source=claude-code-config-${devcontainerId},target=/home/node/.claude,type=volume"
  ]
}
```

**After:**
```json
{
  "mounts": [
    "source=${localEnv:HOME}/.claude,target=/home/node/.claude,type=bind"
  ]
}
```

This makes `~/.claude` accessible from both host and container, enabling:
- Easy plugin installation
- Portable configuration across machines
- Direct file editing from host
- No docker volume complexity

### Domain Approval System

The container runs a firewall that blocks external URLs by default. Browser automation plugins must get user approval before accessing new domains.

**How it works:**
1. Plugin calls `approve-domain.sh <domain>` before navigating
2. If domain is new, user is prompted: `Allow access to example.com? [y/N]`
3. If approved, domain is added to `~/.claude/.allowed-browser-domains` and firewall is updated
4. Subsequent requests to the same domain are auto-approved

**Usage from plugins:**

```bash
# Check and prompt for approval (interactive)
scripts/approve-domain.sh example.com

# Check only, no prompt (for pre-flight checks)
scripts/approve-domain.sh example.com --check-only
```

**Exit codes:**
- `0` - Domain is approved
- `1` - Domain was denied or error
- `2` - Invalid usage

**Environment variables:**
- `ALLOWED_DOMAINS_FILE` - Override storage location (default: `~/.claude/.allowed-browser-domains`)

**Container-level scripts:**
- `/usr/local/bin/add-domain-to-firewall.sh <domain>` - Resolves domain and adds IPs to firewall ipset (requires sudo, called automatically by approve-domain.sh)

## Setup on New Machine

```bash
# Recommended: use uvx
uvx clankercage

# Or use curl|bash (see security warning in Quick Setup section)
bash <(curl -s https://raw.githubusercontent.com/clankerbot/clankercage/main/scripts/claude-code.sh)
```

Done! Copy `~/.claude/` to bring your configuration if desired.

## Troubleshooting

**SSH not working for private repos?**
- Ensure your SSH agent is running on the host: `eval "$(ssh-agent -s)"`
- Add your key: `ssh-add ~/.ssh/id_ed25519`
- Verify with: `ssh-add -l`
- The setup script automatically forwards your SSH agent to the container
- Test inside container: `ssh -T git@github.com`

**Container won't start?**
- Check Docker is running
- Try: `docker system prune` (removes old containers)
- Verify devcontainer config: `cat ~/.claude/.devcontainer/devcontainer.json`

**Want to run tests?**
- Clone the repo: `git clone https://github.com/clankerbot/clankercage.git`
- Run tests: `bash clankercage/scripts/run-tests.sh`

**UV hardlink warning?**
If you see `warning: Failed to hardlink files; falling back to full copy`:
- This is harmless - it occurs when uv's cache is on a different filesystem than your project
- To suppress: `export UV_LINK_MODE=copy`
- Or add to your shell profile for permanent fix


## Development

### Setting Up Git Hooks

Enable pre-commit hooks to run unit tests before each commit:

```bash
git config core.hooksPath .githooks
```

This runs unit tests automatically. Skip with `git commit --no-verify` for WIP commits.

### Adding New Tests

1. Create test script in `tests/` with format: `##-test-name.sh`
2. Follow existing test structure (exit 0 for pass, exit 1 for fail)
3. Make executable: `chmod +x tests/##-test-name.sh`
4. Test runner will automatically pick it up

### Updating Setup Script

1. Edit `scripts/claude-code.sh`
2. Test locally
3. Commit and push to repo

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_DOMAINS_FILE` | `~/.claude/.allowed-browser-domains` | Path to user domain whitelist |
| `CLAUDE_CONFIG_DIR` | `/home/node/.claude` | Claude configuration directory |
| `NODE_OPTIONS` | `--max-old-space-size=4096` | Node.js memory limit (4GB) |
| `DEVCONTAINER` | `true` | Indicates running in devcontainer |
| `SHELL` | `/bin/zsh` | Default shell |
| `EDITOR` / `VISUAL` | `nano` | Default text editor |
| `POWERLEVEL9K_DISABLE_GITSTATUS` | `true` | Disables git status in prompt (performance) |

## Architecture Principles

1. **Minimal Core** - ClankerCage handles only devcontainer setup
2. **Plugin Ecosystem** - Extended functionality via plugins
3. **Bind Mount Strategy** - Single `~/.claude` mount for simplicity
4. **Portable Configuration** - Git-tracked setup works across machines
5. **Test-Driven** - Automated tests verify everything works

## License

MIT
