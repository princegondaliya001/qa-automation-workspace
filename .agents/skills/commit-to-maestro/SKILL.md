---
name: commit-to-maestro
description: >
  Universal commit-queue handler for automatically updating Maestro Studio automation
  flows when frontend repos change. Use this skill whenever: a commit is detected on
  any tracked frontend repo, the queue-auto-process.py script reports pending entries,
  a Commit Watcher message arrives, a sub-agent needs to process repo diffs for Maestro
  updates, or ANY automation needs to bridge frontend code changes to maestro-studio
  YAML flows. Covers all projects in the workspace (chroma-studio, max-v2, remix-ai,
  faceswapper, deepswapper, maxstudio, ampere). Handles diff analysis, selector updates,
  new-screen detection, shared flow creation, temp-test generation, git commit/push,
  Discord summary, and queue entry cleanup.
---

# Commit-to-Maestro Universal Skill

Automatically process frontend repo commits and update Maestro Studio automation flows.

## When This Skill Triggers

- `queue-auto-process.py check` returns pending entries
- Commit Watcher posts a new commit to `#testing-automation-failed`
- A sub-agent is spawned with a commit-change handler task
- Any frontend repo (chroma-studio, max-v2, remix, faceswapper, deepswapper, ampere) has new commits
- The user asks to "process the queue", "update Maestro for commits", or "handle pending automation"

## Project Registry

Maps repo names to their Maestro folder, base URL, and project ID header.
**Branch-aware testing:** The queue entry includes a `testUrl` field. For `dev` branch commits, this is the staging URL. For `main`/`master`, it's production. Always use the queue entry's `testUrl` in temp tests and when updating `config.yaml`.

| Repo | Maestro Folder | Production URL | Dev Branch Staging URL | projectId Header |
|------|---------------|----------------|------------------------|-----------------|
| `chroma-studio-frontend-nextjs` | `chromastudio` | `https://www.chromastudio.ai` | `https://style-transfer-git-dev-nextbasecores-projects.vercel.app` | `default` |
| `max-v2` | `maxstudio` | `https://www.maxstudio.ai` | `https://max-v2-git-dev-nextbasecores-projects.vercel.app` | `maxStudio` |
| `remix-studio-nextjs` | `remixai` | `https://remixai.io` | `https://remixai-git-dev-nextbasecores-projects.vercel.app` | `remixAi` |
| `faceswapper-ai` | `faceswapper` | `https://faceswapper.ai` | `https://faceswapper-ai-git-dev-nextbasecores-projects.vercel.app` | `faceSwapper` |
| `deepswapper-ai-nextjs` | `deepswapper` | `https://www.deepswapper.com` | *(none yet)* | `deepSwapper` |
| `ampere-sh` | `ampere` | `https://ampere.sh` | `https://ampere-sh-5px3-git-dev-paradoxs-projects-657e7e56.vercel.app` | `ampere` |

> **Daily cron jobs always use production URLs.** The `testUrl` field is only for commit-watcher triggered testing.
> 1. Listing `repos/maestro-studio/` directories
> 2. Finding matching frontend repos in `repos/`
> 3. Asking the user for the mapping if ambiguous

## Workflow

### 1. Check the Queue

```bash
cd /root/.openclaw/workspace
python3 scripts/queue-auto-process.py check
```

If pending entries exist, the script marks the first one `in_progress` and prints JSON with:
- `entry_id`, `repo`, `branch`, `old_commit`, `new_commit`, `short_hash`, `message`
- `maestro_folder`, `discord_channel`, `diff_stats`, `full_diff` (truncated)

**If multiple entries are pending:** Process them **FIFO sequentially** — one at a time. Do not spawn parallel agents unless the user explicitly asks.

### 2. Read the Full Diff

The queue entry includes a truncated diff. Get the complete picture:

```bash
cd /root/.openclaw/workspace/repos/<repo>
git log -1 --format="%H %s %an %ci" <new_commit>
git diff <old_commit>..<new_commit> --stat
git diff <old_commit>..<new_commit> | head -400
```

If the diff is >400 lines, read the rest in chunks.

### 3. Analyze Diff for Maestro Impact

Categorize every frontend change into these buckets:

