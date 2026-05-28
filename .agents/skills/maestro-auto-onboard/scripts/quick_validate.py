#!/usr/bin/env python3
"""
quick_validate.py — Validate maestro-auto-onboard skill integrity
Checks:
- All required scripts exist and compile
- All reference files exist
- SKILL.md exists and contains required sections
- Scripts are under 200 lines

Usage:
    python3 quick_validate.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
REQUIRED_SCRIPTS = [
    "scripts/discover-project.py",
    "scripts/scan-app.py",
    "scripts/generate-flows.py",
    "scripts/verify-suite.py",
    "scripts/common.py",
]
REQUIRED_REFS = [
    "references/discovery-algorithms.md",
    "references/fallback-handbook.md",
]
REQUIRED_SKILL_SECTIONS = [
    "What you provide",
    "What we discover",
    "Phase 1",
    "Phase 2",
    "Phase 3",
    "Fallback",
    "Example",
]
MAX_LINES = 200

errors = []
warnings = []


def check_script(path):
    if not path.exists():
        errors.append(f"MISSING: {path}")
        return False
    content = path.read_text()
    lines = content.splitlines()
    if len(lines) > MAX_LINES:
        warnings.append(f"LONG ({len(lines)} lines): {path}")
    # Syntax check
    result = subprocess.run([sys.executable, "-m", "py_compile", str(path)], capture_output=True, text=True)
    if result.returncode != 0:
        errors.append(f"SYNTAX ERROR in {path}: {result.stderr}")
        return False
    print(f"  ✓ {path} ({len(lines)} lines, syntax OK)")
    return True


def check_ref(path):
    if not path.exists():
        errors.append(f"MISSING: {path}")
        return False
    lines = len(path.read_text().splitlines())
    print(f"  ✓ {path} ({lines} lines)")
    return True


def check_skill_md(path):
    if not path.exists():
        errors.append(f"MISSING: {path}")
        return False
    text = path.read_text()
    for section in REQUIRED_SKILL_SECTIONS:
        if section.lower() not in text.lower():
            warnings.append(f"SKILL.md may be missing section: '{section}'")
    print(f"  ✓ {path} ({len(text.splitlines())} lines)")
    return True


def main():
    print("=" * 50)
    print("Maestro Auto-Onboard Skill Validation")
    print("=" * 50)

    print("\n--- Scripts ---")
    all_ok = True
    for script in REQUIRED_SCRIPTS:
        all_ok &= check_script(SKILL_DIR / script)

    print("\n--- References ---")
    for ref in REQUIRED_REFS:
        check_ref(SKILL_DIR / ref)

    print("\n--- SKILL.md ---")
    check_skill_md(SKILL_DIR / "SKILL.md")

    print("\n--- Results ---")
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  ! {w}")
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  ✗ {e}")
        print("\nVALIDATION FAILED")
        sys.exit(1)
    else:
        print("VALIDATION PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
