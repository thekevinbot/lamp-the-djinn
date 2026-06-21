# Deploy: trusted harness cache refresh

The cage runs untrusted coding agents. To avoid letting the untrusted agent
download harness packages itself (a supply-chain risk), lamp-the-djinn mounts a
**read-only** harness cache into every container:

    ~/.cache/lamp-the-djinn/harness-cache  ->  /home/node/.cache/ltd-harness (readonly)

That cache is populated on the **host** (trusted) by
`scripts/refresh-harness-cache.sh`, which pre-fetches harness packages (npm/uv)
with a **cooldown window** -- only versions published more than N days ago
(default 3) are installed. The cooldown defends against fresh-malicious
releases: a package compromised today won't enter the cage until it has aged
past the window, giving the ecosystem time to detect and yank it.

This directory contains a systemd user timer to run that refresh nightly.

## systemd user units (recommended)

Link or copy the units into your user systemd directory, then enable the timer:

    mkdir -p ~/.config/systemd/user
    cp deploy/lamp-the-djinn-harness-cache.service ~/.config/systemd/user/
    cp deploy/lamp-the-djinn-harness-cache.timer   ~/.config/systemd/user/

    systemctl --user daemon-reload
    systemctl --user enable --now lamp-the-djinn-harness-cache.timer

Check status / logs:

    systemctl --user list-timers lamp-the-djinn-harness-cache.timer
    systemctl --user start lamp-the-djinn-harness-cache.service   # run once now
    journalctl --user -u lamp-the-djinn-harness-cache.service -n 50

The unit's `ExecStart` assumes the repo lives at
`~/work/code/projects/lamp-the-djinn`. Edit the `.service` file if you cloned it
elsewhere. To keep the refresh running while you're logged out, enable lingering:

    loginctl enable-linger "$USER"

Adjust the cooldown by editing `Environment=LTD_COOLDOWN_DAYS=3` in the
`.service` file.

## cron alternative

If you don't use systemd, a daily cron entry does the same job (runs ~03:17):

    17 3 * * * LTD_COOLDOWN_DAYS=3 $HOME/work/code/projects/lamp-the-djinn/scripts/refresh-harness-cache.sh >> $HOME/.cache/lamp-the-djinn/refresh.log 2>&1
