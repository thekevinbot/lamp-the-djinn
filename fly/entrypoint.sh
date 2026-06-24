#!/bin/bash
# entrypoint.sh -- boot script for the "fly" isolation backend (Firecracker microVM).
#
# Brings Tailscale up (best-effort) so the remote cage rejoins the tailnet and
# can reach tower's LiteLLM proxy + honor egress policy, then execs the cage.
#
# UNVERIFIED: not run against a real Fly Machine in this environment. This is
# guarded, best-effort scaffolding -- every step degrades gracefully if the
# tooling or the auth key is absent.
set -uo pipefail

log() { echo "[ltd-fly-entrypoint] $*" >&2; }

# --- Tailscale rejoin (best-effort, guarded) --------------------------------
# Only attempt if tailscaled is actually present in the image.
if command -v tailscaled >/dev/null 2>&1; then
    log "Starting tailscaled (userspace networking)..."
    # Userspace-networking mode avoids needing a TUN device, which a microVM
    # image may not expose. SOCKS/HTTP proxies let processes route via tailnet.
    tailscaled \
        --state=/var/lib/tailscale/tailscaled.state \
        --socket=/var/run/tailscale/tailscaled.sock \
        --tun=userspace-networking \
        >/var/log/tailscaled.log 2>&1 &

    # Give the daemon a moment to open its control socket.
    sleep 2

    if [ -n "${TS_AUTHKEY:-}" ]; then
        log "Bringing Tailscale up to rejoin the tailnet..."
        tailscale up \
            --authkey="${TS_AUTHKEY}" \
            --hostname="${TS_HOSTNAME:-lamp-the-djinn-cage}" \
            --accept-routes \
            || log "WARNING: 'tailscale up' failed; continuing without tailnet"
    else
        log "TS_AUTHKEY not set; skipping 'tailscale up' (cage will run off-tailnet)"
    fi
else
    log "tailscaled not found in image; skipping Tailscale (cage runs off-tailnet)"
fi

# --- Exec the cage ----------------------------------------------------------
# Hand off to whatever command Fly passed us (CMD / `fly machine run ...`),
# defaulting to an interactive shell so the cage stays useful out of the box.
if [ "$#" -gt 0 ]; then
    log "Exec: $*"
    exec "$@"
else
    log "No command given; exec'ing login shell"
    exec /bin/bash -l
fi
