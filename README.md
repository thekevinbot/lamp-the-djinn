# Clanker

Devcontainer setup and testing infrastructure for Claude Code.

## Overview

Clanker provides:
- **Easy Setup** - One-command devcontainer installation
- **Testing Infrastructure** - Automated validation suite
- **Helper Scripts** - Utilities for setup and testing
- **Plugin Ecosystem** - Works with scribble-pad and browser-fallback plugins

## Quick Setup

```bash
bash ~/.claude/clanker/scripts/claude-code.sh
```

This script:
- Downloads devcontainer configuration files
- Converts Claude Code's docker volume to bind mount
- Starts the devcontainer with proper permissions
- Makes `~/.claude` accessible from host and container

## Directory Structure

```
~/.claude/
├── .devcontainer/           # Docker configuration (downloaded by setup script)
│   ├── devcontainer.json
│   ├── Dockerfile
│   └── init-firewall.sh
└── clanker/                 # This repo
    ├── scripts/
    │   ├── claude-code.sh   # Setup script
    │   └── test-*.sh        # Integration tests
    ├── tests/               # Test suite
    ├── records/             # Context storage (NOT in git)
    └── README.md
```

## Plugin Architecture

Clanker works with Claude Code plugins for extended functionality:

### [scribble-pad](https://github.com/thekevinscott/scribble-pad)
Context management plugin:
- `/save [name]` - Save conversation context
- `/load [name]` - Load previous conversation
- Auto-load on session start

### [browser-fallback](https://github.com/thekevinscott/browser-fallback)
Browser automation plugin:
- `/browse [url]` - Automate browser with Playwright
- Automatic WebFetch fallback hook
- Handles JavaScript-heavy sites

## Installation

### 1. Install Clanker

```bash
# Clone this repo
git clone https://github.com/clankerbot/clanker.git ~/.claude/clanker

# Run setup script
bash ~/.claude/clanker/scripts/claude-code.sh
```

### 2. Install Plugins (Optional)

```bash
# Clone plugins
git clone https://github.com/thekevinscott/scribble-pad.git ~/code/claude-plugins/scribble-pad
git clone https://github.com/thekevinscott/browser-fallback.git ~/code/claude-plugins/browser-fallback

# Add local marketplace
/plugin marketplace add ~/code/claude-plugins

# Install plugins
/plugin install scribble-pad@local
/plugin install browser-fallback@local
```

## Testing

Run automated test suite:

```bash
# Fast tests (run on host)
bash ~/.claude/clanker/scripts/run-tests.sh

# Integration tests (starts container)
bash ~/.claude/clanker/scripts/test-container.sh

# Python tests (if installed)
cd ~/.claude/clanker
make test
```

**Fast Tests** (validate host setup):
- ✓ Directory structure exists
- ✓ Scripts are executable
- ✓ Files are writable

**Integration Test** (validates container):
- ✓ devcontainer.json is valid
- ✓ Container starts successfully
- ✓ Bind mount works correctly
- ✓ Tests pass inside container

## How It Works

### Devcontainer Setup

Clanker modifies the default Claude Code devcontainer to use a bind mount instead of a volume:

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

### Plugin Integration

Plugins use the Claude Code plugin system:
- Commands defined in `commands/*.md`
- Hooks defined in `hooks/hooks.json`
- Scripts in `scripts/` directory

Clanker provides the infrastructure; plugins provide the functionality.

## Setup on New Machine

1. Copy `~/.claude/` from existing machine (or clone this repo)
2. Run `scripts/claude-code.sh` to setup devcontainer
3. Install plugins if desired
4. All your configuration comes with you

## Troubleshooting

**Container won't start?**
- Check Docker is running
- Try: `docker system prune` (removes old containers)
- Verify devcontainer config: `cat ~/.claude/.devcontainer/devcontainer.json`

**Tests failing?**
- Fast tests run on host - should always pass
- Integration test requires Docker
- Check scripts are executable: `chmod +x ~/.claude/clanker/scripts/*.sh`

**Plugins not loading?**
- Run: `/plugin list` to see installed plugins
- Check plugin directories exist
- Verify `plugin.json` is valid JSON

## Development

### Adding New Tests

1. Create test script in `tests/` with format: `##-test-name.sh`
2. Follow existing test structure (exit 0 for pass, exit 1 for fail)
3. Make executable: `chmod +x tests/##-test-name.sh`
4. Test runner will automatically pick it up

### Updating Setup Script

1. Edit `scripts/claude-code.sh`
2. Test locally
3. Commit and push to repo

## Architecture Principles

1. **Minimal Core** - Clanker handles only devcontainer setup
2. **Plugin Ecosystem** - Extended functionality via plugins
3. **Bind Mount Strategy** - Single `~/.claude` mount for simplicity
4. **Portable Configuration** - Git-tracked setup works across machines
5. **Test-Driven** - Automated tests verify everything works

## License

MIT
