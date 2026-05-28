# Fallback Handbook

When auto-discovery fails, use these ordered fallbacks. Each fallback includes when to apply it and what to report.

## No Project ID Found

### Fallback Chain
1. **Try API interception** (Phase 2) — intercept actual network request headers
2. **Try `.env` defaults** — scan for `NEXT_PUBLIC_*` or `VITE_*` with "project" in name
3. **Try hardcoded guesses** based on repo name / org:
   - Repo name contains "max" → `maxStudio`
   - Repo name contains "remix" → `remixAi`
   - Repo name contains "chroma" → `chroma`
   - Repo name contains "deep" → `deepswapper`
   - Repo name contains "face" → `faceswapper`
   - Repo name contains "amp" → `ampere`
4. **Use `default`**

### Reporting
```
⚠️ Project ID auto-discovery failed. Used fallback: <value>
Confidence: LOW — verify by checking API headers manually
```

## No Test Mode Found

### Fallback Chain
1. **Try URL param probe**: `?testMode=true`, `?demo=true`, `?internal=true`
2. **Check env vars**: `NEXT_PUBLIC_TEST_MODE`, `ENABLE_TEST`
3. **Check for bypass functions** in code: search for `bypass`, `skip`, `demo`
4. **Mark as "needs credentials"**

### Action
- Generate `auth.yaml` anyway with placeholder credentials
- Flag in report: "No test mode detected — may need real credentials for full suite"
- If app is public (no auth required), skip auth flow entirely

## OAuth Detected

### Fallback
- **Flag immediately**: "OAuth login requires manual token / session setup"
- Generate placeholder `auth-oauth.yaml` with comments only
- Do NOT attempt automated OAuth login (impossible without tokens)

### Reporting
```
🔐 OAuth detected (Google/GitHub/Apple). Auth flow requires manual setup.
Generated: shared/auth-oauth-placeholder.yaml (commented out in master)
```

## App Won't Start Locally

### Fallback Chain
1. **Check for build errors** — read `npm run build` output
2. **Try different port** — port may be in use
3. **Try `npm run dev` with `NODE_ENV=development`**
4. **Use provided base URL** — skip local dev entirely
5. **Check if app requires env vars** — missing `.env.local`?

### Action
- If base URL was provided by Prince, use it directly
- If only repo URL was provided, report: "App requires manual env setup. Please provide base URL or .env file."

## Selector Keeps Failing After 3 Retries

### Fallback Chain
1. **Retry with partial text match** — use first 10 chars + `.*` regex
2. **Retry with coordinate-based tap** — use CDP bounding box
3. **Retry with `id` or `class` selector** — use `id: "element-id"` or `class: "btn-primary"`
4. **Flag for human review**

### Action
- Keep screenshots from all 3 attempts
- Report: "Selector <X> failed 3 times. Screenshots saved to /tmp/maestro-debug-*."
- Do NOT modify generated flow further — risk of breaking other selectors

## SPA with Client-Side Routing

### Fallback
- After navigation (`tapOn: "Dashboard"`), wait for `networkIdle` or animation end
- Use `waitForAnimationToEnd` before assertions
- Use `extendedWaitUntil:
    visible: "Some Text"
    timeout: 10000`
- If route changes via history API but no page reload, trigger navigation via `evalScript: window.location.href = '/dashboard'`

## Missing Dependencies (npm install fails)

### Fallback
- Run `npm install --legacy-peer-deps`
- If still fails, check for `yarn.lock` or `pnpm-lock.yaml` — use appropriate package manager
- Report: "Dependency install failed. Package manager mismatch suspected."

## No Routes Detected (Empty pages/ directory)

### Fallback
- Framework may use config-based routing (e.g., Vue router config, React Router in code)
- Search for `<Route`, `createBrowserRouter`, `vue-router` in code
- Infer routes from router config file
- If still no routes, generate smoke test for `/` only

## Network / API Errors During Scanning

### Fallback
- If API calls fail (CORS, 401, 404), app may need VPN or whitelist
- Report: "API unreachable during scan. Selectors extracted from static HTML only."
- Confidence lowered to 60%
