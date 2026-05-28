#!/usr/bin/env python3
"""
generate-flows.py — Phase 3: YAML Flow Generation from Selector Map
Usage: python3 generate-flows.py --selector-map sm.json --discovery disc.json --output-dir ./suite --suite-name myapp
"""
import argparse, json, os, re, sys
from pathlib import Path
import common


def safe(t): return re.sub(r'[^\w-]', '_', t.lower()).strip('_')


def auth_flow(sel_map, suite):
    login = next((r for r in sel_map.get("selector_map", []) if "/login" in r.get("route", "") or "/auth" in r.get("route", "")), None)
    if not login: return None
    lines = ["# Auto-generated auth", "appId: ${APP_ID}", "---", "# Auth flow"]
    ei = next((i for i in login.get("inputs", []) if "email" in [i.get("type", "").lower(), i.get("name", "").lower(), i.get("placeholder", "").lower()]), None)
    pi = next((i for i in login.get("inputs", []) if "password" in [i.get("type", "").lower(), i.get("name", "").lower(), i.get("placeholder", "").lower()]), None)
    sb = next((b for b in login.get("buttons", []) if any(w in b.get("text", "").lower() for w in ["sign in", "login", "submit", "continue"])), None)
    if ei: lines += [f'- tapOn: "{ei.get("placeholder", "Email")}"', '- inputText: "test@example.com"']
    if pi: lines += [f'- tapOn: "{pi.get("placeholder", "Password")}"', '- inputText: "password123"']
    lines.append(f'- tapOn: "{sb["text"] if sb else "Sign In"}"')
    lines.append("- assertVisible: \"Dashboard\"")
    return "\n".join(lines)


def nav_flow(sel_map):
    lines = ["# Auto-generated navigation", "appId: ${APP_ID}", "---", "# Navigate to homepage", "- launchApp"]
    home = next((r for r in sel_map.get("selector_map", []) if r.get("route", "") == "/"), None)
    if home:
        for b in home.get("buttons", []):
            if b.get("text"): lines.append(f'- assertVisible: "{b["text"]}"'); break
    else:
        lines.append("- assertVisible: \".*\"")
    return "\n".join(lines)


def close_dialogs_flow(sel_map):
    has_d = any(r.get("dialogs") for r in sel_map.get("selector_map", []))
    lines = ["# Auto-generated dialog dismissal", "appId: ${APP_ID}", "---", "# Close dialogs",
               "- runFlow:", "    when:", "      visible: \".*\"", "    commands:",
               '      - tapOn: "✕"', '      - tapOn: "Close"', '      - tapOn: "Dismiss"',
               '      - tapOn: "Got it"', '      - tapOn: "Skip"']
    if has_d: return "\n".join(lines)
    return "\n".join(lines[:2] + ["---", "# no-op"])


def scenario_flow(rd, suite):
    route = rd.get("route", "/"); sn = safe(route) or "homepage"
    lines = [f"# Scenario: {route}", "appId: ${APP_ID}", "---", f"# {suite} {sn} smoke",
             "- runFlow: shared/navigate-to-homepage.yaml", "- runFlow: shared/close-dialogs.yaml"]
    if route != "/": lines.append(f'- tapOn: "{route}"')
    asserted = False
    for b in rd.get("buttons", [])[:3]:
        t = b.get("text", "")
        if t and len(t) < 60: lines.append(f'- assertVisible: "{t}"'); asserted = True; break
    if not asserted:
        for tb in rd.get("text_blocks", [])[:3]:
            t = tb.get("text", "")
            if t and 5 < len(t) < 80: lines.append(f'- assertVisible: "{t}"'); asserted = True; break
    if not asserted: lines.append("- assertVisible: \".*\"")
    return sn + "-smoke.yaml", "\n".join(lines)


def master_dynamic(scenarios, suite, disc, has_auth_file):
    lines = ["# Auto-generated master", "appId: ${APP_ID}", "---", f"# Master: {suite}",
             "- runFlow: shared/navigate-to-homepage.yaml", "- runFlow: shared/close-dialogs.yaml"]
    if disc.get("auth", {}).get("detected") in ("email", "oauth") and has_auth_file:
        lines.append("- runFlow: shared/auth.yaml")
    for sf in scenarios: lines.append(f"- runFlow: flows/scenarios/{sf}")
    return "\n".join(lines)


def generate_config(disc, sel_map):
    base = sel_map.get("base_url", "http://localhost:3000")
    pid = disc.get("project_id_candidates", [{}])[0].get("value", "default") if disc.get("project_id_candidates") else "default"
    return {"baseUrl": base, "projectId": pid, "timeout": 30000, "env": {"APP_ID": "com.example.app"}}


def main():
    p = argparse.ArgumentParser(); p.add_argument("--selector-map", required=True); p.add_argument("--discovery", required=True); p.add_argument("--output-dir", required=True); p.add_argument("--suite-name", required=True)
    a = p.parse_args()
    sm = common.read_json(a.selector_map); disc = common.read_json(a.discovery)
    out = Path(a.output_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "shared").mkdir(exist_ok=True); (out / "flows" / "scenarios").mkdir(parents=True, exist_ok=True)
    created = []
    ay = auth_flow(sm, a.suite_name)
    if ay: (out / "shared" / "auth.yaml").write_text(ay); created.append(str(out / "shared" / "auth.yaml"))
    (out / "shared" / "navigate-to-homepage.yaml").write_text(nav_flow(sm)); created.append(str(out / "shared" / "navigate-to-homepage.yaml"))
    (out / "shared" / "close-dialogs.yaml").write_text(close_dialogs_flow(sm)); created.append(str(out / "shared" / "close-dialogs.yaml"))
    sfs = []
    for rd in sm.get("selector_map", []):
        route = rd.get("route", "/")
        if "/login" in route or "/auth" in route: continue
        fn, yaml = scenario_flow(rd, a.suite_name)
        (out / "flows" / "scenarios" / fn).write_text(yaml); created.append(str(out / "flows" / "scenarios" / fn)); sfs.append(fn)
    (out / "master-dynamic.yaml").write_text(master_dynamic(sfs, a.suite_name, disc, ay is not None)); created.append(str(out / "master-dynamic.yaml"))
    (out / "config").mkdir(exist_ok=True)
    cfg = generate_config(disc, sm)
    # Write YAML config without pyyaml dependency
    cfg_lines = [f"{k}: {v}" for k, v in cfg.items() if not isinstance(v, dict)]
    cfg_lines += ["env:"] + [f"  {k}: {v}" for k, v in cfg.get("env", {}).items()]
    (out / "config" / "config.yaml").write_text("\n".join(cfg_lines)); created.append(str(out / "config" / "config.yaml"))
    readme = f"# {a.suite_name} Maestro Suite (Auto-generated)\n\n## Files\n- master-dynamic.yaml\n- shared/\n- flows/scenarios/\n- config/config.yaml\n\n## Run\n```bash\nmaestro test {a.output_dir}/master-dynamic.yaml\n```\n"
    (out / "README.md").write_text(readme); created.append(str(out / "README.md"))
    summary = {"suite_name": a.suite_name, "output_dir": str(out), "files_created": created, "scenario_count": len(sfs), "has_auth": ay is not None, "config": cfg}
    with open(out / "generation-summary.json", "w") as f: json.dump(summary, f, indent=2)
    print(f"[DONE] {len(created)} files in {out}")
    for c in created: print(f"       {c}")

if __name__ == "__main__": main()
