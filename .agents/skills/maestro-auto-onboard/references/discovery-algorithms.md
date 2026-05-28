# Discovery Algorithms Reference

This document describes how the auto-discovery scripts find critical app metadata without human input.

## Finding Project ID

### 1. Environment Variable Scanning
- Files scanned: `.env`, `.env.local`, `.env.example`, `.env.production`, `.env.development`
- Patterns: `NEXT_PUBLIC_PROJECT_ID`, `VITE_PROJECT_ID`, `PROJECT_ID`, `PUBLIC_PROJECT_ID`
- Confidence: **95%** when found in `.env` with `API` or `URL` nearby

### 2. Codebase Grep
- Search files: `*.js`, `*.ts`, `*.tsx`, `*.jsx`, `*.json`
- Patterns:
  - `projectId\s*[:=]\s*["']([\w-]+)["']`
  - `x-project-id\s*[:=]\s*["']([\w-]+)["']`
  - `project_id\s*[:=]\s*["']([\w-]+)["']`
- Confidence: **85%** — may match hardcoded strings or variable names

### 3. API Interception (Phase 2)
- Start app, open Chromium DevTools Protocol (CDP)
- Monitor `fetch` / `XMLHttpRequest` network requests
- Extract `x-project-id` header from outbound API calls
- Confidence: **95%** — this is the runtime truth

### 4. Fallback Defaults
If no project ID found after above, try in order:
1. `default`
2. `maxStudio`
3. `remixAi`
4. `chroma`
5. `deepswapper`
6. `faceswapper`
7. `ampere`

## Finding Auth Type

### 1. DOM Analysis (Phase 2)
- Navigate to `/login`, `/auth`, `/signin`
- Detect input fields:
  - Email input (`type="email"` or placeholder containing "email")
  - Password input (`type="password"`)
  - Submit button (text: "Sign In", "Log In", "Continue")
- If found → **email auth**
- Confidence: **95%**

### 2. OAuth Detection
- Look for buttons with text:
  - "Sign in with Google", "Continue with Google"
  - "Sign in with GitHub", "Sign in with Apple"
  - Any button with `google`, `github`, `oauth`, `sso` in class or aria-label
- If found → **OAuth**
- Confidence: **90%**

### 3. Redirect Detection
- Navigate to `/dashboard` or `/app` without cookies
- If redirect to `/login` → auth required
- If page loads with content → **public**
- Confidence: **95%**

### 4. Codebase Grep (Phase 1)
- Search for auth library imports:
  - `next-auth`, `auth0`, `firebase/auth` → indicates auth type
  - `passport`, `jwt`, `bcrypt` → backend auth hints
- Confidence: **70%** (may be dev dependencies or unused)

## Finding Test Mode

### 1. Code Search (Phase 1)
- Patterns: `testMode`, `test_mode`, `testmode`, `bypass`, `demo`, `skipAuth`, `skip_auth`, `internal_mode`
- Look for URL param parsing: `new URLSearchParams(window.location.search).get('testMode')`
- Confidence: **80%**

### 2. URL Param Testing (Phase 2)
- Load `/?testMode=true`
- Compare DOM with normal load:
  - Different HTML → test mode active
  - Contains "test", "demo", "internal", "bypass" text → test mode active
  - No change → test mode not working or not present
- Confidence: **70%**

### 3. Environment Variable
- `.env` keys: `NEXT_PUBLIC_TEST_MODE`, `VITE_ENABLE_TEST`, `TEST_MODE`
- Confidence: **90%**

## Finding Selectors

### 1. CDP DOM Dump (Primary)
- Launch headless Chromium with `--remote-debugging-port=9222`
- Connect via CDP `DOM.getDocument`
- Recursively extract:
  - Elements with `id`, `class`, `aria-label`, `data-testid`
  - Visible text content
  - Bounding boxes for coordinate fallback
- Filter for interactive elements: `button`, `a`, `input`, `select`, `textarea`, `[role="button"]`
- Confidence: **90%**

### 2. HTML Static Parse (Fallback)
- Use `curl` to fetch raw HTML
- Regex extract `<button>`, `<input>`, `<a>` tags
- Parse `class`, `id`, `placeholder`, `name`, `href`
- Confidence: **70%** (misses client-rendered elements)

### 3. Screenshot Analysis (Human Fallback)
- If automated selector extraction fails, take screenshot
- Flag for human review with annotated screenshot
- Used when: SPA with heavy client-side rendering, canvas-based UI

## Handling Frameworks

### Next.js (App Router)
- Routes discovered from `app/` directory
- File conventions: `page.tsx`, `layout.tsx`, `loading.tsx`
- Dynamic segments: `[id]`, `[...slug]`, `[[...catchall]]`
- Route mapping: file path → URL path

### Next.js (Pages Router)
- Routes discovered from `pages/` directory
- Files: `index.tsx` → `/`, `about.tsx` → `/about`
- Dynamic routes: `[id].tsx` → `/:id`

### React (Vite/CRA)
- Routes must be inferred from router config or guessed
- Common patterns: `/`, `/login`, `/dashboard`, `/app`
- Look for `react-router-dom` usage in code

### Vue / Nuxt
- Nuxt: `pages/` directory similar to Next.js
- Vue: `router/index.js` or `<router-view>` config
- Look for `vue-router` imports

### SPA (Client-Side Routing)
- No distinct HTML per route from server
- Must use CDP to trigger client navigation (`window.history.pushState`)
- Wait for DOM mutations (`MutationObserver`) after navigation
- Use `assertVisible` with generous timeouts
