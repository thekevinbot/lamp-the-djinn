#!/bin/bash
set -e

CLAUDE_DIR="$HOME/.claude/.devcontainer"
CONFIG="$CLAUDE_DIR/devcontainer.json"

# Create directories
mkdir -p "$HOME/.claude/commands"
mkdir -p "$HOME/.claude/hooks"

# Symlink settings.json from clanker repo
if [ ! -e "$HOME/.claude/settings.json" ]; then
    ln -s "$HOME/.claude/clanker/config/settings.json" "$HOME/.claude/settings.json"
    echo "Created settings.json symlink"
elif [ ! -L "$HOME/.claude/settings.json" ]; then
    echo "Warning: ~/.claude/settings.json exists but is not a symlink"
    echo "Consider backing it up and removing it to use clanker's settings"
fi

# Symlink hook scripts from clanker repo
for hook in "$HOME/.claude/clanker/hooks"/*.sh; do
    hook_name=$(basename "$hook")
    if [ ! -e "$HOME/.claude/hooks/$hook_name" ]; then
        ln -s "$hook" "$HOME/.claude/hooks/$hook_name"
        echo "Created hook symlink: $hook_name"
    fi
done

# Download devcontainer files if missing
if [ ! -f "$CONFIG" ]; then
    mkdir -p "$CLAUDE_DIR"
    curl -fsSL https://raw.githubusercontent.com/anthropics/claude-code/main/.devcontainer/devcontainer.json -o "$CONFIG"
    curl -fsSL https://raw.githubusercontent.com/anthropics/claude-code/main/.devcontainer/Dockerfile -o "$CLAUDE_DIR/Dockerfile"
    curl -fsSL https://raw.githubusercontent.com/anthropics/claude-code/main/.devcontainer/init-firewall.sh -o "$CLAUDE_DIR/init-firewall.sh"
fi

# Replace .claude docker volume with bind mount
if grep -q 'claude-code-config.*type=volume' "$CONFIG"; then
    tmp=$(mktemp)
    sed 's|source=claude-code-config-${devcontainerId},target=/home/node/.claude,type=volume|source=${localEnv:HOME}/.claude,target=/home/node/.claude,type=bind|' "$CONFIG" > "$tmp"
    mv "$tmp" "$CONFIG"
fi

# Run devcontainer with stdin attached
if ! npx -y @devcontainers/cli exec --workspace-folder . --config "$CONFIG" claude --dangerously-skip-permissions 2>/dev/null </dev/tty; then
    echo "Starting devcontainer..."
    npx -y @devcontainers/cli up --workspace-folder . --config "$CONFIG" \
    && npx -y @devcontainers/cli exec --workspace-folder . --config "$CONFIG" claude --dangerously-skip-permissions </dev/tty
fi
