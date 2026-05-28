---
name: maestro-auto-onboard
description: Zero-touch or minimal-input onboarding of any new frontend project into Maestro Studio automation. Use when Prince says "add this new project to testing", "onboard this repo", "create Maestro flows for this app", or any request to automate a project with minimal information. Only needs repo URL or base URL — auto-discovers project ID, auth type, routes, selectors, test mode, and generates complete Maestro flows, verification, and cron integration without human intervention. Replaces the 5-phase manual onboarding with a self-discovery agent.
---

# Maestro Auto-Onboard

Onboard a brand-new frontend project into Maestro Studio with **minimal human input**.

---

## What you provide vs What we discover

### What you provide (10-20%)

| Input | Example | Required? |
|---|---|---|
| **Git repo URL** | `https://github.com/nextbasecore/newapp-frontend-nextjs` | **OR** base URL |
| **Base URL** | `https://newapp.chromastudio.ai` or `http://localhost:3000` | **OR** repo URL |
| **Project hint** | "It's a Chroma product" or "uses chromastudio API" | Optional |

**NOT required (auto-discovered):**
- Project ID → extracted from API calls or `.env` files
- Auth credentials → test mode is auto-detected, or app may be public
- Framework → read from `package.json`
- Routes → scanned from `pages/` or `app/` directory
- Selectors → dumped from live Chromium render
- Test mode → searched in codebase

### What we discover (80-90%)

| Discovery | How | Confidence | Time |
|---|---|---|---|
| **Framework** | Read `package.json`, `next.config.*`, `vite.config.*` | **100%** | Instant |
| **Routes / pages** | Scan `pages/` or `app/` directory | **95%** | 5-10s |
| **Project ID** | Intercept API calls or read `.env` files | **90%** | 30s |
| **Base URL** | Read `.env` files, `NEXT_PUBLIC_*` vars, or use provided URL | **90%** | 5s |
| **Auth type** | Render login page, detect OAuth vs email vs none | **95%** | 10s |
| **Test mode / bypass** | Check URL params, env vars, code references to `testMode` | **70%** | 15s |
| **All selectors** | Render page in Chromium, dump DOM, extract text/aria-label/class | **90%** | 2-3 min |
| **Forms and fields** | Detect `<input>`, `<textarea>`, `<select>` with labels/placeholders | **90%** | 10s |
| **Buttons** | Detect `<button>`, `<a>` with actionable text | **90%** | 10s |
| **Dialogs / popups** | Detect modal overlays on first load | **80%** | 5s |
| **Loading states** | Detect spinners, skeletons, progress bars | **70%** | 5s |

---

## The 3-phase self-discovery workflow

### Phase 1: Deep Repo Analysis

**What it does:**
1. `git clone <repo-url>`
2. Reads every config file:
   - `package.json` → framework, dependencies, scripts
   - `next.config.*` / `vite.config.*` / `nuxt.config.*` → routes, env vars
   - `.env*` files → API URLs, project IDs, feature flags
   - `tsconfig.json` → path aliases, root dir
3. Scans `pages/` or `app/` directory → builds complete route tree
4. Searches code for:
   - `testMode`, `test_mode`, `bypass`, `demo` → finds test mode logic
   - `api.chromastudio.ai`, `api.maxstudio.ai` → finds backend API
   - `x-project-id` → finds project ID constants
   - `login`, `auth`, `signin`, `oauth` → finds auth flow
5. Reports: framework, routes, env vars found, auth type, test mode availability, project ID

**Time:** 2-5 minutes
**Human interaction:** ZERO

#### Exact sub-agent spawn command
```bash
cd /root/.openclaw/workspace/.agents/skills/maestro-auto-onboard
python3 scripts/discover-project.py --repo <REPO_URL> --output /tmp/discovery-report.json
```

---

### Phase 2: Live App Scanning

**What it does:**
1. Start the app:
   - If repo has dev script: `npm run dev` on a free port
   - If only base URL provided: use that directly
2. Navigate to every discovered route with headless Chromium
3. At each page:
   - Wait for full load
   - Take screenshot
   - Dump full DOM
   - Extract interactive elements (buttons, inputs, links, dialogs)
4. Detect auth state:
   - Try `/dashboard` without login → redirect?
   - Detect login form fields
   - Detect OAuth buttons
5. Detect test mode:
   - Try `?testMode=true` on URLs
6. Intercept API calls:
   - Extract `x-project-id` from request headers
7. Build complete **selector map** (JSON)

**Time:** 5-10 minutes
**Human interaction:** ZERO

#### Exact sub-agent spawn command (with repo)
```bash
cd /tmp/maestro-onboard-<project>
python3 /root/.openclaw/workspace/.agents/skills/maestro-auto-onboard/scripts/scan-app.py \
  --start-cmd "npm run dev" --port 3001 --cwd . \
  --routes-file /tmp/discovery-report.json \
  --output /tmp/selector-map.json
```

#### Exact sub-agent spawn command (with base URL only)
```bash
python3 /root/.openclaw/workspace/.agents/skills/maestro-auto-onboard/scripts/scan-app.py \
  --base-url https://app.example.com \
  --routes-file /tmp/discovery-report.json \
  --output /tmp/selector-map.json
```

