#!/usr/bin/env python3
"""
commit-to-staging-pr.py - Full staging test + PR creation workflow for commit queue entries.

Usage:
  python3 commit-to-staging-pr.py run <entry_id>
    - Full workflow: analyze diff → create temp test → run on staging → PR if pass
  python3 commit-to-staging-pr.py pr-only <entry_id>
    - Skip tests, just create PR (for already-verified entries)
  python3 commit-to-staging-pr.py test-only <entry_id>
    - Run temp test only, no PR creation

Safety rules:
  - NEVER modifies frontend repo files (read-only for diff)
  - NEVER pushes to frontend main/master directly
  - Uses gh pr create for PR requests
  - Staging URLs never leak into committed config.yaml
  - Only selective git add for maestro-studio
"""

import json
import sys
import os
import subprocess
import re
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

try:
    from discord_summary import send_entry_dual, build_test_failure_message, send_to_both
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "discord_summary", os.path.join(SCRIPT_DIR, "discord-summary.py")
    )
    discord_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(discord_mod)
    send_entry_dual = discord_mod.send_entry_dual
    build_test_failure_message = discord_mod.build_test_failure_message
    send_to_both = discord_mod.send_to_both

QUEUE_FILE = "/root/.openclaw/workspace/state/commit-queue.json"
MAESTRO_REPO = "/root/.openclaw/workspace/repos/maestro-studio"
REPO_BASE = "/root/.openclaw/workspace/repos"

# Branch → production base branch mapping
BRANCH_TO_BASE = {
    "chroma-studio-frontend-nextjs": {"dev": "main", "main": None},
    "max-v2": {"dev": "master", "master": None},
    "remix-studio-nextjs": {"dev": "main", "main": None},
    "deepswapper-ai-nextjs": {"dev": "main", "main": None},
    "faceswapper-ai": {"dev": "maestro-test", "maestro-test": None},
    "ampere-sh": {"dev": "main", "main": None},
}

# Repo to Maestro folder mapping
REPO_TO_FOLDER = {
    "chroma-studio-frontend-nextjs": "chromastudio",
    "max-v2": "maxstudio",
    "remix-studio-nextjs": "remixai",
    "deepswapper-ai-nextjs": "deepswapper",
    "faceswapper-ai": "faceswapper",
    "ampere-sh": "ampere",
}

# GitHub owner mapping
REPO_TO_OWNER = {
    "chroma-studio-frontend-nextjs": "nextbasecore",
    "max-v2": "nextbasecore",
    "remix-studio-nextjs": "nextbasecore",
    "deepswapper-ai-nextjs": "nextbasecore",
    "faceswapper-ai": "nextbasecore",
    "ampere-sh": "nextbasecore",
}


def log(msg):
    print(msg)


def load_queue():
    try:
        with open(QUEUE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_queue(queue):
    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=2)


def find_entry(entry_id):
    queue = load_queue()
    for entry in queue:
        if entry.get('id') == entry_id:
            return entry
    return None


def update_entry_status(entry_id, status, reason=""):
    queue = load_queue()
    for entry in queue:
        if entry.get('id') == entry_id:
            entry['status'] = status
            entry['processedAt'] = datetime.now(timezone.utc).isoformat()
            if reason:
                entry['failureReason'] = reason
            save_queue(queue)
            log(f"  Updated {entry_id} -> {status}")
            return True
    log(f"  Entry not found: {entry_id}")
    return False


def run_git(args, cwd=None):
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd or REPO_BASE,
        capture_output=True,
        text=True
    )
    return result


