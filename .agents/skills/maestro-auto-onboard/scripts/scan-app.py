#!/usr/bin/env python3
"""
scan-app.py — Phase 2: Live App Scanning via Headless Chromium
Usage: python3 scan-app.py --base-url URL --routes-file routes.json --output selector-map.json
   or: python3 scan-app.py --start-cmd "npm run dev" --port 3000 --routes-file routes.json --output selector-map.json
"""
import argparse, json, os, re, subprocess, sys, time
import common


def wait_url(url, max_wait=60):
    for _ in range(max_wait):
        try:
            import urllib.request
            # Try HEAD first, fall back to GET on 405 or failure
            try:
                req = urllib.request.Request(url, method="HEAD")
                urllib.request.urlopen(req, timeout=2)
                return True
            except Exception:
                urllib.request.urlopen(url, timeout=2)
                return True
        except Exception:
            time.sleep(1)
    return False


def start_dev(cmd, port, cwd):
    print(f"[INFO] Starting: {cmd}")
    env = {**os.environ, "PORT": str(port)}
    proc = subprocess.Popen(cmd, shell=True, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    url = f"http://localhost:{port}"
    if not wait_url(url, 60):
        proc.terminate(); print(f"[ERROR] Dev server failed on {url}", file=sys.stderr); sys.exit(1)
    print(f"[INFO] Dev ready at {url}"); return proc, url


def fetch_dom(url, route, out_dir):
    full = url.rstrip("/") + route
    sm = {"route": route, "url": full, "accessible": False, "buttons": [], "inputs": [], "links": [], "dialogs": [], "text_blocks": [], "api_headers": {}}
    html, err, rc = common.run_cmd(f"curl -s -L --max-time 15 '{full}'", timeout=20)
    if rc != 0 or not html:
        print(f"[WARN] Could not fetch {full}: {err}"); return sm
    sm["accessible"] = True
    for m in re.finditer(r'<button[^>]*>(.*?)</button>', html, re.DOTALL | re.I):
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        cls = re.search(r'class=["\']([^"\']+)["\']', m.group(0))
        sm["buttons"].append({"text": text, "tag": "button", "class": cls.group(1) if cls else None})
    for m in re.finditer(r'<input[^>]*>', html, re.I):
        tag = m.group(0); inp = {"tag": "input"}
        for attr in ["type", "name", "placeholder", "id", "class"]:
            mm = re.search(rf'{attr}=["\']([^"\']+)["\']', tag, re.I)
            if mm: inp[attr] = mm.group(1)
        if "type" not in inp: inp["type"] = "text"
        sm["inputs"].append(inp)
    for m in re.finditer(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.I):
        href, text = m.group(1), re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if href.startswith(("/", "http")): sm["links"].append({"href": href, "text": text})
    for kw in ["modal", "dialog", "overlay", "popup", "toast", "banner"]:
        if re.search(rf'class=["\'][^"\']*{kw}[^"\']*["\']', html, re.I):
            sm["dialogs"].append({"type": kw, "detected_by": "class_keyword"})
    for m in re.finditer(r'<(h[1-6]|p|span)[^>]*>(.*?)</\1>', html, re.DOTALL | re.I):
        text = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if text and len(text) < 200: sm["text_blocks"].append({"tag": m.group(1), "text": text})
    ss = os.path.join(out_dir, f"ss_{route.replace('/', '_').strip('_') or 'home'}.png")
    _, _, rc = common.run_cmd(f'google-chrome --headless --disable-gpu --screenshot={ss} --window-size=1280,720 --hide-scrollbars "{full}" 2>/dev/null', timeout=20)
    sm["screenshot"] = ss if rc == 0 and os.path.exists(ss) else None
    return sm


def intercept_headers(url, route):
    full = url.rstrip("/") + route
    html, _, rc = common.run_cmd(f"curl -s -L --max-time 10 '{full}'", timeout=15)
    h = {}
    if rc == 0:
        for pat in [r'x-project-id["\']?\s*[:=]\s*["\']([\w-]+)["\']', r'projectId["\']?\s*[:=]\s*["\']([\w-]+)["\']']:
            m = re.search(pat, html, re.I)
            if m: h["x-project-id"] = m.group(1); break
    return h


def main():
    p = argparse.ArgumentParser(); p.add_argument("--base-url"); p.add_argument("--start-cmd"); p.add_argument("--port", type=int, default=3000); p.add_argument("--cwd"); p.add_argument("--routes-file", required=True); p.add_argument("--output", default="selector-map.json"); p.add_argument("--test-mode-param", default="testMode=true"); p.add_argument("--screenshot-dir", default="/tmp/maestro-screenshots")
    a = p.parse_args()
    if not a.base_url and not a.start_cmd:
        print("[ERROR] Provide --base-url or --start-cmd", file=sys.stderr); sys.exit(1)
    os.makedirs(a.screenshot_dir, exist_ok=True)
    with open(a.routes_file) as f: routes = json.load(f)
    if isinstance(routes, dict) and "routes" in routes: routes = routes["routes"]
    dev_proc = None; base = a.base_url
    if a.start_cmd: dev_proc, base = start_dev(a.start_cmd, a.port, a.cwd)
    all_maps = []
    for route in routes:
        print(f"[INFO] Scanning {route} ..."); sm = fetch_dom(base, route, a.screenshot_dir)
        sm["api_headers"] = intercept_headers(base, route); all_maps.append(sm); time.sleep(1)
    test_url = base.rstrip("/") + "/?" + a.test_mode_param
    print(f"[INFO] Probing test mode: {test_url}")
    th, _, rc = common.run_cmd(f"curl -s -L --max-time 10 '{test_url}'", timeout=15)
    tm = bool(re.search(r'(test|demo|internal|bypass|dev)', th, re.I)) if rc == 0 else False
    result = {"base_url": base, "routes_scanned": len(all_maps), "selector_map": all_maps, "test_mode_probe": {"url": test_url, "detected": tm}, "screenshot_dir": a.screenshot_dir}
    with open(a.output, "w") as f: json.dump(result, f, indent=2)
    print(f"[DONE] {a.output} — routes={len(all_maps)}, ss={a.screenshot_dir}")
    if dev_proc: dev_proc.terminate(); dev_proc.wait(timeout=5)

if __name__ == "__main__": main()
