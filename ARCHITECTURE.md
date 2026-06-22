# Architecture

lamp-the-djinn runs an untrusted coding agent ("the harness") inside a
disposable cage. The design has two seams so that *what isolates the agent* and
*what model serves it* can each vary independently behind a single interface.

## Isolation seam

One question: how strongly is the container isolated from the host? The CLI
resolves an OCI runtime and hands it to Docker; nothing else in the code path
changes.

- **local / gVisor (default)** — `detect_runtime("auto")` uses gVisor's `runsc`
  when it is registered with Docker, otherwise falls back to stock `runc`. Hosts
  without gVisor keep their existing behavior unchanged.
- **kata** — `--runtime kata-runtime` selects a VM-backed runtime when installed.
- **fly** — the same cage shipped to a remote Fly.io machine (see `fly/`).

A concrete runtime that Docker does not report falls back to `runc` with a
warning, so a run never hard-fails on a missing runtime. See
`detect_runtime` in `src/lamp_the_djinn/cli.py`.

## Provider seam

One question: which model serves a request? Every harness talks to exactly one
local endpoint — the **LiteLLM proxy** — and never to a provider directly. The
proxy abstracts the backend:

- `--model local` → a local llama.cpp server.
- `--model <hosted>` → OpenRouter (or any LiteLLM-mapped backend).

Two wire formats are supported by `harness.provider_env`: OpenAI
(`OPENAI_BASE_URL`/`OPENAI_API_KEY`, used by Codex/Aider/custom) and Anthropic
(`ANTHROPIC_BASE_URL`/`ANTHROPIC_AUTH_TOKEN`, used by Claude Code). The harness
only ever sees a base URL, a key, and a model name.

## Harness model

A harness is the agent program run inside the cage (Claude Code, Codex, Aider,
or a raw command). Harnesses are fetched with `npx`/`uvx` at runtime. To keep
that fetch from being an egress hole:

- A **trusted nightly refresh** runs on the *host*
  (`scripts/refresh-harness-cache.sh`) and pre-fetches packages into
  `~/.cache/lamp-the-djinn/harness-cache` with a cooldown window.
- The cage mounts that cache **read-only**; in-container `UV_CACHE_DIR` and
  `npm_config_cache` point at it. The agent uses pre-vetted packages instead of
  downloading fresh ones.

## Load-bearing controls

The security model rests on four properties, not on any single fence:

1. **Default-deny egress** — outbound traffic is blocked except for a small
   allowlist; the harness reaches models only through the proxy.
2. **No credentials in the cage** — secrets live in the host's gitignored
   `.env`; the proxy holds the real keys, the agent gets only a placeholder
   proxy token.
3. **Ephemeral** — the cage is disposable; `git reset --hard` is the undo.
4. **Diff review** — the human reviews the produced diff before it leaves.
