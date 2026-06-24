# Roadmap

## Done

- **Rename** to lamp-the-djinn (package `src/lamp_the_djinn/`, `ltd` entrypoint).
- **Provider seam** — harnesses talk only to the LiteLLM proxy; OpenAI and
  Anthropic wire formats wired via `harness.provider_env`.
- **Harness-agnostic entrypoint** — `--harness` accepts a known name (claude,
  codex, aider) or a raw command; auto-configured against the proxy.
- **Isolation seam scaffolding** — `detect_runtime` resolves auto/runsc/
  kata-runtime/runc against what Docker reports, with safe fallback to runc.
- **Read-only harness cache** — host-side nightly refresh + read-only mount.

## Next / unverified

- **Real-container firewall verification** — confirm default-deny egress and
  proxy-only reachability inside an actual running container, not just unit
  tests. Also verify uv/npm fail gracefully against a read-only cache when a
  package was not pre-fetched.
- **gVisor / kata install** — document and verify install paths; the seam is
  scaffolded but the stronger runtimes are not yet validated end to end.
- **Fly deploy** — finish and verify the remote-machine path (`fly/`).
- **More harness adapters** — broaden beyond claude/codex/aider; pin/validate
  the auto-approve flags, which drift between releases.
