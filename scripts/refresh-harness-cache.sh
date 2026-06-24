#!/usr/bin/env bash
#
# refresh-harness-cache.sh -- TRUSTED nightly harness pre-fetch.
#
# WHERE THIS RUNS: on the HOST, as the trusted user (you), OUTSIDE the cage.
# WHY: the cage mounts ~/.cache/lamp-the-djinn/harness-cache READ-ONLY, so the
#   untrusted agent inside the container uses these pre-vetted packages instead
#   of downloading fresh ones itself over the network.
# COOLDOWN: we only fetch package versions published before a cutoff (default
#   3 days ago). This defends against fresh-malicious releases -- a package
#   compromised and published today won't be installed until it has aged past
#   the cooldown window, giving the ecosystem time to detect and yank it.
#
# Best-effort: every fetch is wrapped so one failing harness doesn't abort the
# rest. Idempotent: safe to run nightly via systemd timer or cron.

set -euo pipefail

CACHE_DIR="${HOME}/.cache/lamp-the-djinn/harness-cache"
MANIFEST="${HOME}/.cache/lamp-the-djinn/harness-manifest.txt"
COOLDOWN_DAYS="${LTD_COOLDOWN_DAYS:-3}"
CUTOFF="$(date -u -d "${COOLDOWN_DAYS} days ago" +%Y-%m-%dT%H:%M:%SZ)"

UV_CACHE="${CACHE_DIR}/uv"
NPM_CACHE="${CACHE_DIR}/npm"
NPM_PREFIX="${CACHE_DIR}/npm"

mkdir -p "${UV_CACHE}" "${NPM_CACHE}" "${NPM_PREFIX}"

echo "refresh-harness-cache: cache dir = ${CACHE_DIR}"
echo "refresh-harness-cache: cooldown  = ${COOLDOWN_DAYS} day(s) (cutoff ${CUTOFF})"

# --- uv-based harnesses (aider) ---------------------------------------------
# `uv tool install --exclude-newer` ignores any distribution published after the
# cutoff, enforcing the cooldown for the Python side.
if command -v uv >/dev/null 2>&1; then
  echo "refresh-harness-cache: pre-fetching aider via uv (cutoff ${CUTOFF})"
  UV_CACHE_DIR="${UV_CACHE}" uv tool install --exclude-newer "${CUTOFF}" aider \
    || echo "warn: uv tool install aider failed (cutoff ${CUTOFF})"
else
  echo "warn: uv not found on PATH; skipping uv-based harnesses"
fi

# --- npm-based harnesses (codex, devcontainers/cli) -------------------------
# `npm install --before` resolves to the latest version published before the
# cutoff, enforcing the cooldown for the Node side. Packages land under
# ${NPM_PREFIX}/node_modules and the download cache under ${NPM_CACHE}.
if command -v npm >/dev/null 2>&1; then
  echo "refresh-harness-cache: pre-fetching npm harnesses (before ${CUTOFF})"
  npm_config_cache="${NPM_CACHE}" npm install --prefix "${NPM_PREFIX}" \
    --before "${CUTOFF}" @openai/codex @devcontainers/cli \
    || echo "warn: npm install @openai/codex @devcontainers/cli failed (before ${CUTOFF})"
else
  echo "warn: npm not found on PATH; skipping npm-based harnesses"
fi

# --- manifest-driven harnesses ----------------------------------------------
# ltd records the package specs users actually invoke (npx/uvx/...) to
# ${MANIFEST}, one spec per line. Warm each here with the same cooldown logic.
# Heuristic: a leading '@' (scoped) or a name containing '/' is npm; otherwise
# try uv first then npm best-effort. Blank lines and '#' comments are skipped.
warm_uv() {
  local spec="$1"
  if command -v uv >/dev/null 2>&1; then
    UV_CACHE_DIR="${UV_CACHE}" uv tool install --exclude-newer "${CUTOFF}" "${spec}" \
      && return 0
  fi
  return 1
}

warm_npm() {
  local spec="$1"
  if command -v npm >/dev/null 2>&1; then
    npm_config_cache="${NPM_CACHE}" npm install --prefix "${NPM_PREFIX}" \
      --before "${CUTOFF}" "${spec}" \
      && return 0
  fi
  return 1
}

if [[ -f "${MANIFEST}" ]]; then
  echo "refresh-harness-cache: warming manifest entries from ${MANIFEST}"
  while IFS= read -r spec || [[ -n "${spec}" ]]; do
    # Trim whitespace.
    spec="${spec#"${spec%%[![:space:]]*}"}"
    spec="${spec%"${spec##*[![:space:]]}"}"
    [[ -z "${spec}" ]] && continue
    [[ "${spec}" == \#* ]] && continue

    echo "refresh-harness-cache: manifest spec '${spec}'"
    if [[ "${spec}" == @* || "${spec}" == */* ]]; then
      # Scoped or namespaced name -> npm-flavored.
      warm_npm "${spec}" || echo "warn: failed to warm '${spec}' via npm"
    else
      # Plain name: prefer uv (Python), fall back to npm best-effort.
      warm_uv "${spec}" || warm_npm "${spec}" \
        || echo "warn: failed to warm '${spec}' via uv or npm"
    fi
  done < "${MANIFEST}"
else
  echo "refresh-harness-cache: no manifest at ${MANIFEST}; skipping manifest warm"
fi

echo "refresh-harness-cache: done."
