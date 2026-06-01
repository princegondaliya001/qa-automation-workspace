# MEMORY.md

## Prince / QA Tester

- User is **Prince**; call him Prince only.
- Assistant identity: **QA Tester** 🧪.
- Vibe: sharp, friendly, direct, evidence-first; proactive on internal checks; careful with secrets/external/destructive actions.

## Current project

Prince is working on Maestro/testing automation across ChromaStudio, MaxStudio, RemixAI, and Maestro Studio.

Ampere testing note: use `caltuanbesa6@gmail.com` as the Ampere login email going forward; password unchanged per Prince, but do not store or echo it.

Discord workflow: use channel `#testing-automation-failed` / `1498991059227774986` as the failed-automation drop queue. `requireMention` is false, so no @mention is needed; triage every dropped failure message routed from that channel. For each failure/Captain Hook run-log message: triage it, spawn a focused sub-agent when useful, resolve/verify, then report back in that channel. On 2026-05-15 Prince explicitly asked that all Captain Hook-sent messages be resolved proactively by QA Tester using run logs and sub-agents.

See `MAESTRO_CONTEXT.md` and `memory/imported-telegram-testingautomation-2026-05-06.md` for imported history.

Important: imported Telegram history contains exposed credentials/webhooks. Treat them as compromised. Do not repeat or reuse them; ask Prince for fresh credentials when needed.

## Repo restoration targets

- `nextbasecore/chroma-studio-frontend-nextjs`
- `nextbasecore/max-v2`
- `nextbasecore/remix-studio-nextjs`
- `princegondaliya001/maestro-studio`

Current fresh workspace needs these cloned with valid GitHub auth.

## Branch-Aware Commit Watcher URLs (2026-05-29)

Commit watcher now supports branch-aware staging URLs. When a `dev` branch commit is detected, the queue entry includes the staging `testUrl` from `BRANCH_URLS` in `commit-watcher-update.py`.

| Repo | Dev Branch URL | Production URL |
|------|---------------|----------------|
| chroma-studio-frontend-nextjs | https://style-transfer-git-dev-nextbasecores-projects.vercel.app | https://www.chromastudio.ai |
| max-v2 | https://max-v2-git-dev-nextbasecores-projects.vercel.app | https://www.maxstudio.ai |
| remix-studio-nextjs | https://remixai-git-dev-nextbasecores-projects.vercel.app | https://remixai.io |
| faceswapper-ai | https://faceswapper-ai-git-dev-nextbasecores-projects.vercel.app | https://faceswapper.ai |
| ampere-sh | https://ampere-sh-5px3-git-dev-paradoxs-projects-657e7e56.vercel.app | https://ampere.sh |
| deepswapper-ai-nextjs | https://deepswapper-ai-git-dev-sanketkheni01s-projects.vercel.app | https://www.deepswapper.com |

**Daily cron jobs remain on production URLs.** Only commit-watcher triggered dev branch testing uses staging URLs.

## Local skills

- Chroma Studio skill is installed at `/root/.openclaw/workspace/.agents/skills/chroma-studio/SKILL.md`; it uses repo path `/root/.openclaw/workspace/repos/chroma-studio-frontend-nextjs`, Discord failed queue `#testing-automation-failed` / `1498991059227774986`, and live `https://api.chromastudio.ai/model-schema` with `x-project-id: default` as source of truth.
- MaxStudio / max-v2 skill is installed at `/root/.openclaw/workspace/.agents/skills/max-v2/SKILL.md`; it uses repo path `/root/.openclaw/workspace/repos/max-v2`, triggers for `projectId="maxStudio"`, watches the same Discord failed queue, and uses live `https://api.chromastudio.ai/model-schema` with `x-project-id: maxStudio` as source of truth.
- RemixAI schema-solve skill is installed at `/root/.openclaw/workspace/.agents/skills/remix-schema-solve/SKILL.md`; it uses repo path `/root/.openclaw/workspace/repos/remix-studio-nextjs`, watches the same Discord failed queue with `requireMention=false`, and uses live `https://api.chromastudio.ai/model-schema` with `x-project-id: remixAi` as the primary source of truth.
- Failed-automation queue orchestration skill is installed at `/root/.openclaw/workspace/.agents/skills/failed-automation-queue/SKILL.md`; it coordinates ChromaStudio, MaxStudio, RemixAI, DeepSwapper/Maestro failures from Discord `#testing-automation-failed`, tracks FIFO state in `/root/.openclaw/workspace/state/failed-automation-queue.json`, and includes `scripts/queue.py` for add/list/update.
- Sentry `security-review` skill is installed and ready from `agents-skills-personal` (`/root/.agents/skills/security-review/SKILL.md`, symlinked for OpenClaw). Prince asked on 2026-05-20 to use it all the time; for code/repo changes, especially before finalizing patches or reviews, load/use `security-review` when security implications are plausible.
- Prince's failed-automation policy from 2026-05-20: for Discord/Captain Hook errors, fetch/pull relevant frontend/product repo context as source of truth, but avoid frontend code changes unless clearly necessary; prefer clean Maestro Studio automation fixes. Resolve all related errors first, run verification + security review, then push only when clean/safe. Maintain clean code/file/folder structure and do not commit temp/debug/unrelated files. Default queue execution must be strict FIFO/sequential: solve one item/group at a time; do not spawn multiple parallel fix agents unless Prince explicitly asks for parallel work. Duplicate alerts with the same root cause may be grouped under the one active resolver.
- Anthropic `skill-creator` skill is installed and ready from `agents-skills-personal` (`/root/.agents/skills/skill-creator/SKILL.md`, symlinked for OpenClaw). Prince asked on 2026-05-20 to use it to create/improve skills for recurring issue patterns.

