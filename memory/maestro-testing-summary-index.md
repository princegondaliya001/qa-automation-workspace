# Maestro Testing Automation Summary Index

This compact memory note is distilled from Prince's exported testingautomation_bot Telegram history and is intended for reliable recall.

## Identity and user

- User: Prince. Call him Prince only.
- Assistant: QA Tester 🧪.
- Role: QA automation/test agent for Maestro, cron, ChromaStudio, MaxStudio, RemixAI, visual noVNC, and Waydroid/mobile captesting.

## Repositories

Repos restored under `/root/.openclaw/workspace/repos/`:

- `chroma-studio-frontend-nextjs` from `nextbasecore/chroma-studio-frontend-nextjs`
- `max-v2` from `nextbasecore/max-v2`
- `remix-studio-nextjs` from `nextbasecore/remix-studio-nextjs`
- `maestro-studio` from `princegondaliya001/maestro-studio`

Do not repeat or reuse old PATs from chat history; they were exposed and should be rotated.

## Maestro Studio structure

- `chromastudio/` — largest ChromaStudio Maestro automation suite.
- `maxstudio/` — MaxStudio Maestro automation suite.
- `remixai/` — RemixAI route/model/tool coverage.
- Main master files: `chromastudio/master-dynamic.yaml`, `maxstudio/master-dynamic.yaml`, `remixai/master-dynamic.yaml`.
- Common pattern: `flows/masters`, `flows/scenarios`, `shared`, `schema/desktop`, `schema/mobile`, `tests`.

## Restored skill

Maestro skill file exists at:

- `/root/.openclaw/workspace/repos/maestro-studio/skills/chromastudio-maxstudio-desktop-maestro/SKILL.md`

It says daily cron automation must use desktop web only (`appId: web`) and must not accidentally use Waydroid, Android, iOS Simulator, mobile Safari, mobile viewport sizes, or device emulation for the daily setup. Mobile/Waydroid captesting is separate unless Prince asks.

## Cron testing agents

OpenClaw cron jobs restored:

- `daily-maestro-studio-chromastudio-maxstudio-tests`: `0 7 * * *` Asia/Calcutta, isolated agent, desktop daily tests.
- `daily-maestro-generation-rotation-chromastudio-maxstudio`: `30 8 * * *` Asia/Calcutta, isolated agent, live desktop generation rotation.
- `maestro-self-healing-repair-agent`: `30 15 * * *` Asia/Calcutta, isolated repair agent.
- `run-inspector-maestro-cron-health-check`: `17 */6 * * *` Asia/Calcutta, isolated health checker, no live tests.

Discord webhook env is stored at `/root/.openclaw/workspace/state/maestro-discord.env` with restricted permissions. Never print webhook values. Alert reports must be redacted.

## Health check fix

The previous health-check cron timed out because Maestro syntax scanning walked too many mobile/iOS YAML files. It was patched to validate the desktop daily dry-run files only. Latest manual health run passed with failures 0 at:

- `/root/.openclaw/workspace/state/maestro-cron-health/20260511-112418`

Local `maestro-studio` commit for this fix:

- `b746024 Bound cron health Maestro syntax checks`

## RemixAI Happy Horse previous fix

Previous workspace implemented missing RemixAI route coverage for `/m/happy-horse-1-0`, desktop and mobile, with model ids:

- `alibaba-happy-horse-t2v`
- `alibaba-happy-horse-i2v`

Tests mentioned as passing in history: `model-route-coverage.test.js`, `coverage-report.test.js`, `direct-model-routes-contract.test.js`, `maestro-mobile-direct-model-routes.test.js`, YAML parse check. Need verify in current repo before claiming present.

## Visual monitor / noVNC

Previous visual monitor setup used:

- Xvfb
- x11vnc
- noVNC/websockify
- Chromium
- tmux session `visual-monitor`
- local-only noVNC on `127.0.0.1:6080`

Prince accesses from MacBook/Termius with SSH tunnel:

`ssh -L 6080:127.0.0.1:6080 root@138.199.175.88`

Then open local browser:

`http://127.0.0.1:6080/vnc.html`

The URL is opened in the MacBook browser, not typed inside the SSH shell.

## ChromaStudio login/captesting history

Reusable CDP login script exists in current repo:

- `scripts/chromastudio-login-cdp.mjs`

Previous captesting focused on ChromaStudio one T2I model `bria-3-2-t2i`:

- close dialog
- auth/login
- open exact model route
- verify/fill prompt
- enable Internal Mode
- click Generate only after Internal Mode verified ON

Desktop visible keep-open test previously passed. A key bug was Escape/close-dialog logic closing auth modal too early after `Log In & Create`; fixed by stronger CDP mouse events, isolated CDP port, safer modal handling, and real Internal Mode checkbox verification.

## Waydroid/mobile context

Waydroid was used for visible Android/mobile captesting, not for desktop daily cron. Previous blocker was Waydroid visible compositor/ADB/IP issue. Fix involved matching Waydroid resolution to visible Weston/mobile window; then Waydroid became visible with ADB connected at `192.168.240.112:5555`.

Previous mobile ChromaStudio captesting:

- Android Jelly browser in Waydroid
- exact Bria 3.2 T2I mobile page
- prompt filled
- Internal Mode turned ON and verified
- Generate clicked once only after Internal Mode ON
- final screenshot/history indicated generated results appeared with no visible error

Keep mobile/Waydroid scripts separate from desktop cron unless Prince explicitly asks for mobile cron or mobile captesting.

## Safety rules

- Never print tokens, PATs, Discord webhooks, passwords, emails from logs, or auth contents.
- Treat all secrets pasted in exported Telegram history as compromised.
- Daily desktop cron must not run mobile/Waydroid.
- Live generation may spend credits. Enforce Internal Mode before Generate and avoid live generation unless the intended cron/run explicitly requires it.
- Do not commit or push unless Prince asks, except local workspace memory/context commits are okay for assistant state.
