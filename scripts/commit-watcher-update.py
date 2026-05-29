#!/usr/bin/env python3
"""
commit-watcher-update.py - Update commit watcher state and queue
Usage:
  python3 commit-watcher-update.py check <state_file> <queue_file> <repo_base> <discord_channel>
    - Checks all repos, updates state, populates queue
  python3 commit-watcher-update.py init <state_file> <repo_base>
    - Initialize state file with current commits
"""

import json
import sys
import os
import subprocess
from datetime import datetime, timezone

REPOS = [
    "chroma-studio-frontend-nextjs",
    "max-v2",
    "remix-studio-nextjs",
    "deepswapper-ai-nextjs",
    "faceswapper-ai",
    "ampere-sh"
]

# Branch-Aware URL Config — production + dev staging URLs
BRANCH_URLS = {
    "chroma-studio-frontend-nextjs": {
        "main": "https://app.chromastudio.ai",
        "dev": "https://style-transfer-git-dev-nextbasecores-projects.vercel.app"
    },
    "max-v2": {
        "master": "https://app.maxstudio.ai",
        "dev": "https://max-v2-git-dev-nextbasecores-projects.vercel.app"
    },
    "remix-studio-nextjs": {
        "main": "https://app.remixai.ai",
        "dev": "https://remixai-git-dev-nextbasecores-projects.vercel.app"
    },
    "deepswapper-ai-nextjs": {
        "main": "https://app.deepswapper.ai",
        "dev": None  # Add staging URL when available
    },
    "faceswapper-ai": {
        "maestro-test": "https://app.faceswapper.ai",
        "dev": "https://faceswapper-ai-git-dev-nextbasecores-projects.vercel.app"
    },
    "ampere-sh": {
        "main": "https://app.ampere.ai",
        "dev": "https://ampere-sh-5px3-git-dev-paradoxs-projects-657e7e56.vercel.app"
    }
}


def get_test_url(repo, branch):
    """Get the test URL for a repo+branch. Falls back to production if dev URL not set."""
    repo_urls = BRANCH_URLS.get(repo, {})
    if branch in repo_urls and repo_urls[branch]:
        return repo_urls[branch]
    for prod_branch in ["main", "master"]:
        if prod_branch in repo_urls and repo_urls[prod_branch]:
            return repo_urls[prod_branch]
    return None


