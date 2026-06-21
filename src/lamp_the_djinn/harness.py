"""Harness registry: the coding agent that runs *inside* the cage.

A "harness" is the agent program executed in the sandboxed devcontainer (Claude
Code, Codex, Aider, or an arbitrary command). lamp-the-djinn is harness-agnostic:
the agent is selectable and auto-configured to talk to the LiteLLM proxy on the
host.

Provider seam
-------------
Every harness talks to ONE local endpoint -- the LiteLLM proxy -- never to a
provider directly. The proxy abstracts away *which* backend serves a request:
``--model local`` may hit llama.cpp on a local box, while ``--model glm-5.2``
fans out to OpenRouter. The harness neither knows nor cares; it only sees a
base URL and an API key.

Two wire formats are in play:

* ``provider="openai"`` harnesses (Codex, Aider, custom) speak the OpenAI
  chat-completions format and use the proxy's ``/v1`` endpoint.
* ``provider="anthropic"`` harnesses (Claude Code) speak the Anthropic Messages
  format. LiteLLM must therefore expose its *anthropic-format* passthrough
  endpoint for these; ``ANTHROPIC_BASE_URL`` should point at that endpoint so
  Claude Code's native ``/v1/messages`` calls are translated to whatever backend
  the chosen model maps to.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Harness:
    """A coding agent that can run inside the cage.

    Attributes:
        name: Short identifier (registry key).
        run: In-container command, auto-approve / non-interactive variant.
        run_safe: Optional variant *without* auto-approve (permission prompts on).
            ``None`` means the harness has no distinct safe mode.
        provider: Wire format / credential shape: "openai" or "anthropic".
        description: Human-readable one-liner.
    """

    name: str
    run: list[str]
    provider: str
    description: str = ""
    run_safe: list[str] | None = None


# Registry of known harnesses. Add new agents here.
HARNESSES: dict[str, Harness] = {
    "claude": Harness(
        name="claude",
        run=["claude", "--dangerously-skip-permissions"],
        run_safe=["claude"],
        provider="anthropic",
        description="Anthropic Claude Code (default).",
    ),
    "codex": Harness(
        name="codex",
        # Best-effort flags: `codex exec --full-auto` runs non-interactively with
        # auto-approval. Exact flag names drift between Codex releases -- tune if
        # the agent errors on startup (e.g. `--dangerously-bypass-approvals`).
        run=["npx", "-y", "@openai/codex", "exec", "--full-auto"],
        provider="openai",
        description="OpenAI Codex CLI.",
    ),
    "aider": Harness(
        name="aider",
        run=["uvx", "aider", "--yes-always"],
        provider="openai",
        description="Aider pair-programming agent.",
    ),
}


def provider_env(h: Harness, proxy_url: str, model: str, api_key: str) -> dict[str, str]:
    """Build the env vars that point a harness at the LiteLLM proxy.

    The proxy abstracts local-llama-vs-OpenRouter behind one endpoint, so the
    same three knobs (base URL, key, model) configure every backend. For
    ``provider="anthropic"`` the ``proxy_url`` must be LiteLLM's anthropic-format
    endpoint (see module docstring).
    """
    if h.provider == "openai":
        return {
            "OPENAI_BASE_URL": proxy_url,
            "OPENAI_API_KEY": api_key,
            "OPENAI_MODEL": model,
        }
    if h.provider == "anthropic":
        return {
            "ANTHROPIC_BASE_URL": proxy_url,
            "ANTHROPIC_AUTH_TOKEN": api_key,
            "ANTHROPIC_MODEL": model,
        }
    raise ValueError(f"unknown provider {h.provider!r} for harness {h.name!r}")


def resolve(name_or_cmd: str) -> Harness:
    """Resolve a harness by registry name, or treat the string as a raw command.

    If ``name_or_cmd`` is a known harness name, return it. Otherwise wrap the
    string as a shell command run via ``bash -lc`` and assume the OpenAI wire
    format (the broadest-compatible default for arbitrary agents).
    """
    if name_or_cmd in HARNESSES:
        return HARNESSES[name_or_cmd]
    return Harness(
        name="custom",
        run=["bash", "-lc", name_or_cmd],
        provider="openai",
        description=f"Custom command: {name_or_cmd}",
    )
