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

| Repo | Dev Branch URL |
|------|---------------|
| chroma-studio-frontend-nextjs | https://style-transfer-git-dev-nextbasecores-projects.vercel.app |
| max-v2 | https://max-v2-git-dev-nextbasecores-projects.vercel.app |
| remix-studio-nextjs | https://remixai-git-dev-nextbasecores-projects.vercel.app |
| faceswapper-ai | https://faceswapper-ai-git-dev-nextbasecores-projects.vercel.app |
| ampere-sh | https://ampere-sh-5px3-git-dev-paradoxs-projects-657e7e56.vercel.app |
| deepswapper-ai-nextjs | (none yet — falls back to production) |

**Daily cron jobs remain on production URLs.** Only commit-watcher triggered dev branch testing uses staging URLs.

## Local skills

- Chroma Studio skill is installed at `/root/.openclaw/workspace/.agents/skills/chroma-studio/SKILL.md`; it uses repo path `/root/.openclaw/workspace/repos/chroma-studio-frontend-nextjs`, Discord failed queue `#testing-automation-failed` / `1498991059227774986`, and live `https://api.chromastudio.ai/model-schema` with `x-project-id: default` as source of truth.
- MaxStudio / max-v2 skill is installed at `/root/.openclaw/workspace/.agents/skills/max-v2/SKILL.md`; it uses repo path `/root/.openclaw/workspace/repos/max-v2`, triggers for `projectId="maxStudio"`, watches the same Discord failed queue, and uses live `https://api.chromastudio.ai/model-schema` with `x-project-id: maxStudio` as source of truth.
- RemixAI schema-solve skill is installed at `/root/.openclaw/workspace/.agents/skills/remix-schema-solve/SKILL.md`; it uses repo path `/root/.openclaw/workspace/repos/remix-studio-nextjs`, watches the same Discord failed queue with `requireMention=false`, and uses live `https://api.chromastudio.ai/model-schema` with `x-project-id: remixAi` as the primary source of truth.
- Failed-automation queue orchestration skill is installed at `/root/.openclaw/workspace/.agents/skills/failed-automation-queue/SKILL.md`; it coordinates ChromaStudio, MaxStudio, RemixAI, DeepSwapper/Maestro failures from Discord `#testing-automation-failed`, tracks FIFO state in `/root/.openclaw/workspace/state/failed-automation-queue.json`, and includes `scripts/queue.py` for add/list/update.
- Sentry `security-review` skill is installed and ready from `agents-skills-personal` (`/root/.agents/skills/security-review/SKILL.md`, symlinked for OpenClaw). Prince asked on 2026-05-20 to use it all the time; for code/repo changes, especially before finalizing patches or reviews, load/use `security-review` when security implications are plausible.
- Prince’s failed-automation policy from 2026-05-20: for Discord/Captain Hook errors, fetch/pull relevant frontend/product repo context as source of truth, but avoid frontend code changes unless clearly necessary; prefer clean Maestro Studio automation fixes. Resolve all related errors first, run verification + security review, then push only when clean/safe. Maintain clean code/file/folder structure and do not commit temp/debug/unrelated files. Default queue execution must be strict FIFO/sequential: solve one item/group at a time; do not spawn multiple parallel fix agents unless Prince explicitly asks for parallel work. Duplicate alerts with the same root cause may be grouped under the one active resolver.
- Anthropic `skill-creator` skill is installed and ready from `agents-skills-personal` (`/root/.agents/skills/skill-creator/SKILL.md`, symlinked for OpenClaw). Prince asked on 2026-05-20 to use it to create/improve skills for recurring issue patterns.

## Current Status (2026-05-28)

**Trattoria Sostanza** (`princegondaliya001/trattoria-sostanza`) — Blog fully implemented and live. Navbar, blog listing page (`/blog`), individual post pages (`/blog/[slug]`), 6 rich blog posts, multiple CTA buttons throughout. Onboarding to Maestro Studio testing in progress via auto-onboard skill.

**Maestro Auto-Onboard skill** — 4 bugs fixed and committed to workspace repo (quick_validate.py, verify-suite.py, generate-flows.py, scan-app.py).

## Repo Sync Status (2026-05-28)
| Repo | Status |
|------|--------|
| chroma-studio-frontend-nextjs | ✅ Pulled latest |
| max-v2 | ✅ Committed WIP → pulled → merged → pushed |
| remix-studio-nextjs | ✅ Committed WIP → pulled → merged → pushed |
| maestro-studio | ✅ Already up to date |
| trattoria-sostanza | ✅ Blog implemented, pushed |

### Resolved merge conflicts:
- max-v2: accepted remote deletion of `src/app/api/notify-interest/route.ts` (had hardcoded webhook)
- remix: accepted remote deletion of `src/app/api/submit-interest/route.ts` (had hardcoded webhook)
