#!/usr/bin/env python3
"""
auto-process-simple-changes.py
Automatically processes SIMPLE commit changes without needing sub-agents.
Run from cron after commit-watcher detects changes.

Simple changes include:
- Header button label changes (Get Started ↔ Create)
- Known selector text changes
- Simple additions/removals that have clear Maestro mappings

For complex changes, it leaves them in the queue for agent processing.
"""

import json
import subprocess
import sys
import os
import re

# Allow importing discord-summary.py helpers
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
try:
    from discord_summary import send_entry_dual, build_test_failure_message
except ImportError:
    # Fallback: if discord-summary.py isn't importable as a module name,
    # try loading it directly by path
    import importlib.util
    spec = importlib.util.spec_from_file_location("discord_summary", os.path.join(SCRIPT_DIR, "discord-summary.py"))
    discord_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(discord_mod)
    send_entry_dual = discord_mod.send_entry_dual
    build_test_failure_message = discord_mod.build_test_failure_message

QUEUE_FILE = "/root/.openclaw/workspace/state/commit-queue.json"
STATE_FILE = "/root/.openclaw/workspace/state/commit-watcher.json"
DISCORD_ENV = "/root/.openclaw/workspace/state/maestro-discord.env"
REPO_BASE = "/root/.openclaw/workspace/repos"
MAESTRO_REPO = "/root/.openclaw/workspace/repos/maestro-studio"

def log(msg):
    print(msg)


def load_queue():
    try:
        with open(QUEUE_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_queue(queue):
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def run_git(args, cwd=None):
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd or REPO_BASE,
        capture_output=True,
        text=True
    )
    return result


def get_maestro_folder(repo, branch):
    """Map repo/branch to Maestro folder"""
    mappings = {
        ("chroma-studio-frontend-nextjs", "main"): "chromastudio/",
        ("max-v2", "master"): "maxstudio/",
        ("remix-studio-nextjs", "main"): "remix-ai/",
        ("deepswapper-ai-nextjs", "main"): "deepswapper/",
        ("faceswapper-ai", "maestro-test"): "faceswapper/",
        ("ampere-sh", "main"): "ampere/",
    }
    return mappings.get((repo, branch), f"{repo.split('-')[0]}/")


def is_simple_header_label_change(diff_text):
    """Check if diff is just a header button label change"""
    lines = diff_text.split('\n')
    
    # Must only modify Header/index.tsx or similar
    file_pattern = re.compile(r'^\+\+\+ b/src/components/Header/')
    
    header_files = [l for l in lines if file_pattern.match(l)]
    if not header_files:
        return False
    
    # Check for label patterns
    label_changes = []
    for line in lines:
        if line.startswith('+') and not line.startswith('+++'):
            if 'getStarted:' in line or 'aria-label=' in line:
                # Extract the label value
                match = re.search(r'["\']([^"\']+)["\']', line)
                if match:
                    label_changes.append(match.group(1))
    
    # If we have exactly 2 label changes and they're different, it's a simple swap
    if len(label_changes) >= 2:
        return True
    
    return False


def find_and_replace_in_maestro(maestro_folder, old_text, new_text):
    """Find and replace text in all YAML files in Maestro folder"""
    folder_path = os.path.join(MAESTRO_REPO, maestro_folder)
    
    if not os.path.exists(folder_path):
        log(f"  Maestro folder not found: {folder_path}")
        return 0
    
    changed_count = 0
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.yaml') or file.endswith('.yml'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    content = f.read()
                
                if old_text in content:
                    new_content = content.replace(old_text, new_text)
                    with open(filepath, 'w') as f:
                        f.write(new_content)
                    changed_count += 1
                    log(f"  Updated: {filepath.replace(MAESTRO_REPO + '/', '')}")
    
    return changed_count


def commit_and_push_maestro(repo, branch, short_hash, commit_msg):
    """Commit and push Maestro changes"""
    # Stage changes
    result = run_git(["status", "--short"], cwd=MAESTRO_REPO)
    if not result.stdout.strip():
        log("  No changes to commit")
        return False
    
    # Only stage modified files in the target folder
    lines = result.stdout.strip().split('\n')
    maestro_folder = get_maestro_folder(repo, branch)
    
    for line in lines:
        if line.startswith(' M ') and maestro_folder.replace('/', '') in line:
            filepath = line[3:]
            run_git(["add", filepath], cwd=MAESTRO_REPO)
    
    # Commit
    commit_message = f"test: update Maestro for {repo}/{branch} {short_hash} - {commit_msg}"
    result = run_git(["commit", "-m", commit_message], cwd=MAESTRO_REPO)
    if result.returncode != 0:
        log(f"  Commit failed: {result.stderr}")
        return False
    
    # Push
    result = run_git(["push", "origin", "main"], cwd=MAESTRO_REPO)
    if result.returncode != 0:
        log(f"  Push failed: {result.stderr}")
        return False
    
    log(f"  Pushed: {commit_message}")
    return True


