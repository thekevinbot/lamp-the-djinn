# Building a Sandbox for Claude Code

I keep giving Claude Code more rope to hang me with.

It started innocently. Let it run `git status`. Fine. Let it run tests. Sure. Then I discovered `--dangerously-skip-permissions` and—look, the name is right there, I knew what I was getting into.

The thing is, Claude with full permissions is genuinely useful. No more approving every `npm install`. No more clicking through "are you sure?" dialogs while it refactors a file. It just... does the work.

But "does the work" includes "can run arbitrary shell commands on your machine." And I've had enough late-night debugging sessions caused by my *own* fat fingers to know I don't want an AI with unlimited shell access to my actual system.

So I built a sandbox. Took about a day and a half, with Claude doing most of the heavy lifting (yes, I used the AI to build its own cage—there's a metaphor in there somewhere).

## Why Bespoke?

Here's the thing about tools in 2024: they're cheap to build.

I could've looked for an existing Claude Code sandbox. Probably found something 80% right. Then spent weeks fighting the other 20%—the permissions that don't match my workflow, the missing plugins, the network rules that block something I need.

Instead: day and a half. Custom plugins baked in. Permissions tuned exactly how I want them. A dedicated "clankerbot" SSH user so AI commits show up differently in git log than my own.

Bespoke tooling used to be a luxury for teams with budgets. Now it's a weekend project. Your version of this would look different, and that's fine. That's the point.

## What It Does

One command:

```bash
bash <(curl -s https://raw.githubusercontent.com/clankerbot/clanker/main/scripts/claude-code.sh)
```

No repo to clone. The script pulls a Docker image, wires up the config, and drops you into Claude Code running with `--dangerously-skip-permissions`—but inside a container that can't hurt anything that matters.

The philosophy is simple: let Claude run amok. The container is disposable. Git is the source of truth. If everything goes sideways, `git reset --hard` and you're back to sanity.

## The Network Firewall

Here's where the paranoia kicks in.

The container blocks all outbound network traffic by default:

```bash
iptables -P OUTPUT DROP
```

Everything. Blocked. Claude can't phone home to mysterious servers, can't exfiltrate your code, can't do anything networky unless I've explicitly allowed it.

The whitelist lives in an ipset—basically a lookup table of allowed IPs:

```bash
ipset create allowed-domains hash:net
iptables -A OUTPUT -m set --match-set allowed-domains dst -j ACCEPT
```

I pre-populate it with the obvious stuff: npm registry, GitHub, PyPI, Docker Hub. Thirty-three domains total. When Claude tries to hit something not on the list, I get a prompt:

```
═══════════════════════════════════════════════════════════════
  Browser wants to access: stackoverflow.com
═══════════════════════════════════════════════════════════════

Allow access to stackoverflow.com? [y/N]
```

Say yes once, it's remembered forever. Say no, and Claude has to figure out another way.

Why iptables instead of, like, a proxy? Because kernel-level filtering can't be bypassed. An application can ignore proxy settings. It can't ignore iptables. (Well, technically it could if it had root, but the AI doesn't have root. More on that later.)

## Git as the Undo Button

I'm going to be honest: Claude still messes things up sometimes. Deletes a file it shouldn't. Refactors something into nonsense. Writes code that technically works but makes me want to cry.

The safety net is git. The AI commits constantly—more often than I would manually. So when something goes wrong, I'm never more than a few commits away from "before it broke."

The clankerbot user helps here. Every AI commit has a different author than my commits:

```
* a1b2c3d (clankerbot) Refactor auth module
* e4f5g6h (clankerbot) Add error handling
* i7j8k9l (Kevin Scott) Initial auth implementation
```

When I'm staring at a broken build at 11pm, I can immediately see: was this me, or was this the robot? Usually it's the robot. Sometimes it's me. Either way, I know where to look.

## The safe-rm Thing

Okay, this one might be overkill, but I sleep better.

`rm` is scary. Claude needs to delete files sometimes—that's legitimate. But I wanted a checkpoint before anything disappears.

So there's a wrapper script called `safe-rm`:

```bash
#!/bin/bash
if git rev-parse --git-dir > /dev/null 2>&1; then
    if [ -n "$(git status --porcelain)" ]; then
        echo "ERROR: Uncommitted changes. Commit first." >&2
        exit 1
    fi
fi
exec /bin/rm "$@"
```

Claude can delete whatever it wants—but only after committing everything. Worst case, the deleted file is one `git checkout` away.

Is this paranoid? Probably. Has it saved me yet? Not yet. Will I remove it? No.

## What Went Wrong (A Lot)

I'd love to tell you this was a clean build. It wasn't.

### Playwright

The sandbox includes Playwright for web browsing—it's more performant and flexible than Claude's built-in web tools.

### The SSH Maze

Someone reported that SSH wasn't working for private repos. I added SSH agent forwarding. Tested locally. Worked great.

Still broken for them.

Turns out they use Fish shell. When you `curl ... | bash`, the bash subprocess doesn't inherit Fish's environment variables. `SSH_AUTH_SOCK` was empty the whole time.

Okay, mount `~/.ssh` directly into the container instead. Now the error changes from "Permission denied (publickey)" to "Host key verification failed."

Here's the thing I learned: when error messages change, you're making progress. Even when it feels like you're not.

"Permission denied" meant SSH auth was failing. "Host key verification failed" meant auth *succeeded* but the host wasn't in `known_hosts`. Completely different problem. The fix was running `ssh-keyscan github.com` at container startup.

## The Permissions Philosophy

Claude has sudo access. But not to everything.

The sudoers file is surgical:

```bash
node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh
node ALL=(root) NOPASSWD: /usr/local/bin/add-domain-to-firewall.sh
node ALL=(root) NOPASSWD: /sbin/ipset add allowed-domains *
node ALL=(root) NOPASSWD: /sbin/ipset list allowed-domains
```

Claude can modify the firewall whitelist. That's it. Can't install packages as root. Can't modify system files. Can't do anything root-y except the specific firewall commands.

The 87 pre-approved shell commands are similar—broad within the sandbox, useless for escaping it. `git`, `npm`, `python`, `docker`, all the build tools. But not `rm` (that goes through `safe-rm`). Not `sudo` (except for firewall stuff). Not anything that could reach outside the container.

## Graceful Degradation

The firewall script used to be strict. DNS lookup fails? Exit with error. GitHub API unreachable? Exit with error.

This was dumb. A sandbox that refuses to start because PyPI had a DNS hiccup is useless.

Now it warns and continues:

```bash
if [ -z "$ips" ]; then
    echo "WARNING: Failed to resolve $domain (skipping)"
    continue
fi
```

GitHub down? Fine, you lose GitHub access until it's back. Container still starts. You can still work on local stuff. The degraded state is better than no state.

## Where It's At

Thirty-three whitelisted domains. Eighty-seven pre-approved commands. Sub-minute container startup when cached. Weekly CI builds to keep the Docker cache warm.

The code's at [github.com/clankerbot/clanker](https://github.com/clankerbot/clanker). One command to try it:

```bash
bash <(curl -s https://raw.githubusercontent.com/clankerbot/clanker/main/scripts/claude-code.sh)
```

It's tuned for my paranoia level and my workflow. Yours would be different. That's the whole point—software's cheap enough now that "good enough" isn't good enough. Build the thing you actually want.

And if Claude breaks something inside the sandbox? `git reset --hard`. Back to normal. That's the whole idea.

## What's Missing

This works for me. That doesn't mean it's done.

**Domain IPs are cached at startup.** The firewall resolves domain names once when the container starts. If GitHub's CDN rotates IPs mid-session, you might get blocked until restart. Haven't hit this in practice, but it's theoretically possible.

**The test suite needs work.** There are tests, but they're mostly "does the container start?" Not "does the firewall actually block things?" Not "what happens when DNS is down?" The happy path is tested. The sad paths aren't.

## What's Next

Stuff I might get to eventually:

- Negative testing. Verify that blocked things stay blocked, that `safe-rm` actually refuses deletion with uncommitted changes.
- A CLI tool for managing domains—approve, revoke, list—instead of editing files.

Or maybe none of this. The thing works. I'll probably only add features when I hit a wall that forces me to.