## Current Status (2026-05-31)

**ChromaStudio MCP Modal Fix** - Committed `752c0e2` to maestro-studio. Addresses async "Coming Soon" modal blocking 7 daily test suites. Uses full-document search + indefinite setInterval guard.

**MaxStudio Homepage CTA Fix** - Committed `243a0c9` to maestro-studio. `ensure-internal-mode.yaml` now accepts "Start Creating" in addition to "Generate".

**Chrome/CDP Cleanup** - Cleared 10 zombie Chrome processes and 41 temp profile directories. Chrome 149 binary + wrapper confirmed working.

**Trattoria Sostanza** - Blog live.

**FaceSwapper All-Tools Cron** — Stage 05 batch timeout (exit 124) on `gender-swap`. Retries passed. 64/64 coverage green (2026-05-31).

**Frontend diff → Maestro sync** (`chromastudio` branch `git-diff-maestro-test`) — 9 files changed (credits, models, payload, routes, UI text). All 4 focused verifications passed (ChromaStudio, MaxStudio, RemixAI, DeepSwapper). Dirty-tree guard active — no auto-patching until frontend repo is clean.

**Waydroid Status** — RUNNING at 192.168.240.112.

**Commit Queue** — Clear as of 2026-05-31 18:25 UTC.

## Repo Sync Status (2026-05-31)
| Repo | Status |
|------|--------|
| chroma-studio-frontend-nextjs | ✅ Up to date |
| max-v2 | ✅ Up to date |
| remix-studio-nextjs | ✅ Up to date |
| maestro-studio | ✅ Up to date |
| trattoria-sostanza | ✅ Blog live |

## Key Learnings (2026-05-29 to 2026-05-30)

### ChromaStudio select-model-with-search off-screen bug
- **Fix:** Added `evalScript` step that calls `scrollIntoView({ block: 'center', inline: 'center' })` and dispatches `MouseEvent('click')` before `tapOn` fallback.
- **Commit:** `10ecfe0` in maestro-studio

### ChromaStudio text-to-video URL mismatch
- **Problem:** All text-to-video flows used `chromastudio.ai/text-to-video` (landing page) instead of `chromastudio.ai/ai-text-to-video` (actual tool).
- **Fix:** Updated 108 flow references across all platforms.
- **Commit:** `3fbb023` in maestro-studio

### MaxStudio schema check timeout fix
- **Problem:** 241 flows each ran redundant `ensure-auth` + `ensure-internal-mode` + `close-home-dialog` setup. Per-model overhead was ~50-60s.
- **Fix:** Created optimized shared flows that skip `ensure-internal-mode`, split into 6-model sub-masters, generated `master-desktop-schema-check-optimized.yaml` that runs setup once then runs all sub-masters in same session.
- **Commit:** `e2a57ac` in maestro-studio

### MaxStudio regenerate check failure
- **Fix (Maestro):** Updated `regenerate-result-desktop.yaml` to prefer `window.location` over `globalThis.location` with fallback guards.
- **Fix (frontend):** Added `data-maestro-current-model-id` attribute to `ImageCreatorToolForm` in max-v2.
- **Commits:** `3953c34` (maestro-studio), `baa686f1` (max-v2)

### Chrome/CDP infrastructure instability pattern
- **Observation:** Chrome 148 / Chromedriver 148.0.7778.178 shows recurring instability with Maestro 2.6.0: renderer crashes, `UnreachableBrowserException`, cross-origin iframe NPE.
- **Action:** Retry on fresh runner. No Maestro fix needed. Monitor ChromeDriver compatibility.

### Waydroid mobile infrastructure
- **Observation:** Waydroid container can stop unexpectedly, causing all mobile tests to fail with gRPC UNAVAILABLE or no WebView socket found.
- **Action:** Check `waydroid status` before mobile test runs. Restart if needed.

### DeepSwapper transient API slowness
- **Observation:** Face swap processing can exceed 120s timeout. Download button may not appear within timeout even though test mode initializes correctly.
- **Action:** If recurring, increase timeout from 120s to 180s. No Maestro fix needed.