| Change Type | Maestro Action |
|-------------|---------------|
| New `data-testid` or `data-maestro` attribute added | **Update selectors** in flows to use stable attributes |
| `data-testid` / `data-maestro` **removed** | **Find replacement selectors** (class, text, coordinate fallback) |
| New component / screen / dialog | **Add new flow or sub-flow** to handle navigation/dismissal |
| Component / screen / dialog **removed** | **Remove or skip** dead flows |
| URL route added/changed | **Update `openLink` / `launchApp` steps** |
| Generate button moved/renamed | **Update tap target** in generation flows |
| Upload area changed (single → multiple, new props) | **Update upload sub-flows** |
| Model selector changed (groups, options, structure) | **Update model-selection helpers** |
| Schema fields changed (new field type, options, defaults) | **Update schema-field helpers** |
| CSS/class changes only (no semantic change) | **Usually no action** — verify selectors still match |
| `__maestroInternalMode=1` or similar automation flag | **Add to `openLink` URLs** in relevant flows |

**Rule of thumb:** If the diff touches anything a Maestro flow would tap, type into, or wait for, it probably needs a Maestro update.

### 4. Discover Current Maestro Flows

```bash
find /root/.openclaw/workspace/repos/maestro-studio/<maestro_folder> -type f -name "*.yaml" | head -50
```

Read key flows that are likely affected. Prioritize:
1. `shared/` — helper flows used by many tests
2. `schema/` or `routes/` — generation and model flows
3. `config.yaml` — base URLs, headers, defaults
4. Any flow whose filename suggests the changed component

### 5. Apply Changes to Maestro

**Rules:**
- **ONLY** modify files in `repos/maestro-studio/<maestro_folder>/`
- **NEVER** modify frontend repos
- Prefer **stable selectors** over fragile ones:
  - `[data-maestro="..."]` > `[data-testid="..."]` > `text:` > class-based > coordinate tapping
- When replacing coordinate taps (`tapOn: { x, y }`), add a JavaScript tap with coordinate fallback:
  ```yaml
  - runScript:
      file: ../shared/tap-element.js
      env:
        SELECTOR: '[data-maestro="model-generate-button"]'
        FALLBACK_X: "0.5"
        FALLBACK_Y: "0.85"
  ```
- If a new shared flow is needed, create it under `<maestro_folder>/shared/`
- If a new test is needed, create it under `<maestro_folder>/tests/`
- Keep changes **minimal and targeted** — don't rewrite entire flows for small selector changes

### 6. Create a Temp Test (Optional but Recommended)

Create a focused temp test that exercises the changed functionality.

**Use the `testUrl` from the queue entry** — this is already set correctly:
- `main`/`master` → production URL
- `dev` → staging URL (Vercel preview deploy)

```yaml
# <maestro_folder>/tests/temp-test-<repo>-<short_hash>.yaml
appId: <app-id>
---
- openLink: "<testUrl>?__maestroInternalMode=1"
- assertVisible: { selector: "[data-maestro='changed-element']" }
# ... steps that specifically test the changed behavior
```

If the queue entry's `testUrl` differs from the current `config.yaml` baseUrl, update `config.yaml` before running the test:

```bash
cd /root/.openclaw/workspace/repos/maestro-studio/<maestro_folder>
sed -i "s|baseUrl: .*|baseUrl: <testUrl>|" config/config.yaml
```

Run it if Maestro CLI is available. If not, skip and note "Maestro CLI not available" in the summary.

> **Important:** Only change `config.yaml` for the temp test. Do NOT commit `config.yaml` with a staging URL — either revert it after testing, or leave it unchanged and use `--env baseUrl=<testUrl>` when running `maestro test`.

### 7. Commit and Push

```bash
cd /root/.openclaw/workspace/repos/maestro-studio

# Stage ONLY the files you changed
git add <maestro_folder>/shared/<new-or-changed>.yaml
git add <maestro_folder>/tests/temp-test-...  # if keeping, otherwise skip
git add <maestro_folder>/schema/...
# etc.

# NEVER use `git add .`

git commit -m "test: update Maestro for <repo>/<branch> <short_hash> - <commit_message>"
git push origin main
```

Capture the push result (success / error message).

### 8. Delete Temp Test (if created)

```bash
rm /root/.openclaw/workspace/repos/maestro-studio/<maestro_folder>/tests/temp-test-<repo>-<short_hash>.yaml
git add <maestro_folder>/tests/
git commit --amend -m "test: update Maestro for <repo>/<branch> <short_hash> - <commit_message>"
git push origin main --force-with-lease  # only if already pushed; otherwise just commit
```

