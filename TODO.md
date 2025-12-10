# TODO

## Container Tools
- [x] uv support - DONE (cache issue fixed, tests passing)
- [x] pnpm support - DONE (installed via corepack, tests passing)
- [x] Docker socket access - ALL TESTS PASSING
  - [x] CI test added - runs `docker ps` with socket mounted (commit 1f45e78)
  - [x] Socket mount in devcontainer.json - line 39 (already configured)
  - [x] Fixed group permissions in CI (--group-add for Docker socket gid)

## CI/CD
- [x] CI tests for container - DONE (test-container.yml merged)
- [x] Fix cache busting - DONE (Dockerfile hash in cache key)
- [ ] Automerge on CI check pass - configure GitHub branch protection + auto-merge
- [ ] Linting - add linting workflow (shellcheck for scripts, hadolint for Dockerfile)

## GitHub Auth
- [x] Logout thekevinscott from gh CLI - DONE
- [x] Set gh to use SSH protocol - DONE
- [ ] Create PAT for clankerbot - need token with scopes: repo, workflow, write:packages
- [ ] Run `gh auth login` with clankerbot token
- Note: Git operations work via SSH, but gh API commands need a PAT

## Blog Post (separate repo)
- [ ] Add "Baked-In Tools" section: pnpm, uv, Playwright, Docker socket