### ChromaStudio IOSAppBanner Re-enabled (2026-05-31)
- **Observation:** Frontend diff on `git-diff-maestro-test` branch re-enables `IOSAppBanner` (was commented out). Banner has `z-[9999]` fixed positioning, could block Maestro interactions.
- **Changes:** localStorage keys renamed (`iosAppBannerDismissed` → `iosAppBannerDismissed1`), new "Ad" badge, text changed to "Install Free Image & Video", width reduced from 420px to 360px.
- **Impact:** `close-home-dialog.yaml` currently searches for "Coming Soon"/"MCP" text — won't catch this banner. If banner renders over Generate button, tests will fail.
- **Status:** Uncommitted in test branch. Sync passed all 4 focused checks. Monitor when merged to `dev`/`main`.
- **Problem:** Optimized `master-optimized-part*.yaml` sub-masters were included in flow counts, causing test failures.
- **Fix:** Updated 4 test files to exclude `master-optimized` files from counts.
- **Commit:** `c1745e1` in maestro-studio

### ChromaStudio MCP Modal Fix (2026-05-31)
- **Problem:** MCP "Coming Soon" promo modal renders asynchronously via React portal, evading synchronous `close-home-dialog.yaml` dismissal. Blocks Generate button, model selection, and success detection across 7 ChromaStudio daily test suites.
- **Root cause:** React portals can attach DOM nodes outside `document.body` (e.g., as direct children of `document.documentElement`). Searching only `document.querySelectorAll('body *')` misses these nodes.
- **Fix:**
  - Search entire document: `document.querySelectorAll('*')` instead of `document.querySelectorAll('body *')`
  - Walk up to `documentElement` (15 levels deep), catch `fixed/absolute/sticky` + z-index ≥20 + area >10% viewport
  - Fallback: remove text element's parent if no large container found
  - Added indefinite `setInterval` guard (500ms ticks) that continuously polls for and removes modal for entire test duration
- **Files:** `close-home-dialog.yaml`, `i2i-enter-prompt.yaml`, `image-to-image-optimized-part1.yaml`
- **Commit:** `752c0e2`

### RemixAI MCP Modal Fix (2026-06-01)
- **Problem:** RemixAI `master-home-check.yaml` desktop test failing at "MCP promo dialog title is no longer blocking the page". The MCP promo modal renders via React portal outside `document.body`, so `document.querySelectorAll('body *')` in `close-anniversary-modal.yaml` missed it.
- **Fix:** Applied same pattern as ChromaStudio: `document.querySelectorAll('*')` instead of `document.querySelectorAll('body *')`, walk up to `document.documentElement` (15 levels) instead of `document.body` (12).
- **Verification:** `master-home-check` desktop passes on remixai.io after fix.
- **Commit:** `847ae52` in maestro-studio

### Daily Maestro Tests Runner Bugs (2026-06-01)
- **Missing DISPLAY/Xvfb setup:** Script didn't ensure `DISPLAY` was set or Xvfb was running, causing all desktop tests to fail with `SessionNotCreatedException: Chrome instance exited`.
- **Missing Chrome wrapper PATH:** Script didn't prepend the Chrome wrapper directory to PATH, so bare `/usr/bin/chromium-browser` was used which can fail in cron environments.
- **Mobile `find` returning directories:** `find ... -name "*master*" | head -1` returned the `masters` directory itself (matching `*master*`) instead of files inside it. Added `-type f` to all `find` commands.
- **Broken `grep` regex:** `grep -v "ios\|mobile"` doesn't work in basic regex mode. Changed to `grep -v -E "ios|mobile"`.
- **Mobile test selection:** Script preferred iOS Safari tests over Android/Waydroid tests and didn't reset `MOBILE_SMOKE` between products, causing test bleed-over. Fixed to prefer Waydroid/Android and reset variable per product.
- **Status:** Script fixed locally in workspace.
### MaxStudio Homepage CTA Change (2026-05-31)
- **Problem:** `ensure-internal-mode.yaml` asserts "Generate" is visible on MaxStudio homepage, but UI now shows "Start Creating".
- **Fix:** Check for either "Generate" OR "Start Creating" via `evalScript` + `assertTrue` instead of `extendedWaitUntil` on "Generate" only.
- **File:** `maxstudio/shared/ensure-internal-mode.yaml`
- **Commit:** `243a0c9`

### Chrome/CDP Infrastructure Cleanup Pattern
- **Observation:** Zombie Chrome processes (10+) and temp profile directories (41+) accumulate after failed runs, causing `SessionNotCreatedException: Chrome instance exited` on subsequent runs.
- **Action:** `killall -9 chrome chromium-browser chromedriver chrome_crashpad_handler && rm -rf /tmp/maestro-chrome-profile.*` restores Chrome startup capability.
- **Note:** Selenium Chrome 149.0.7827.54 binary works correctly when launched via its `chrome-wrapper` script (sets `LD_LIBRARY_PATH`). Direct `chrome` binary call may fail due to missing shared libs.