> If the temp test file was already committed and you want it gone, you can also just `git rm` it and do a follow-up commit. Cleanliness matters — don't leave temp files in the repo.

### 9. Send Discord Summary

Post to the queue entry's `discord_channel` (default `#testing-automation-failed` / `1498991059227774986`):

```
📋 Maestro update — <repo> <short_hash>

**Commit:** <message>
**Files changed:** <count> (<list key files>)

**Maestro updates:**
• <specific change 1>
• <specific change 2>
• ...

**Temp test:** <pass / fail / skipped>
**Git push:** <success / fail with error>
```

Use the `scripts/discord-summary.py` helper if available, or just post text.

### 10. Mark Queue Entry Done

```bash
cd /root/.openclaw/workspace
python3 scripts/queue-auto-process.py mark-done <entry_id>
```

### 11. Check for Next Entry

If more pending entries exist, loop back to step 1 and process the next one **sequentially**.

## Common Patterns

### Pattern A: data-maestro attributes added to ModelSelector

**Frontend diff:** `ModelSelector/index.tsx` gets `data-maestro="model-selector-trigger"`, `data-maestro="model-selector-popover"`, `data-maestro="model-selector-group"`, `data-maestro="model-selector-option"`

**Maestro action:**
1. Update `assert-model-automation-context.yaml` to assert `[data-maestro="model-generate-button"]`
2. Update `open-model-route.yaml` to assert the same
3. Create `shared/tap-model-generate-button.yaml` if it doesn't exist
4. Replace coordinate-based generate tapping in all `*-generate.yaml` flows with the new shared flow

### Pattern B: GenerateButton component split into model vs legacy

**Frontend diff:** New `model-generate-button` alongside existing `legacy-generate-button`

**Maestro action:**
1. Update `assert-model-automation-context.yaml` → checks `model-generate-button`
2. Update `assert-tool-route-hydration.yaml` → checks `legacy-generate-button`
3. Update generation flows to tap `model-generate-button` where appropriate

### Pattern C: Upload area gets `data-maestro` attributes

**Frontend diff:** `SingleMediaUploader.tsx` adds `data-maestro="upload-area-trigger"`, `data-maestro="upload-input"`

**Maestro action:**
1. Update upload helper flows to use the new selectors
2. If the upload structure changed (e.g., from single to multiple), update tap sequences

### Pattern D: `__maestroInternalMode=1` param needed

**Frontend diff:** Dialog/promo code that should be suppressed in automation

**Maestro action:**
1. Find all `openLink` steps in the Maestro folder
2. Add `?__maestroInternalMode=1` to the URL (or `&__maestroInternalMode=1` if query params already exist)
3. Verify no flow breaks from the extra param

## Safety Rules

1. **Never modify frontend repos.** Only `repos/maestro-studio/...`
2. **Never use `git add .` in maestro-studio.** Stage only changed files explicitly.
3. **Never commit temp/debug files.** Delete temp tests before final push, or keep them clean.
4. **Never expose secrets/credentials** in Discord summaries or commits.
5. **FIFO/sequential processing.** One queue entry at a time unless user explicitly requests parallel.
6. **Minimal changes.** Don't rewrite flows — update selectors, add assertions, or create small shared helpers.
7. **Security review if uncertain.** If the diff touches auth, API routes, webhooks, or payment flows, pause and ask Prince before proceeding.

## Bundled Scripts

- `scripts/diff-analyzer.py` — (optional) Scans a diff and suggests Maestro file updates
- `scripts/selector-finder.py` — (optional) Searches maestro-studio YAMLs for selector patterns

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Queue script not found | Check `scripts/queue-auto-process.py` exists; if not, use the failed-automation-queue skill |
| Maestro folder missing | Ask user for the correct mapping; add to Project Registry above |
| Push rejected (non-fast-forward) | `git pull origin main`, resolve conflicts accepting remote unless local changes are newer, then re-push |
| Diff too large to analyze | Read in 300-line chunks; focus on `src/components/` and `src/app/` paths |
| No data-maestro attributes in diff | Fall back to `data-testid`, then text, then class selectors |
| Conflicting selector updates | Prefer the most specific stable selector; add assertions to verify |
