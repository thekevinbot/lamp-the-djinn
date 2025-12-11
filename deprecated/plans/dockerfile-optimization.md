# Dockerfile Optimization Plan

## Current State

### Build Performance (GitHub Actions)
| Run | Duration | Notes |
|-----|----------|-------|
| #1 | 9m 1s | Initial build (cold cache) |
| #2 | 51s | Cached |
| #3 | 57s | Cached |
| #4-6 | ~1m | Cached |
| #7 | 1m 56s | Latest (some cache invalidation) |

**Takeaway**: Cached builds are fast (~1 min), but cold builds are slow (9+ min). The recent 2-minute build suggests cache invalidation occurred.

---

## Identified Optimization Opportunities

### 1. Add npm Cache Mount (HIGH PRIORITY)

**Problem**: Line 54 installs Claude Code globally without cache mount:
```dockerfile
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}
```

**Impact**: Every build with a different `CLAUDE_CODE_VERSION` re-downloads all npm packages.

**Solution**:
```dockerfile
RUN --mount=type=cache,target=/root/.npm,sharing=locked \
  npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}
```

---

### 2. Move ssh-keyscan to Runtime (MEDIUM PRIORITY)

**Problem**: Lines 96-99 run `ssh-keyscan` at build time:
```dockerfile
RUN mkdir -p ~/.ssh && \
  chmod 700 ~/.ssh && \
  ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null && \
  chmod 644 ~/.ssh/known_hosts
```

**Issues**:
- Network call during build (~1-2s)
- GitHub's SSH keys may change, making the cached image stale
- If GitHub is slow/down, build can fail or timeout

**Solution**: Move to a startup script that runs once on container start:
```dockerfile
# Remove ssh-keyscan from Dockerfile
RUN mkdir -p ~/.ssh && chmod 700 ~/.ssh

# In devcontainer.json postStartCommand, add:
# ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
```

---

### 3. Combine User Setup RUN Commands (LOW PRIORITY)

**Problem**: Multiple small RUN commands for user/directory setup:
- Lines 58-63: User rename and group setup
- Lines 66-68: Command history directory
- Lines 77-78: Workspace/config directories

**Solution**: Combine into fewer layers:
```dockerfile
RUN usermod -l node -d /home/node -m ubuntu && \
  groupmod -n node ubuntu && \
  chsh -s /bin/zsh node && \
  echo "node ALL=(root) NOPASSWD: ..." > /etc/sudoers.d/node-firewall && \
  chmod 0440 /etc/sudoers.d/node-firewall && \
  usermod -aG docker node 2>/dev/null || groupadd docker && usermod -aG docker node || true && \
  mkdir /commandhistory && \
  touch /commandhistory/.bash_history && \
  chown -R node /commandhistory && \
  mkdir -p /workspace /home/node/.claude && \
  chown -R node:node /workspace /home/node/.claude /home/node
```

---

### 4. Pre-download git-delta and Docker CLI (OPTIONAL)

**Current**: These are downloaded during build from GitHub/Docker CDN.

**Alternative**: Use GitHub Actions to pre-cache these binaries, or check if there are faster mirrors.

---

## Recommended Changes

### File: `.devcontainer/Dockerfile`

#### Change 1: Add npm cache mount
**Location**: Line 54

**Before**:
```dockerfile
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}
```

**After**:
```dockerfile
RUN --mount=type=cache,target=/root/.npm,sharing=locked \
  npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}
```

#### Change 2: Move ssh-keyscan to runtime
**Location**: Lines 96-99

**Before**:
```dockerfile
RUN mkdir -p ~/.ssh && \
  chmod 700 ~/.ssh && \
  ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null && \
  chmod 644 ~/.ssh/known_hosts
```

**After**:
```dockerfile
RUN mkdir -p ~/.ssh && chmod 700 ~/.ssh
```

### File: `.devcontainer/devcontainer.json`

Add ssh-keyscan to postStartCommand:
```json
"postStartCommand": "ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null || true && sudo /usr/local/bin/init-firewall.sh"
```

#### Change 3: Combine user/directory setup (optional)
**Location**: Lines 56-68, 77-78

Merge these RUN commands into a single layer to reduce image layers.

---

## Expected Impact

| Optimization | Build Time Savings | Cache Improvement |
|--------------|-------------------|-------------------|
| npm cache mount | 5-30s per build | Better npm layer reuse |
| Remove ssh-keyscan | 1-2s per build | Eliminates network dependency |
| Combine RUN commands | Minimal | Smaller image (~few KB) |

**Overall**: These changes should reduce cold build times and improve reliability by eliminating network dependencies during build.

---

## Files to Modify

1. `.devcontainer/Dockerfile` - Main optimization target
2. `.devcontainer/devcontainer.json` - Add ssh-keyscan to postStartCommand
