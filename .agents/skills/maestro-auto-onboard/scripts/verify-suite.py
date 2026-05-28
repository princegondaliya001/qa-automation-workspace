#!/usr/bin/env python3
"""
verify-suite.py — Phase 3: Verification & Auto-Fix
Runs maestro tests, reads debug/screenshots, suggests fixes, retries up to 3x.
Usage: python3 verify-suite.py --suite-dir ./suite --maestro-binary maestro --max-retries 3
"""
import argparse, json, os, re, subprocess, sys, time
from pathlib import Path
import common


def run_maestro(suite, flow, binary, env):
    dd = f"/tmp/maestro-debug-{int(time.time())}"
    os.makedirs(dd, exist_ok=True)
    try:
        r = subprocess.run(f"{binary} test {suite}/{flow} --debug-output {dd}", shell=True, capture_output=True, text=True, timeout=120, env=env)
        return {"rc": r.returncode, "out": r.stdout, "err": r.stderr, "dd": dd}
    except subprocess.TimeoutExpired:
        return {"rc": 1, "out": "", "err": "TIMEOUT", "dd": dd}


def find_screenshots(dd):
    return sorted([os.path.join(dd, f) for f in os.listdir(dd) if f.endswith(".png")]) if os.path.isdir(dd) else []


def analyze_failure(stdout, stderr):
    c = stdout + "\n" + stderr
    sugs = []
    for pat, et in [(r"No elements found for '(.*?)'", "missing"), (r"Element not found: (.*?)", "missing"),
                     (r"Timeout waiting for '(.*?)'", "timeout"), (r"App is not running", "launch"), (r"Failed to launch app", "launch")]:
        for m in re.finditer(pat, c, re.I):
            sel = m.group(1).strip() if m.lastindex else ""
            if et == "missing": sugs.append({"type": "missing", "sel": sel, "sug": f"'{sel}' not found. Try partial text or coordinate fallback."})
            elif et == "timeout": sugs.append({"type": "timeout", "sel": sel, "sug": f"Timeout on '{sel}'. Add wait or assertVisible first."})
            else: sugs.append({"type": "launch", "sug": "App launch failed. Check APP_ID or install."})
    if not sugs: sugs.append({"type": "generic", "sug": "Unknown failure. Check screenshots and retry."})
    return sugs


def apply_fixes(flow_path, sugs):
    if not os.path.exists(flow_path): return False
    content = Path(flow_path).read_text(); mod = False
    for s in sugs:
        if s["type"] == "missing" and s["sel"] and s["sel"] in content:
            old = s["sel"]; new = old[:10] + ".*" if len(old) > 10 else ".*" + old[-10:]
            content = content.replace(f'- tapOn: "{old}"', f'- tapOn: "{new}"')
            content = content.replace(f'- assertVisible: "{old}"', f'- assertVisible: "{new}"')
            mod = True
        elif s["type"] == "timeout" and "waitForAnimationToEnd" not in content:
            content = content.replace("appId:", "appId:\n- waitForAnimationToEnd"); mod = True
    if mod: Path(flow_path).write_text(content)
    return mod


def main():
    p = argparse.ArgumentParser(); p.add_argument("--suite-dir", required=True); p.add_argument("--maestro-binary", default="maestro"); p.add_argument("--max-retries", type=int, default=3); p.add_argument("--output", default="verification-report.json")
    a = p.parse_args()
    suite = Path(a.suite_dir)
    if not (suite / "master-dynamic.yaml").exists(): print(f"[ERROR] master-dynamic.yaml not found", file=sys.stderr); sys.exit(1)
    flows = ["master-dynamic.yaml"]
    scenario_flows = []
    if (suite / "flows" / "scenarios").exists():
        scenario_flows = [f"flows/scenarios/{f.name}" for f in sorted((suite / "flows" / "scenarios").iterdir()) if f.suffix == ".yaml"]
    flows += scenario_flows
    shared = [f"shared/{f.name}" for f in sorted((suite / "shared").iterdir()) if f.suffix == ".yaml"] if (suite / "shared").exists() else []
    env = {**os.environ}
    cp = suite / "config" / "config.yaml"
    if cp.exists():
        m = re.search(r'projectId:\s*([\w-]+)', cp.read_text())
        if m: env["PROJECT_ID"] = m.group(1)
    results = []
    for flow in flows:
        fp = suite / flow
        if not fp.exists(): continue
        print(f"[INFO] Testing {flow} ..."); attempt = 0; passed = False; fsugs = []; fss = []
        while attempt < a.max_retries and not passed:
            attempt += 1; res = run_maestro(str(suite), flow, a.maestro_binary, env); ss = find_screenshots(res["dd"]); fss.extend(ss)
            if res["rc"] == 0: passed = True; print(f"       PASS ({attempt})")
            else:
                print(f"       FAIL ({attempt})"); sugs = analyze_failure(res["out"], res["err"]); fsugs = sugs
                for s in sugs: print(f"       Suggestion: {s['sug']}")
                if attempt < a.max_retries:
                    if apply_fixes(str(fp), sugs): print("       Auto-fix applied, retrying...")
                    else: print("       No auto-fix.")
        results.append({"flow": flow, "passed": passed, "attempts": attempt, "suggestions": fsugs, "screenshots": fss})
    for flow in shared:
        fp = suite / flow
        if not fp.exists(): continue
        print(f"[INFO] Testing shared {flow} ...")
        res = run_maestro(str(suite), flow, a.maestro_binary, env); ss = find_screenshots(res["dd"])
        results.append({"flow": flow, "passed": res["rc"] == 0, "attempts": 1, "suggestions": [] if res["rc"] == 0 else analyze_failure(res["out"], res["err"]), "screenshots": ss})
    report = {"suite_dir": str(suite), "binary": a.maestro_binary, "max_retries": a.max_retries, "total": len(results), "passed": sum(1 for r in results if r["passed"]), "failed": sum(1 for r in results if not r["passed"]), "results": results}
    with open(a.output, "w") as f: json.dump(report, f, indent=2)
    print(f"[DONE] {a.output} — passed={report['passed']}/{report['total']}")
    if report["failed"] > 0: print(f"       {report['failed']} flow(s) need human review."); sys.exit(1)

if __name__ == "__main__": main()