def send_discord_summary(entry, result_text=""):
    """Send Discord summary via dual-format (technical + summary) to both webhooks."""
    try:
        success = send_entry_dual(entry, result_text)
        return success
    except Exception as e:
        log(f"  Discord send error: {e}")
        return False


def send_test_failure_dual(project, test_type, error_type, description, action_taken="", status="failed"):
    """Send test failure report in dual format to both webhooks."""
    try:
        message_full = build_test_failure_message(project, test_type, error_type, description, action_taken, status, technical=True)
        message_summary = build_test_failure_message(project, test_type, error_type, description, action_taken, status, technical=False)
        from discord_summary import send_to_both
        return send_to_both(message_full, message_summary, username="QA Tester")
    except Exception as e:
        log(f"  Discord test failure send error: {e}")
        return False


def process_entry(entry):
    """Try to process a queue entry automatically"""
    repo = entry['repo']
    branch = entry['branch']
    old_commit = entry['oldCommit']
    new_commit = entry['newCommit']
    short_hash = entry['shortHash']
    commit_msg = entry['commitMessage']
    entry_id = entry['id']
    
    log(f"\nProcessing: {repo} {short_hash} - {commit_msg}")
    
    # Mark as in_progress
    entry['status'] = 'in_progress'
    save_queue(load_queue())
    
    # Get the diff
    repo_path = os.path.join(REPO_BASE, repo)
    result = subprocess.run(
        ["git", "diff", f"{old_commit}..{new_commit}"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    diff_text = result.stdout
    
    # Check if it's a simple header label change
    if is_simple_header_change(diff_text):
        log("  Detected: Simple header label change")
        
        # Extract old and new labels
        labels = []
        for line in diff_text.split('\n'):
            if line.startswith('-') and not line.startswith('---'):
                match = re.search(r'["\']([^"\']+)["\']', line)
                if match and match.group(1) not in ['Login', 'Pricing', 'Search tools']:
                    labels.append(('old', match.group(1)))
            if line.startswith('+') and not line.startswith('+++'):
                match = re.search(r'["\']([^"\']+)["\']', line)
                if match and match.group(1) not in ['Login', 'Pricing', 'Search tools']:
                    labels.append(('new', match.group(1)))
        
        if len(labels) >= 2:
            old_label = labels[0][1]
            new_label = labels[1][1]
            
            log(f"  Replacing '{old_label}' → '{new_label}' in Maestro flows")
            
            maestro_folder = get_maestro_folder(repo, branch)
            changed_count = find_and_replace_in_maestro(maestro_folder, old_label, new_label)
            log(f"  Updated {changed_count} files")
            
            if changed_count > 0:
                # Commit and push
                pushed = commit_and_push_maestro(repo, branch, short_hash, commit_msg)
                
                # Send Discord summary (dual format)
                result_text = f"✅ Auto-processed: {repo}/{branch} {short_hash}. Replaced '{old_label}' → '{new_label}' in {changed_count} Maestro files. Push: {'SUCCESS' if pushed else 'FAILED'}."
                send_discord_summary(entry, result_text)
                
                # Mark done
                entry['status'] = 'done'
                entry['processedAt'] = subprocess.run(
                    ["date", "-u", "+%Y-%m-%dT%H:%M:%S%z"],
                    capture_output=True, text=True
                ).stdout.strip()
                save_queue(load_queue())
                
                log(f"  ✅ Done: {entry_id}")
                return True
    
    log(f"  ⚠️ Complex change - leaving for agent processing")
    # Reset to pending for agent to handle
    entry['status'] = 'pending'
    save_queue(load_queue())
    return False


def is_simple_header_change(diff_text):
    """Check if diff is a simple header-related change"""
    # Only one file changed
    file_changes = re.findall(r'^\+\+\+ b/(.+)', diff_text, re.MULTILINE)
    if len(file_changes) != 1:
        return False
    
    # File must be Header related
    if 'Header' not in file_changes[0]:
        return False
    
    # Only label/text changes, no structural changes
    added_lines = [l for l in diff_text.split('\n') if l.startswith('+') and not l.startswith('+++')]
    removed_lines = [l for l in diff_text.split('\n') if l.startswith('-') and not l.startswith('---')]
    
    # Should only be text content changes (getStarted, aria-label)
    for line in added_lines + removed_lines:
        if not any(k in line for k in ['getStarted', 'aria-label', 'login', 'pricing', 'searchPlaceholder']):
            return False
    
    return True


def main():
    queue = load_queue()
    
    # Find pending entries
    pending = [e for e in queue if e.get('status') == 'pending']
    
    if not pending:
        log("No pending queue entries")
        return 0
    
    log(f"Found {len(pending)} pending queue entries")
    
    processed = 0
    for entry in pending:
        if process_entry(entry):
            processed += 1
    
    log(f"\nAuto-processed {processed}/{len(pending)} entries")
    
    # Return count of remaining complex entries that need agent processing
    remaining = len([e for e in load_queue() if e.get('status') == 'pending'])
    if remaining > 0:
        log(f"{remaining} entries need agent processing")
        return 1  # Signal that agent processing is needed
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