def run_git(repo_path, *args):
    result = subprocess.run(
        ["git", "-C", repo_path] + list(args),
        capture_output=True, text=True
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def get_latest_commit(repo_path):
    """Get LOCAL HEAD commit (used for init only)"""
    out, _, rc = run_git(repo_path, "log", "-1", "--format=%H")
    return out if rc == 0 else ""

def get_remote_latest_commit(repo_path, branch):
    """Get REMOTE HEAD commit from origin/<branch> (used for checking)"""
    out, _, rc = run_git(repo_path, "log", "-1", "--format=%H", f"origin/{branch}")
    return out if rc == 0 else ""

def get_commit_msg(repo_path):
    out, _, rc = run_git(repo_path, "log", "-1", "--format=%s")
    return out if rc == 0 else ""

def get_remote_commit_msg(repo_path, branch):
    out, _, rc = run_git(repo_path, "log", "-1", "--format=%s", f"origin/{branch}")
    return out if rc == 0 else ""

def get_short_hash(repo_path):
    out, _, rc = run_git(repo_path, "log", "-1", "--format=%h")
    return out if rc == 0 else ""

def get_remote_short_hash(repo_path, branch):
    out, _, rc = run_git(repo_path, "log", "-1", "--format=%h", f"origin/{branch}")
    return out if rc == 0 else ""

def get_commit_meta(repo_path):
    out, _, rc = run_git(repo_path, "log", "-1", "--format=%an | %ci")
    return out if rc == 0 else ""

def get_remote_commit_meta(repo_path, branch):
    out, _, rc = run_git(repo_path, "log", "-1", "--format=%an | %ci", f"origin/{branch}")
    return out if rc == 0 else ""

def get_current_branch(repo_path):
    out, _, rc = run_git(repo_path, "branch", "--show-current")
    return out if rc == 0 else "unknown"

def get_diff_stats(repo_path, last_commit, branch):
    if not last_commit:
        return "(initial check)"
    out, _, rc = run_git(repo_path, "diff", "--stat", f"{last_commit}..origin/{branch}")
    return out if rc == 0 else "(unable to diff)"

def get_full_diff(repo_path, last_commit, branch, max_bytes=51200):
    if not last_commit:
        return "(initial check)"
    out, _, rc = run_git(repo_path, "diff", f"{last_commit}..origin/{branch}")
    if rc != 0:
        return "(unable to diff)"
    return out[:max_bytes]

def load_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def init_state(state_file, repo_base):
    state = {"repos": {}, "queue": []}
    for repo in REPOS:
        repo_path = os.path.join(repo_base, repo)
        if os.path.isdir(os.path.join(repo_path, ".git")):
            commit = get_latest_commit(repo_path)
            branch = get_current_branch(repo_path)
            state["repos"][repo] = {
                "path": repo_path,
                "lastCommit": commit,
                "branch": branch,
                "lastChecked": datetime.now(timezone.utc).isoformat()
            }
    save_json(state_file, state)
    print(f"State initialized: {state_file}")

def check_repos(state_file, queue_file, repo_base, discord_channel):
    state = load_json(state_file)
    if state is None:
        print(f"State file not found: {state_file}")
        sys.exit(1)
    
    queue = load_json(queue_file)
    if queue is None:
        queue = []
    
    new_count = 0
    
    for repo in REPOS:
        repo_path = os.path.join(repo_base, repo)
        if not os.path.isdir(os.path.join(repo_path, ".git")):
            print(f"SKIP: {repo} not a git repo")
            continue
        
        # Get current branch for this repo
        branch = get_current_branch(repo_path)
        
        # Fetch origin/<branch> to get remote HEAD (fetch already done in shell script)
        remote_latest = get_remote_latest_commit(repo_path, branch)
        last = state["repos"].get(repo, {}).get("lastCommit", "")
        last_branch = state["repos"].get(repo, {}).get("branch", "")
        
        # If branch changed, update state but DON'T queue (manual branch switch, not a new commit)
        if branch != last_branch and last_branch != "":
            print(f"BRANCH SWITCH: {repo}")
            print(f"  Old branch: {last_branch}")
            print(f"  New branch: {branch}")
            print(f"  Remote commit: {remote_latest[:16] if remote_latest else '(none)'}...")
            print(f"  -> State updated, no queue entry (manual branch switch)")
            
            state["repos"][repo] = {
                "path": repo_path,
                "lastCommit": remote_latest if remote_latest else get_latest_commit(repo_path),
                "branch": branch,
                "lastChecked": datetime.now(timezone.utc).isoformat()
            }
            continue
        
        # Check REMOTE HEAD against stored commit (not local HEAD)
        if remote_latest != last:
            print(f"CHANGE DETECTED: {repo}")
            print(f"  Old: {last[:16] if last else '(none)'}...")
            print(f"  New: {remote_latest[:16]}...")
            
            entry = {
                "id": f"{repo}-{int(datetime.now(timezone.utc).timestamp())}",
                "repo": repo,
                "branch": branch,
                "repoPath": repo_path,
                "maestroPath": os.path.join(repo_base, "maestro-studio"),
                "oldCommit": last,
                "newCommit": remote_latest,
                "shortHash": get_remote_short_hash(repo_path, branch),
                "commitMessage": get_remote_commit_msg(repo_path, branch),
                "commitMeta": get_remote_commit_meta(repo_path, branch),
                "diffStats": get_diff_stats(repo_path, last, branch),
                "fullDiff": get_full_diff(repo_path, last, branch),
                "testUrl": get_test_url(repo, branch),
                "detectedAt": datetime.now(timezone.utc).isoformat(),
                "status": "pending",
                "discordChannel": discord_channel
            }
            
            queue.append(entry)
            new_count += 1
            
            state["repos"][repo] = {
                "path": repo_path,
                "lastCommit": remote_latest,
                "branch": branch,
                "lastChecked": datetime.now(timezone.utc).isoformat()
            }
        else:
            print(f"NO CHANGE: {repo} ({remote_latest[:16] if remote_latest else '(none)'}) on {branch}")
            if repo in state["repos"]:
                state["repos"][repo]["lastChecked"] = datetime.now(timezone.utc).isoformat()
                state["repos"][repo]["branch"] = branch
    
    save_json(state_file, state)
    save_json(queue_file, queue)
    
    if new_count > 0:
        print(f"\n=== QUEUE UPDATED ===")
        print(f"Added {new_count} task(s) to queue")
        
        # Write trigger file
        trigger_file = os.path.join(os.path.dirname(state_file), "commit-watcher-trigger")
        with open(trigger_file, 'w') as f:
            f.write(datetime.now(timezone.utc).isoformat())
    else:
        print(f"\n=== NO NEW COMMITS ===")
    
    print(f"\nDone at {datetime.now(timezone.utc).isoformat()}")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "init":
        if len(sys.argv) < 4:
            print("Usage: commit-watcher-update.py init <state_file> <repo_base>")
            sys.exit(1)
        init_state(sys.argv[2], sys.argv[3])
    
    elif cmd == "check":
        if len(sys.argv) < 6:
            print("Usage: commit-watcher-update.py check <state_file> <queue_file> <repo_base> <discord_channel>")
            sys.exit(1)
        check_repos(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)

if __name__ == '__main__':
    main()
