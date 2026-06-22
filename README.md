# lamp-the-djinn

A sandbox for running Claude Code with full autonomy, without risking your system.

[Read the blog post](https://thekevinscott.com/sandbox-for-claude-code/) for more context.

## What It Solves

You want Claude Code to run with `--dangerously-skip-permissions` so it can work without constant interruptions. But you don't want it [deleting your hard drive](https://www.tomshardware.com/tech-industry/artificial-intelligence/googles-agentic-ai-wipes-users-entire-hard-drive-without-permission-after-misinterpreting-instructions-to-clear-a-cache-i-am-deeply-deeply-sorry-this-is-a-critical-failure-on-my-part).

lamp-the-djinn runs Claude Code inside a Docker container. The container mounts your project directory, so Claude can read and write files. But it can't touch anything else on your system. A network firewall blocks outbound traffic by default.

## Quick Start

```bash
uvx --from git+https://github.com/thekevinbot/lamp-the-djinn lamp-the-djinn
```

## Usage

The command after ltd's own options is what runs inside the cage:
`ltd [ltd-opts] <command...>`. The command's own flags are passed through
untouched (ltd's option parsing stops at the first command token).

```bash
ltd                          # bare: runs `claude --dangerously-skip-permissions`
ltd claude -p "fix the bug"  # the -p goes to claude, not ltd
ltd npx @anthropic/claude    # run an agent straight from npm
ltd --model glm-5.2 aider    # route a different harness through the proxy
ltd --safe-mode              # bare claude with permission prompts on
```

When you pass a command, a `--model`, or a `--proxy-url` (or set `LTD_MODEL` /
`LTD_PROXY_URL`), ltd wires the harness to a LiteLLM proxy on the host and
injects both provider env families (`OPENAI_*` and `ANTHROPIC_*`) so the agent
finds whichever it speaks. Bare `ltd` with none of these stays fully
backward-compatible: no proxy, just claude.

## Configuration

For a dedicated GitHub identity (recommended for distinguishing AI commits from your own):

```bash
uvx --from git+https://github.com/thekevinbot/lamp-the-djinn lamp-the-djinn \
  --ssh-key-file ~/.ssh/id_ed25519_yourbot \
  --git-user-name yourbot \
  --git-user-email "yourbot@users.noreply.github.com" \
  --gpg-key-id YOUR_GPG_KEY_ID \
  --gh-token ghp_your_github_token
```

## How It Works

- **Container isolation**: Claude runs in Docker, can only access the mounted project directory
- **Network firewall**: Outbound traffic blocked by default; whitelisted domains (npm, GitHub, PyPI, etc.) allowed
- **Git as undo**: Lean on `git reset --hard` as your escape hatch

## Credential Persistence

To let harness sessions survive across runs (e.g. an OAuth token an agent
writes after `login`), ltd bind-mounts a **writable** host directory
(`~/.cache/lamp-the-djinn/auth`) into the cage at
`/home/node/.config/ltd-auth`.

**Principle: anything in this volume is readable by the untrusted agent.**
The agent has full read access to everything you persist here, so treat it as
exposed. Concretely:

- **Persist only scoped, revocable credentials** here — e.g. a session token you
  can invalidate, never a long-lived root credential.
- **The model API key never enters the cage.** It stays in the LiteLLM proxy on
  the host; the cage only ever sees the proxy's base URL and a local proxy key.
- **Keep your primary git identity out.** Push host-side, or supply a
  fine-grained, single-repo, revocable PAT — not your account-wide SSH key or a
  broad GitHub token.

The existing `~/.claude` mount stays **read-only**, so the agent can read your
settings/hooks but cannot modify them or exfiltrate keys through them.

## Forking and Customizing

This is designed to be forked. Make it your own.

**Adding dependencies**: Edit the `Dockerfile` to add tools you need. Use Claude Code to help:

```
Add playwright and ffmpeg to the Dockerfile
```

## License

MIT
