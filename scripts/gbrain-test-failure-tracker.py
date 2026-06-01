#!/usr/bin/env python3
"""
gbrain-test-failure-tracker.py — Store test failures to GBrain for institutional memory

Usage:
  python3 gbrain-test-failure-tracker.py store <product> <test_type> <error_type> <description> [--action="fix applied"] [--result="pass/fail"]
    - Store a test failure to GBrain
  
  python3 gbrain-test-failure-tracker.py query <search_term>
    - Query GBrain for similar past failures

  python3 gbrain-test-failure-tracker.py summary <product>
    - Get summary of failures for a product

Examples:
  python3 gbrain-test-failure-tracker.py store deepswapper "schema-check" "chrome-cdp" "Chrome instance exited unexpectedly" --action="Killed zombie processes" --result="pass"
  
  python3 gbrain-test-failure-tracker.py query "Chrome crash DeepSwapper"
  
  python3 gbrain-test-failure-tracker.py summary chromastudio
"""

import sys
import os
import subprocess
import json
from datetime import datetime, timezone
from pathlib import Path

# GBrain environment setup
GBRAIN_ENV = {
    "PATH": f"{os.environ.get('HOME', '/root')}/.bun/bin:{os.environ.get('PATH', '')}",
    "ZEROENTROPY_API_KEY": os.environ.get("ZEROENTROPY_API_KEY", ""),
    "VOYAGE_API_KEY": os.environ.get("VOYAGE_API_KEY", ""),
}

BRAIN_DIR = os.path.expanduser("~/brain/testing-automation/failures")
GBRAIN_SOURCE = "testing-automation"


def ensure_brain_dir():
    """Ensure the brain directory exists."""
    Path(BRAIN_DIR).mkdir(parents=True, exist_ok=True)


def gbrain_command(cmd, timeout=120):
    """Run a gbrain command with proper environment."""
    env = {**os.environ, **GBRAIN_ENV}
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            shell=True
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def store_failure(product, test_type, error_type, description, action_taken="", result="", tests_total=0, tests_passed=0, tests_failed=0):
    """Store a test failure to GBrain."""
    ensure_brain_dir()
    
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Create filename
    safe_product = product.lower().replace(" ", "-")
    safe_test = test_type.lower().replace(" ", "-")
    safe_error = error_type.lower().replace(" ", "-")[:30]
    filename = f"{safe_product}-{safe_test}-{safe_error}-{date_str}.md"
    filepath = os.path.join(BRAIN_DIR, filename)
    
    # Build content
    lines = [
        f"# Test Failure: {product.title()} {test_type.title()} - {date_str}",
        f"",
        f"## Problem",
        description,
        f"",
        f"## Environment",
        f"- **Product:** {product.title()}",
        f"- **Test Type:** {test_type}",
        f"- **Date:** {timestamp}",
        f"- **Status:** {result.upper() if result else 'FAILED'}",
        f"- **Error Type:** {error_type}",
    ]
    
    if tests_total > 0:
        lines.extend([
            f"",
            f"## Test Results",
            f"- **Total:** {tests_total}",
            f"- **Passed:** {tests_passed}",
            f"- **Failed:** {tests_failed}",
        ])
    
    if action_taken:
        lines.extend([
            f"",
            f"## Fix Applied",
            action_taken,
        ])
    
    lines.extend([
        f"",
        f"## Prevention",
        f"- [ ] Monitor for recurrence",
        f"- [ ] Update runbook if pattern repeats",
        f"",
        f"---",
        f"*Auto-captured by QA Tester on {date_str}*",
    ])
    
    content = "\n".join(lines)
    
    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    # Capture to GBrain
    cmd = f"gbrain capture --file '{filepath}' --source {GBRAIN_SOURCE}"
    returncode, stdout, stderr = gbrain_command(cmd)
    
    if returncode == 0:
        print(f"✅ Stored failure to GBrain: {filename}")
        print(f"   {stdout.strip()}")
        return True
    else:
        print(f"❌ Failed to store to GBrain: {stderr}")
        # Keep local file even if gbrain capture fails
        print(f"   Local file saved: {filepath}")
        return False


def query_failures(search_term):
    """Query GBrain for similar past failures."""
    cmd = f"gbrain search '{search_term}' --source {GBRAIN_SOURCE}"
    returncode, stdout, stderr = gbrain_command(cmd)
    
    if returncode == 0:
        print(f"=== GBrain Search Results for '{search_term}' ===")
        print(stdout)
        return True
    else:
        print(f"❌ Search failed: {stderr}")
        return False


def summarize_failures(product):
    """Get summary of failures for a product."""
    cmd = f"gbrain search '{product}' --source {GBRAIN_SOURCE}"
    returncode, stdout, stderr = gbrain_command(cmd)
    
    if returncode == 0:
        print(f"=== Failures for {product.title()} ===")
        print(stdout)
        return True
    else:
        print(f"❌ Summary failed: {stderr}")
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "store":
        if len(sys.argv) < 5:
            print("Usage: store <product> <test_type> <error_type> <description> [--action=...] [--result=...]")
            sys.exit(1)
        
        product = sys.argv[2]
        test_type = sys.argv[3]
        error_type = sys.argv[4]
        description = sys.argv[5] if len(sys.argv) > 5 else "No description provided"
        
        action_taken = ""
        result = ""
        
        # Parse optional args
        for arg in sys.argv[6:]:
            if arg.startswith("--action="):
                action_taken = arg.split("=", 1)[1]
            elif arg.startswith("--result="):
                result = arg.split("=", 1)[1]
        
        success = store_failure(product, test_type, error_type, description, action_taken, result)
        sys.exit(0 if success else 1)
    
    elif cmd == "query":
        if len(sys.argv) < 3:
            print("Usage: query <search_term>")
            sys.exit(1)
        
        search_term = sys.argv[2]
        success = query_failures(search_term)
        sys.exit(0 if success else 1)
    
    elif cmd == "summary":
        if len(sys.argv) < 3:
            print("Usage: summary <product>")
            sys.exit(1)
        
        product = sys.argv[2]
        success = summarize_failures(product)
        sys.exit(0 if success else 1)
    
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
