#!/usr/bin/env python3
"""
queue-auto-process.py - Dynamic queue processor for commit watcher
Called by heartbeat to automatically process pending queue entries.
Usage:
  python3 queue-auto-process.py check
    - Checks queue, returns first pending entry as JSON (or None)
  python3 queue-auto-process.py mark-done <entry_id>
    - Marks entry as done
  python3 queue-auto-process.py mark-failed <entry_id> <reason>
    - Marks entry as failed with reason
"""

import json
import sys
import os

QUEUE_FILE = "/root/.openclaw/workspace/state/commit-queue.json"

def load_queue():
    try:
        with open(QUEUE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_queue(queue):
    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=2)

def get_first_pending():
    queue = load_queue()
    for entry in queue:
        if entry.get("status") == "pending":
            return entry
    return None

def update_status(entry_id, status, reason=""):
    queue = load_queue()
    for entry in queue:
        if entry.get("id") == entry_id:
            entry["status"] = status
            entry["processedAt"] = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
            if reason:
                entry["failureReason"] = reason
            save_queue(queue)
            print(f"Updated {entry_id} -> {status}")
            return True
    print(f"Entry not found: {entry_id}")
    return False

def build_task_for_subagent(entry):
    """Build the task string for the sub-agent from a queue entry."""
    repo = entry["repo"]
    branch = entry.get("branch", "main")
    repo_path = entry["repoPath"]
    maestro_path = entry["maestroPath"]
    old_commit = entry["oldCommit"]
    new_commit = entry["newCommit"]
    short_hash = entry["shortHash"]
    commit_msg = entry["commitMessage"]
    diff_stats = entry.get("diffStats", "")
    full_diff = entry.get("fullDiff", "")
    discord_channel = entry.get("discordChannel", "1498991059227774986")
    
    # Determine maestro folder from repo (dev branches use same folder as production)
    repo_to_folder = {
        "chroma-studio-frontend-nextjs": "chromastudio",
        "max-v2": "maxstudio",
        "remix-studio-nextjs": "remix-ai",
        "deepswapper-ai-nextjs": "deepswapper",
        "faceswapper-ai": "faceswapper",
        "ampere-sh": "ampere",
    }
    # Branch-specific overrides (if any)
    branch_overrides = {
        ("chroma-studio-frontend-nextjs", "git-diff-maestro-test"): "chromastudio-git",
    }
    maestro_folder = branch_overrides.get((repo, branch), repo_to_folder.get(repo, repo.split("-")[0]))
    
    task = f"""# Commit Change Handler Task

## Queue Entry
- **Repo:** {repo}
- **Branch:** {branch}
- **Test URL:** {entry.get('testUrl', '(production default)')}
- **Old Commit:** {old_commit}
- **New Commit:** {new_commit}
- **Short Hash:** {short_hash}
- **Message:** {commit_msg}
- **Maestro Folder:** {maestro_folder}
- **Discord Channel:** {discord_channel}

## Your Mission

## ⚠️ SAFETY RULES — You CANNOT:
1. ❌ Delete or modify files in credentials/ directory
2. ❌ Modify frontend repos (nextbasecore/*) — READ ONLY
3. ❌ Delete .sh, .py, .json, .yaml script files
4. ❌ Push to frontend main/master branches
5. ❌ Expose secrets in Discord or commits
6. ❌ Run rm -rf on any directory
7. ❌ Modify openclaw.json or system configs

## ✅ You CAN:
1. ✅ Read git diffs from frontend repos
2. ✅ Update Maestro YAML flows in maestro-studio/
3. ✅ Run temp tests with --env baseUrl
4. ✅ Commit to maestro-studio main branch
5. ✅ Create temporary test files (delete after)

### Step 0: ALWAYS pull latest first (CRITICAL)
```bash
cd {repo_path}
# Fetch and pull the latest changes for the detected branch
git fetch origin {branch}
git pull origin {branch}
# Verify we are at the new commit
git log -1 --format="%H %s"
```
This ensures you are analyzing the ACTUAL latest code, not stale local copy.

1. Read the git diff between old and new commit:
   ```bash
   cd {repo_path}
   git log -1 --format="%H %s %an %ci" {new_commit}
   git diff {old_commit}..{new_commit} --stat
   git diff {old_commit}..{new_commit} | head -200
   ```

2. Determine the correct base URL:
   - **Branch `{branch}` test URL:** `{entry.get('testUrl', 'production default')}`
   - For dev branches, use this staging URL in Maestro flows and temp tests
   - For main/master branches, use the production URL

3. If a test URL is provided, **do NOT modify config.yaml**. Use one of these approaches:
   - Pass `--env baseUrl={entry.get('testUrl', 'production')}` when running `maestro test`
   - Use inline `openLink: "{entry.get('testUrl', 'production')}?__maestroInternalMode=1"` in the temp test YAML
   - NEVER use `sed` to permanently change config.yaml — staging URLs must not leak into committed config

   Example temp test with inline URL:
   ```yaml
   appId: web
   ---
   - openLink: "{entry.get('testUrl', 'production')}?__maestroInternalMode=1"
   ```

   Example running with env override:
   ```bash
   maestro test temp-test.yaml --env baseUrl={entry.get('testUrl', 'production')}
   ```

4. Analyze what changed and plan Maestro updates for `{maestro_folder}/` in `{maestro_path}`

5. Apply Maestro flow changes (selectors, URLs, new screens, removed features)

6. Create a temp test: `{maestro_path}/{maestro_folder}/tests/temp-test-{repo}-{short_hash}.yaml`
   - Use `openLink: "{entry.get('testUrl', 'production URL')}?__maestroInternalMode=1"` for dev branches
   - Test the changed functionality specifically

7. Run the temp test (if Maestro CLI available), capture results

   **If temp test PASSES and this is a DEV branch with staging URL:**
   a. Create a PR from dev to main/master using `gh pr create`:
      ```bash
      cd {repo_path}
      # Determine base branch: main for most repos, master for max-v2
      BASE_BRANCH=$(if [ "{repo}" = "max-v2" ]; then echo "master"; else echo "main"; fi)
      gh pr create --repo nextbasecore/{repo} --base $BASE_BRANCH --head {branch} \
        --title "Auto PR: {commit_msg} ({short_hash})" \
        --body "Staging Maestro tests passed. Ready for review.\n\n- Test URL: {entry.get('testUrl', 'N/A')}\n- Commit: {short_hash}\n\n_Generated by QA Tester_"
      ```
   b. If `gh pr create` says a PR already exists, that's fine — note it in the summary.
   c. NEVER push directly to main/master — only use `gh pr create`.

   **If temp test FAILS:**
   a. Try to fix Maestro flows (update selectors, URLs, etc.) based on what changed.
   b. Re-run the temp test after fixes.
   c. If still failing after reasonable fixes → mark queue entry failed and send failure Discord.

8. Push Maestro changes to GitHub (if any flows were updated):
   ```bash
   cd {maestro_path}
   # ⚠️ NEVER stage config.yaml if it contains a staging URL.
   # If you accidentally changed config.yaml, revert it first:
   #   git checkout -- <maestro_folder>/config/config.yaml
   git add <changed files only>
   git commit -m "test: update Maestro for {repo}/{branch} {short_hash} - {commit_msg}"
   git push origin main
   ```

9. Delete the temp test file

10. Send Discord summary to channel {discord_channel} with:
    - Repo, branch, commit, files changed
    - **Test URL used:** {entry.get('testUrl', 'production')}
    - Maestro updates made
    - Temp test result (pass/fail/skipped)
    - Git push result
    - **PR status:** (created / already exists / skipped / failed)
    - **Webhook 1** = technical details (full output, errors, diffs)
    - **Webhook 2** = clean summary + @Dixit Savaliya mention at the end:
      ```
      **Assignee:** @Dixit Savaliya
      ```
    - Use `python3 /root/.openclaw/workspace/scripts/discord-summary.py send {entry["id"]} "<result text>"` to send both webhooks correctly

11. Mark queue entry as done (or failed if test permanently failed):
    ```bash
    python3 /root/.openclaw/workspace/scripts/queue-auto-process.py mark-done {entry["id"]}
    # OR if failed:
    python3 /root/.openclaw/workspace/scripts/queue-auto-process.py mark-failed {entry["id"]} "<reason>"
    ```

## Alternative Automated Path
If you prefer, you can delegate the staging test + PR workflow to the dedicated script:
```bash
python3 /root/.openclaw/workspace/scripts/commit-to-staging-pr.py run {entry["id"]}
```
This script will: analyze diff → create temp test → run on staging → create PR if pass → send Discord → mark done. You can still do manual Maestro flow fixes before or after calling it.

## Diff Stats
```
{diff_stats[:500]}
```

## Full Diff (truncated)
```
{full_diff[:2000]}
```
"""
    return task

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "check":
        entry = get_first_pending()
        if entry:
            task = build_task_for_subagent(entry)
            # Output as JSON for the heartbeat handler
            output = {
                "has_pending": True,
                "entry_id": entry["id"],
                "repo": entry["repo"],
                "branch": entry.get("branch", "main"),
                "testUrl": entry.get("testUrl"),
                "task": task,
                "discord_channel": entry.get("discordChannel", "1498991059227774986")
            }
            # Also mark as in_progress immediately
            update_status(entry["id"], "in_progress")
            print(json.dumps(output, indent=2))
        else:
            print(json.dumps({"has_pending": False}, indent=2))
    
    elif cmd == "mark-done":
        if len(sys.argv) < 3:
            print("Usage: queue-auto-process.py mark-done <entry_id>")
            sys.exit(1)
        update_status(sys.argv[2], "done")
    
    elif cmd == "mark-failed":
        if len(sys.argv) < 4:
            print("Usage: queue-auto-process.py mark-failed <entry_id> <reason>")
            sys.exit(1)
        update_status(sys.argv[2], "failed", sys.argv[3])
    
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)

if __name__ == '__main__':
    main()
