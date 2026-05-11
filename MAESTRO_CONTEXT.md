# Maestro Automation Context

Imported from Prince's Telegram export on 2026-05-11. Secrets from the export must be treated as compromised/redacted and not reused unless Prince provides fresh credentials.

## Repos to restore

Clone under `/root/.openclaw/workspace/repos/` when credentials are available:

- `https://github.com/nextbasecore/chroma-studio-frontend-nextjs`
- `https://github.com/nextbasecore/max-v2`
- `https://github.com/nextbasecore/remix-studio-nextjs`
- `https://github.com/princegondaliya001/maestro-studio`

Current fresh workspace check: these repos are not present yet, and unauthenticated GitHub access fails, likely private repos.

## Maestro Studio structure remembered

- `chromastudio/` — largest suite, ChromaStudio coverage.
- `maxstudio/` — active suite with schema generation coverage.
- `remixai/` — route/model/tool coverage.
- Main master files:
  - `chromastudio/master-dynamic.yaml`
  - `maxstudio/master-dynamic.yaml`
  - `remixai/master-dynamic.yaml`
- Pattern:
  - `flows/masters/` = stable aggregate checks
  - `flows/scenarios/` = auth/pricing/home/navigation
  - `shared/` = helpers/selectors/auth/result detection
  - `schema/desktop` + `schema/mobile` = schema-driven model/tool coverage
  - `tests/` = Python/Node validation scripts

## Completed in previous workspace/history

These were done in the old workspace; they are not guaranteed present in this fresh workspace until repos are restored:

1. RemixAI Happy Horse route drift fixed
   - Added `/m/happy-horse-1-0` desktop + mobile route YAML.
   - Added expected model ids:
     - `alibaba-happy-horse-t2v`
     - `alibaba-happy-horse-i2v`
   - Updated master route files and coverage tests.
   - Verification passed with drift `0`.

2. OpenClaw cron jobs registered previously
   - `daily-maestro-studio-chromastudio-maxstudio-tests`
   - `daily-maestro-generation-rotation-chromastudio-maxstudio`
   - `maestro-self-healing-repair-agent`
   - `run-inspector-maestro-cron-health-check`
   - Schedules used Asia/Calcutta.
   - Discord webhook reporting was wired previously, but webhook from chat should be rotated and not reused raw.

3. Visual monitoring stack previously installed/configured
   - Xvfb, x11vnc, noVNC/websockify, Chromium.
   - Local-only listener target: `127.0.0.1:6080` through SSH tunnel.
   - View command from laptop:
     - `ssh -L 6080:127.0.0.1:6080 root@138.199.175.88`
     - open `http://127.0.0.1:6080/vnc.html` in local browser.

4. ChromaStudio captesting temporary flows previously implemented
   - Desktop T2I smoke around `bria-3-2-t2i`.
   - Waydroid/mobile T2I smoke around `bria-3-2-t2i`.
   - Safety rule: only click Generate after auth + Internal Mode verified ON.
   - Desktop visible keep-open run passed.
   - Mobile/Waydroid run eventually passed after fixing Waydroid resolution/ADB and exact model URL flow.

5. Cron-side blockers previously fixed
   - Health check timeout caused by scanning too many mobile/iOS YAMLs; patched to desktop-relevant checks.
   - X display `:99` down causing Chrome startup failure; patched restore guard to auto-start Xvfb.
   - Daily suite then ran but failed on real app/test issues: pricing assertions and auth/internal-mode selectors.

## Known current blockers in this fresh workspace

- Repos are not cloned yet; GitHub private repo access needs fresh valid auth.
- Do not use old PATs/webhooks from imported chat; they are exposed and should be considered compromised.
- Need verify whether OpenClaw cron jobs still exist in this environment before claiming they are active.
- Need verify visual monitor/noVNC state before claiming it is running.

## Next best restoration order

1. Get fresh GitHub auth/PAT or gh login from Prince.
2. Clone/pull all 4 repos into `/root/.openclaw/workspace/repos/`.
3. Inspect `maestro-studio` actual state against remembered fixes.
4. Recreate missing scripts/cron/env only after verifying repo state.
5. Run smallest safe verification: health check/static tests first, then visible desktop run, then mobile/Waydroid only when needed.
