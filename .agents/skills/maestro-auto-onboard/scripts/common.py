#!/usr/bin/env python3
"""common.py — Shared utilities for maestro-auto-onboard scripts."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd, cwd=None, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", 1


def read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def read_text(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception:
        return ""


def grep_code(root, pattern, max_files=50, exts=(".js", ".ts", ".tsx", ".jsx", ".json", ".env", ".yaml", ".yml")):
    results = []
    count = 0
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if count >= max_files:
                break
            if not fname.endswith(exts):
                continue
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, "r", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            results.append({"file": os.path.relpath(fpath, root), "line": i, "text": line.strip()})
                            count += 1
                            break
            except Exception:
                pass
    return results


def find_files(root, pattern, max_depth=6):
    matches = []
    for dirpath, _, filenames in os.walk(root):
        if dirpath.count(os.sep) - root.count(os.sep) > max_depth:
            continue
        for fname in filenames:
            if re.search(pattern, fname):
                matches.append(os.path.join(dirpath, fname))
    return matches
