#!/usr/bin/env bash
# setup-kata-runtime.sh -- wire Kata Containers (Cloud Hypervisor) into Docker as
# the `kata` runtime, enabling the `ltd --runtime kata` isolation tier.
#
#   sudo bash deploy/setup-kata-runtime.sh
#
# Assumes the kata-static release is installed at /opt/kata. No reboot is needed;
# the only restart is the Docker service (which briefly bounces running
# containers -- the LiteLLM proxy has restart:unless-stopped, so it returns).
set -euo pipefail

KATA_DIR=/opt/kata
RUNTIME_BIN="$KATA_DIR/bin/kata-runtime"
CLH_CONF="$KATA_DIR/share/defaults/kata-containers/configuration-clh.toml"
DEFAULT_CONF="$KATA_DIR/share/defaults/kata-containers/configuration.toml"
DAEMON_JSON=/etc/docker/daemon.json

if [ "$(id -u)" -ne 0 ]; then
    echo "Run as root:  sudo bash $0" >&2
    exit 1
fi

if [ ! -x "$RUNTIME_BIN" ]; then
    echo "ERROR: $RUNTIME_BIN not found -- install the kata-static release to /opt/kata first." >&2
    exit 1
fi

echo "==> Loading vhost kernel modules (vsock = guest<->host agent, vhost_net = networking)..."
modprobe vhost vhost_net vhost_vsock
printf 'vhost\nvhost_net\nvhost_vsock\n' > /etc/modules-load.d/kata.conf

echo "==> Checking the host is Kata-capable..."
if ! "$RUNTIME_BIN" check; then
    echo "ERROR: 'kata-runtime check' failed -- resolve the issues above before continuing." >&2
    exit 1
fi

echo "==> Selecting Cloud Hypervisor (virtio-fs, so bind mounts / -v work in the VM)..."
ln -sf "$CLH_CONF" "$DEFAULT_CONF"

echo "==> Registering the 'kata' runtime in $DAEMON_JSON..."
mkdir -p /etc/docker
if [ -f "$DAEMON_JSON" ]; then
    # Merge into existing config (preserve whatever is already there).
    tmp="$(mktemp)"
    jq --arg p "$RUNTIME_BIN" '.runtimes.kata = {path: $p}' "$DAEMON_JSON" > "$tmp"
    mv "$tmp" "$DAEMON_JSON"
else
    jq -n --arg p "$RUNTIME_BIN" '{runtimes: {kata: {path: $p}}}' > "$DAEMON_JSON"
fi

echo "==> Restarting Docker (service restart, NOT a reboot)..."
systemctl restart docker

echo "==> Verifying the 'kata' runtime is registered..."
if docker info --format '{{json .Runtimes}}' | grep -q '"kata"'; then
    echo "OK: 'kata' runtime is registered."
else
    echo "WARNING: 'kata' not visible in 'docker info' -- check 'systemctl status docker' and $DAEMON_JSON." >&2
    exit 1
fi

echo
echo "Done. Quick smoke test (a Kata guest kernel should differ from the host's $(uname -r)):"
echo "    docker run --rm --runtime kata busybox uname -r"