---

### Phase 3: Auto-Flow Generation + Verification

**What it does:**
1. Read selector map from Phase 2
2. Generate complete suite skeleton:
   ```
   <suite-name>/
     master-dynamic.yaml
     config/config.yaml
     README.md
     flows/scenarios/
       homepage-smoke.yaml
       login.yaml
       dashboard-smoke.yaml
       <tool>-create.yaml
     shared/
       auth.yaml
       navigate-to-homepage.yaml
       close-dialogs.yaml
   ```
3. Write YAML flows using selector map
4. Set `config.yaml` with auto-discovered `baseUrl` and `projectId`
5. Run verification:
   - `maestro test <suite>/master-dynamic.yaml --debug-output /tmp/debug`
   - If fails: read screenshot, fix selector, re-run
   - Retry up to 3 times per flow
6. Report: pass/fail per flow, screenshots, files created

**Time:** 5-15 minutes
**Human interaction:** ZERO (unless verification repeatedly fails)

#### Exact sub-agent spawn command
```bash
python3 /root/.openclaw/workspace/.agents/skills/maestro-auto-onboard/scripts/generate-flows.py \
  --selector-map /tmp/selector-map.json \
  --discovery /tmp/discovery-report.json \
  --output-dir /root/.openclaw/workspace/repos/maestro-studio/<suite-name> \
  --suite-name <suite-name>

python3 /root/.openclaw/workspace/.agents/skills/maestro-auto-onboard/scripts/verify-suite.py \
  --suite-dir /root/.openclaw/workspace/repos/maestro-studio/<suite-name> \
  --maestro-binary maestro \
  --max-retries 3 \
  --output /tmp/verification-report.json
```

---

## Fallbacks when auto-discovery fails

| Discovery Failed | Fallback | Human Needed? |
|---|---|---|
| Project ID not in API calls | Try `default`, `maxStudio`, `remixAi`, `deepswapper` | Maybe |
| Auth type unclear | Assume public (no auth) and skip login flow | No |
| Test mode not found | Skip test mode, use real credentials if available | Maybe |
| App won't start locally | Use provided base URL directly | No (if URL given) |
| Selector keeps failing after 3 retries | Flag for human review with screenshots | Yes |
| OAuth login detected | Note: "OAuth login requires manual token setup" | Yes |

For detailed fallback procedures, see `references/fallback-handbook.md`.
For discovery algorithm details, see `references/discovery-algorithms.md`.

---

## Example: Prince says "onboard https://github.com/nextbasecore/voiceclone-frontend-nextjs"

**What happens (zero human interaction):**

1. **Phase 1** — `discover-project.py` clones repo, reads `package.json` → Next.js 14, routes: /, /login, /dashboard, /clone, /history
   - Finds `.env.example` → `NEXT_PUBLIC_PROJECT_ID=voiceclone`
   - Finds `testMode` references → `?testMode=true` bypasses auth
   - **Time:** 2 min

2. **Phase 2** — `scan-app.py` starts `npm run dev` on port 3001
   - Opens `http://localhost:3001?testMode=true` in headless Chromium
   - Dumps DOM: "Voice Clone" h1, "Upload Audio" button
   - Intercepts API: `x-project-id: voiceclone` confirmed
   - **Time:** 5 min

3. **Phase 3** — `generate-flows.py` creates suite in `maestro-studio/voiceclone/`
   - `master-dynamic.yaml`, `shared/`, `flows/scenarios/clone-smoke.yaml`
   - `verify-suite.py` runs Maestro → passes
   - **Time:** 5 min

4. **Cron integration** — add `qa-voiceclone-desktop-nightly` at 8:30 PM IST

**Total time:** ~12 minutes  
**Human input:** 1 sentence (1 URL)

---

## Scripts in this skill

| Script | Phase | Purpose |
|---|---|---|
| `scripts/discover-project.py` | 1 | Clone repo, scan code, output JSON report |
| `scripts/scan-app.py` | 2 | Start dev server / use base URL, scan live app, output selector map |
| `scripts/generate-flows.py` | 3 | Read selector map, generate complete Maestro YAML suite |
| `scripts/verify-suite.py` | 3 | Run maestro test, auto-fix selectors, retry 3x, output pass/fail report |
| `scripts/common.py` | Shared | Utilities: run_cmd, read_json, grep_code, find_files |
| `scripts/quick_validate.py` | Validation | Validate skill integrity before use |

---

## Rules

- If auth requires OAuth (Google/GitHub), flag for human — can't auto-login
- If app has payment wall without test mode, flag for human — needs real credentials
- If selector fails 3 times, flag for human with screenshots
- Never commit/push without Prince confirmation
- Always run security-review on generated scripts
- Keep generated flows minimal: homepage, auth (if needed), 1-2 key tool flows
- Use `testMode` or bypass whenever found — avoids needing real credentials
- **No hardcoded secrets** in any generated YAML or script
- **Redact credentials** in all output reports
