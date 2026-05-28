#!/usr/bin/env python3
"""
discover-project.py — Phase 1: Deep Repo Analysis
Usage: python3 discover-project.py --repo URL --output report.json
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
import common

DEFAULT_IDS = ["default", "maxStudio", "remixAi", "chroma", "deepswapper", "faceswapper", "ampere"]


def clone(repo_url, dest):
    out, err, rc = common.run_cmd(f"git clone --depth 1 {repo_url} {dest}", timeout=120)
    if rc != 0:
        print(f"[ERROR] git clone failed: {err}", file=sys.stderr); sys.exit(1)
    return dest


def discover_framework(root):
    pkg = common.read_json(os.path.join(root, "package.json"))
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    fw = "nextjs" if "next" in deps else "react" if "react" in deps else "vue" if "vue" in deps else "nuxt" if "nuxt" in deps else "svelte" if "svelte" in deps else "unknown"
    return {"framework": fw, "scripts": list(pkg.get("scripts", {}).keys()), "deps": list(deps.keys())[:30]}


def discover_routes(root, fw):
    routes = []
    if fw == "nextjs":
        for d in ["pages", "app"]:
            dp = os.path.join(root, d)
            if os.path.isdir(dp):
                for dp2, _, fnames in os.walk(dp):
                    for f in fnames:
                        if f.endswith((".tsx", ".ts", ".jsx", ".js")):
                            r = "/" + os.path.relpath(os.path.join(dp2, f), dp).replace("index", "").replace(".tsx", "").replace(".ts", "").replace(".jsx", "").replace(".js", "").replace("\\", "/").strip("/")
                            r = re.sub(r"/\(.*\)/", "/", r)
                            r = re.sub(r"/\[.*?\]", "/<param>", r)
                            if r not in routes: routes.append(r)
    if "/" not in routes: routes.insert(0, "/")
    return sorted(routes)


def discover_env(root):
    env = {}
    for fpath in common.find_files(root, r"\.env")[:5]:
        for line in common.read_text(fpath).splitlines():
            m = re.match(r'^([A-Z_][A-Z0-9_]*)=(.+)$', line.strip())
            if m and any(k in m.group(1) for k in ["API", "PROJECT", "URL", "BASE"]):
                env[m.group(1)] = m.group(2).strip('"\' ')
    return env


def discover_project_id(root, env):
    cands = []
    for k, v in env.items():
        if "PROJECT" in k and v:
            cands.append({"value": v, "source": k, "conf": 0.95})
    for hit in common.grep_code(root, r'projectId["\']?\s*[:=]\s*["\']([a-zA-Z0-9_-]+)["\']')[:5]:
        m = re.search(r'["\']([a-zA-Z0-9_-]+)["\']', hit["text"])
        if m and m.group(1) not in [c["value"] for c in cands]:
            cands.append({"value": m.group(1), "source": f"code:{hit['file']}", "conf": 0.85})
    return cands


def discover_auth(root):
    scores = {}
    for atype, pat in {"oauth": r'(signIn|OAuth|Google|GitHub|sso|oauth)', "email": r'(email|password|login|signin|auth)', "public": r'(public|noAuth|guest)'}.items():
        scores[atype] = len(common.grep_code(root, pat, max_files=20))
    detected = max(scores, key=scores.get)
    return {"detected": detected if scores[detected] > 0 else "unknown", "scores": scores}


def discover_test_mode(root):
    hits = common.grep_code(root, r'(testMode|test_mode|bypass|demo|skipAuth)', max_files=30)
    return {"found": len(hits) > 0, "hits": hits[:10]}


def discover_api_url(root, env):
    for k, v in env.items():
        if "API" in k and "URL" in k: return v
    hits = common.grep_code(root, r'(api\.chromastudio\.ai|api\.maxstudio\.ai|localhost:\d+)', max_files=10)
    if hits:
        m = re.search(r'(https?://[^"\'\s]+)', hits[0]["text"])
        if m: return m.group(1)
    return None


def main():
    p = argparse.ArgumentParser(); p.add_argument("--repo"); p.add_argument("--local"); p.add_argument("--output", default="discovery-report.json")
    a = p.parse_args()
    if not a.repo and not a.local:
        print("[ERROR] Provide --repo or --local", file=sys.stderr); sys.exit(1)
    tmpdir = None; root = a.local
    if a.repo:
        tmpdir = tempfile.mkdtemp(prefix="maestro-discover-")
        print(f"[INFO] Cloning {a.repo} ..."); root = clone(a.repo, tmpdir)
    print("[INFO] Analyzing repo...")
    fw = discover_framework(root); routes = discover_routes(root, fw["framework"])
    env = discover_env(root); pids = discover_project_id(root, env)
    auth = discover_auth(root); tm = discover_test_mode(root); api = discover_api_url(root, env)
    report = {"source": {"repo": a.repo, "local": a.local, "analyzed_at": common.run_cmd("date -u +%Y-%m-%dT%H:%M:%SZ")[0]},
              "framework": fw, "routes": routes, "env_vars": env, "project_id_candidates": pids,
              "auth": auth, "test_mode": tm, "api_url": api, "default_project_ids": DEFAULT_IDS}
    with open(a.output, "w") as f: json.dump(report, f, indent=2)
    print(f"[DONE] {a.output} — fw={fw['framework']}, routes={len(routes)}, pids={len(pids)}")
    if tmpdir: shutil.rmtree(tmpdir, ignore_errors=True)

if __name__ == "__main__": main()