def run_shell(cmd, cwd=None, timeout=120):
    result = subprocess.run(
        cmd,
        cwd=cwd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result


def analyze_diff(diff_stats, full_diff):
    """Analyze diff to determine what kind of temp test to create."""
    changed_files = []
    if diff_stats:
        for line in diff_stats.strip().split('\n'):
            if '|' in line and 'changed' not in line:
                filepath = line.split('|')[0].strip()
                if filepath and not filepath.startswith('-'):
                    changed_files.append(filepath)

    # Determine test focus based on changed files
    focus = "general"
    selectors = []
    url_pattern = None

    for f in changed_files:
        f_lower = f.lower()
        if 'header' in f_lower:
            focus = "header"
            selectors.extend(["Get Started", "Create", "Pricing", "Login"])
        elif 'pricing' in f_lower or 'plan' in f_lower:
            focus = "pricing"
            selectors.extend(["Pricing", "Subscribe", "Upgrade"])
        elif 'tool' in f_lower or 'card' in f_lower or 'model' in f_lower:
            focus = "tools"
            selectors.extend(["Create", "Generate", "Try Now"])
        elif 'schema' in f_lower or 'payload' in f_lower or 'api' in f_lower:
            focus = "schema"
            selectors.extend(["Create", "Generate"])
        elif 'route' in f_lower or 'page' in f_lower or 'app/' in f_lower:
            focus = "routing"
            selectors.extend(["Home", "Create", "Tools"])
        elif 'auth' in f_lower or 'login' in f_lower:
            focus = "auth"
            selectors.extend(["Login", "Sign In", "Get Started"])

    # Remove duplicates while preserving order
    seen = set()
    unique_selectors = []
    for s in selectors:
        if s not in seen:
            seen.add(s)
            unique_selectors.append(s)

    return {
        "focus": focus,
        "changed_files": changed_files[:10],
        "selectors": unique_selectors[:5],
    }


def create_temp_test(entry, analysis):
    """Create a focused Maestro temp test YAML for the changed functionality."""
    repo = entry['repo']
    branch = entry.get('branch', 'main')
    short_hash = entry.get('shortHash', 'unknown')
    test_url = entry.get('testUrl', '')
    maestro_folder = REPO_TO_FOLDER.get(repo, repo.split('-')[0])

    if not test_url:
        log(f"  ⚠️ No test URL in entry, skipping temp test creation")
        return None

    # Build test filename
    test_filename = f"temp-test-{repo}-{short_hash}.yaml"
    test_path = os.path.join(MAESTRO_REPO, maestro_folder, "tests", test_filename)

    # Ensure tests directory exists
    os.makedirs(os.path.dirname(test_path), exist_ok=True)

    # Determine what to test based on analysis
    focus = analysis.get("focus", "general")
    selectors = analysis.get("selectors", ["Get Started", "Create"])

    # Build YAML content
    yaml_lines = [
        f"# Auto-generated staging temp test for {repo}/{branch} {short_hash}",
        f"# Focus: {focus}",
        f"# Generated by commit-to-staging-pr.py",
        f"appId: web",
        f"---",
        f"- openLink: \"{test_url}?__maestroInternalMode=1\"",
        f"- waitForAnimationToEnd:",
        f"    timeout: 5000",
    ]

    # Add assertions based on focus
    if focus == "header":
        yaml_lines.extend([
            f"- assertVisible: \".*(Get Started|Create|Home).*\"",
        ])
    elif focus == "pricing":
        yaml_lines.extend([
            f"- tapOn: \"Pricing\"",
            f"- waitForAnimationToEnd:",
            f"    timeout: 3000",
            f"- assertVisible: \".*(Free|Basic|Pro|Plan).*\"",
        ])
    elif focus == "tools":
        yaml_lines.extend([
            f"- assertVisible: \".*(Create|Generate|Tool).*\"",
            f"- tapOn: \"Create\"",
            f"- waitForAnimationToEnd:",
            f"    timeout: 5000",
        ])
    elif focus == "auth":
        yaml_lines.extend([
            f"- tapOn: \"Login\"",
            f"- waitForAnimationToEnd:",
            f"    timeout: 3000",
            f"- assertVisible: \".*(Email|Password|Sign In).*\"",
        ])
    else:
        # General smoke test
        yaml_lines.extend([
            f"- assertVisible: \".*(Get Started|Create|Home|Generate).*\"",
        ])

    yaml_lines.extend([
        f"- takeScreenshot: staging-temp-{short_hash}",
    ])

    yaml_content = '\n'.join(yaml_lines)

    with open(test_path, 'w') as f:
        f.write(yaml_content)

    log(f"  Created temp test: {test_path}")
    return test_path


def run_temp_test(test_path, test_url):
    """Run the Maestro temp test against staging URL."""
    if not test_path or not os.path.exists(test_path):
        log(f"  ⚠️ Temp test file not found: {test_path}")
        return False, "Test file not found"

    # Run with --env baseUrl to avoid touching config.yaml
    cmd = f'maestro test "{test_path}" --env baseUrl="{test_url}"'
    log(f"  Running: {cmd}")

    result = run_shell(cmd, cwd=MAESTRO_REPO, timeout=180)

    if result.returncode == 0:
        log(f"  ✅ Temp test PASSED")
        return True, result.stdout.strip()[-500:] if result.stdout else "Passed"
    else:
        log(f"  ❌ Temp test FAILED")
        err = result.stderr.strip()[-500:] if result.stderr else "Unknown error"
        out = result.stdout.strip()[-500:] if result.stdout else ""
        return False, f"STDERR: {err}\nSTDOUT: {out}"


def delete_temp_test(test_path):
    """Clean up temp test file."""
    if test_path and os.path.exists(test_path):
        os.remove(test_path)
        log(f"  Deleted temp test: {test_path}")


def create_pr(entry):
    """Create a PR from dev branch to main/master using gh CLI."""
    repo = entry['repo']
    branch = entry.get('branch', 'main')
    repo_path = entry.get('repoPath', os.path.join(REPO_BASE, repo))
    commit_msg = entry.get('commitMessage', 'Dev branch update')
    short_hash = entry.get('shortHash', 'unknown')

    # Determine base branch
    base_branch = BRANCH_TO_BASE.get(repo, {}).get(branch)
    if not base_branch:
        log(f"  ⚠️ No base branch mapping for {repo}/{branch}, skipping PR")
        return False, "No base branch mapping"

    # Check if gh is available
    gh_check = run_shell("which gh", timeout=10)
    if gh_check.returncode != 0:
        return False, "gh CLI not available"

    # Build PR title and body
    pr_title = f"Auto PR: {commit_msg} ({short_hash})"
    pr_body = (
        f"This PR was automatically created after Maestro staging tests passed.\n\n"
        f"- **Source branch:** `{branch}`\n"
        f"- **Target branch:** `{base_branch}`\n"
        f"- **Commit:** `{short_hash}`\n"
        f"- **Test URL:** {entry.get('testUrl', 'N/A')}\n\n"
        f"_Generated by QA Tester 🤖_"
    )

    # Run gh pr create
    # Note: we run from the repo directory, the local branch should be 'dev'
    cmd = (
        f'gh pr create '
        f'--repo {REPO_TO_OWNER.get(repo, "nextbasecore")}/{repo} '
        f'--base {base_branch} '
        f'--head {branch} '
        f'--title "{pr_title}" '
        f'--body "{pr_body}"'
    )
    log(f"  Creating PR: {pr_title}")
    log(f"  Command: {cmd}")

    result = run_shell(cmd, cwd=repo_path, timeout=60)

    if result.returncode == 0:
        pr_url = result.stdout.strip()
        log(f"  ✅ PR created: {pr_url}")
        return True, pr_url
    else:
        err = result.stderr.strip()
        # Handle "a pull request already exists" gracefully
        if "already exists" in err.lower() or "already exists" in result.stdout.lower():
            log(f"  ℹ️ PR already exists for this branch")
            return True, "PR already exists"
        log(f"  ❌ PR creation failed: {err}")
        return False, err


def send_discord_summary(entry, result_text, is_failure=False):
    """Send Discord summary with dual webhook format."""
    try:
        if is_failure:
            # Use test failure format for failures
            message_full = build_test_failure_message(
                project=entry.get('repo', 'unknown'),
                test_type="Staging Temp Test",
                error_type="Maestro Flow Error" if "maestro" in result_text.lower() else "General Error",
                description=result_text[:500],
                action_taken="Manual review required. Maestro flows may need selector updates.",
                status="failed",
                technical=True
            )
            message_summary = build_test_failure_message(
                project=entry.get('repo', 'unknown'),
                test_type="Staging Temp Test",
                error_type="Maestro Flow Error" if "maestro" in result_text.lower() else "General Error",
                description=result_text[:200],
                action_taken="Please review the Maestro flows and staging test results.",
                status="failed",
                technical=False
            )
            return send_to_both(message_full, message_summary, username="QA Tester")
        else:
            # Use standard commit summary format
            return send_entry_dual(entry, result_text, username="QA Tester")
    except Exception as e:
        log(f"  Discord send error: {e}")
        return False


def run_full_workflow(entry_id):
    """Execute the full staging test + PR workflow for a queue entry."""
    entry = find_entry(entry_id)
    if not entry:
        log(f"Entry not found: {entry_id}")
        return False

    repo = entry['repo']
    branch = entry.get('branch', 'main')
    test_url = entry.get('testUrl', '')

    log(f"\n{'='*60}")
    log(f"STAGING PR WORKFLOW: {repo}/{branch} {entry.get('shortHash', '???')}")
    log(f"{'='*60}")

    # Step 1: Analyze diff
    log("\n[1/5] Analyzing git diff...")
    diff_stats = entry.get('diffStats', '')
    full_diff = entry.get('fullDiff', '')
    analysis = analyze_diff(diff_stats, full_diff)
    log(f"  Focus: {analysis['focus']}")
    log(f"  Changed files: {len(analysis['changed_files'])}")

    # Step 2: Create temp test
    log("\n[2/5] Creating temp Maestro test...")
    if not test_url:
        log(f"  ⚠️ No staging URL available. Cannot run staging test.")
        # Still try to create PR if it's a main/master branch change? No, skip.
        update_entry_status(entry_id, "failed", "No staging URL")
        send_discord_summary(entry, "No staging URL configured for this branch", is_failure=True)
        return False

    test_path = create_temp_test(entry, analysis)
    if not test_path:
        log(f"  ⚠️ Could not create temp test")
        update_entry_status(entry_id, "failed", "Temp test creation failed")
        send_discord_summary(entry, "Temp test creation failed", is_failure=True)
        return False

    # Step 3: Run temp test
    log("\n[3/5] Running temp test on staging URL...")
    test_passed, test_output = run_temp_test(test_path, test_url)

    if test_passed:
        log("\n[4/5] Temp test PASSED → Creating PR...")
        pr_success, pr_result = create_pr(entry)

        # Step 5: Send Discord + mark done
        if pr_success:
            result_text = (
                f"✅ Staging temp test PASSED\n"
                f"🔄 PR created: {pr_result}\n"
                f"📁 Changed: {', '.join(analysis['changed_files'][:3])}"
            )
            log("\n[5/5] Sending Discord summary...")
            send_discord_summary(entry, result_text)
            update_entry_status(entry_id, "done")
            log(f"\n{'='*60}")
            log(f"WORKFLOW COMPLETE: {repo}/{branch} — PR created")
            log(f"{'='*60}")
        else:
            result_text = (
                f"✅ Staging temp test PASSED\n"
                f"❌ PR creation failed: {pr_result}\n"
                f"📁 Changed: {', '.join(analysis['changed_files'][:3])}"
            )
            log("\n[5/5] Sending Discord summary (PR failed)...")
            send_discord_summary(entry, result_text)
            # Mark as done since test passed, but note PR failure
            update_entry_status(entry_id, "done")
            log(f"\n{'='*60}")
            log(f"WORKFLOW PARTIAL: Test passed but PR failed — {pr_result}")
            log(f"{'='*60}")

    else:
        log("\n[4/5] Temp test FAILED → Skipping PR...")
        # Try to fix Maestro flows? For now, just report failure.
        # In a real scenario, a sub-agent would be spawned to fix selectors.
        result_text = (
            f"❌ Staging temp test FAILED\n"
            f"📁 Changed: {', '.join(analysis['changed_files'][:3])}\n"
            f"🔍 Output: {test_output[:300]}"
        )
        log("\n[5/5] Sending Discord failure summary...")
        send_discord_summary(entry, result_text, is_failure=True)
        update_entry_status(entry_id, "failed", f"Staging test failed: {test_output[:200]}")
        log(f"\n{'='*60}")
        log(f"WORKFLOW FAILED: {repo}/{branch} — Staging test did not pass")
        log(f"{'='*60}")

    # Cleanup
    delete_temp_test(test_path)
    return test_passed


def run_pr_only(entry_id):
    """Skip tests, just create PR."""
    entry = find_entry(entry_id)
    if not entry:
        log(f"Entry not found: {entry_id}")
        return False

    repo = entry['repo']
    branch = entry.get('branch', 'main')
    log(f"\n[PR-ONLY] {repo}/{branch} — Creating PR...")
    pr_success, pr_result = create_pr(entry)

    if pr_success:
        result_text = f"🔄 PR created (test skipped): {pr_result}"
        send_discord_summary(entry, result_text)
        update_entry_status(entry_id, "done")
    else:
        result_text = f"❌ PR creation failed: {pr_result}"
        send_discord_summary(entry, result_text, is_failure=True)
        update_entry_status(entry_id, "failed", pr_result)

    return pr_success


def run_test_only(entry_id):
    """Run temp test only, no PR."""
    entry = find_entry(entry_id)
    if not entry:
        log(f"Entry not found: {entry_id}")
        return False

    diff_stats = entry.get('diffStats', '')
    full_diff = entry.get('fullDiff', '')
    analysis = analyze_diff(diff_stats, full_diff)
    test_url = entry.get('testUrl', '')

    test_path = create_temp_test(entry, analysis)
    if not test_path:
        return False

    test_passed, test_output = run_temp_test(test_path, test_url)
    delete_temp_test(test_path)

    log(f"\nTest result: {'PASSED' if test_passed else 'FAILED'}")
    log(f"Output: {test_output[:500]}")
    return test_passed


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    entry_id = sys.argv[2]

    if cmd == "run":
        success = run_full_workflow(entry_id)
        sys.exit(0 if success else 1)
    elif cmd == "pr-only":
        success = run_pr_only(entry_id)
        sys.exit(0 if success else 1)
    elif cmd == "test-only":
        success = run_test_only(entry_id)
        sys.exit(0 if success else 1)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
