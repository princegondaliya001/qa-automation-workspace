#!/usr/bin/env python3
"""
discord-summary.py - Send Discord summary for commit watcher tasks via webhook
Supports DUAL webhook format:
  - Webhook 1 (1498991087539326987): Full technical details
  - Webhook 2 (1509429662529355958): Clean non-tech summary

Usage:
  python3 discord-summary.py send <queue_entry_id> [result_text]
    - Reads queue entry and SENDS both technical + summary formats to respective webhooks
  python3 discord-summary.py preview <queue_entry_id> [result_text]
    - Preview both message formats without sending
  python3 discord-summary.py daily <date> <desktop_pass> <desktop_fail> <mobile_pass> <mobile_fail> <total_products> <run_dir> [log_dir]
    - Send daily test results to both webhooks (technical to #1, summary to #2)
  python3 discord-summary.py custom <message_text> [--webhook=1|2|both]
    - Send a custom message to specified webhook(s)
"""

import json
import sys
import os
import subprocess
from datetime import datetime, timezone

QUEUE_FILE = "/root/.openclaw/workspace/state/commit-queue.json"
ENV_FILE = "/root/.openclaw/workspace/state/maestro-discord.env"

# Webhook IDs for dual format
WEBHOOK_TECHNICAL = "1498991087539326987"
WEBHOOK_SUMMARY = "1509429662529355958"


def load_env():
    """Load webhook URLs from env file. Returns dict mapping webhook_id -> url."""
    webhooks = {}
    try:
        with open(ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('DISCORD_WEBHOOK_URLS='):
                    urls = line.split('=', 1)[1].strip().strip('"').strip("'")
                    for url in urls.split():
                        if url:
                            wid = url.split('/')[-2] if '/' in url else 'unknown'
                            webhooks[wid] = url
                elif line.startswith('DISCORD_WEBHOOK_URL='):
                    single_url = line.split('=', 1)[1].strip().strip('"').strip("'")
                    if single_url:
                        wid = single_url.split('/')[-2] if '/' in single_url else 'unknown'
                        webhooks[wid] = single_url
    except FileNotFoundError:
        pass
    return webhooks


def send_webhook_to(url, message_text, username="Commit Watcher"):
    """Send message to a SINGLE Discord webhook via curl."""
    if not url:
        print("ERROR: No webhook URL provided")
        return False
    
    payload = {
        "username": username,
        "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png",
        "content": message_text[:2000]  # Discord limit
    }
    
    cmd = [
        "curl", "-s", "-H", "Content-Type: application/json",
        "-d", json.dumps(payload),
        url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        wid = url.split('/')[-2] if '/' in url else 'unknown'
        if result.returncode == 0:
            print(f"  Discord notification sent successfully to {wid}")
            return True
        else:
            print(f"  Discord send failed for {wid}: {result.stderr}")
            return False
    except Exception as e:
        wid = url.split('/')[-2] if '/' in url else 'unknown'
        print(f"  Discord send error for {wid}: {e}")
        return False


def send_to_both(message_full, message_summary, username="Commit Watcher"):
    """Send technical format to Webhook 1 and summary format to Webhook 2."""
    webhooks = load_env()
    
    tech_url = webhooks.get(WEBHOOK_TECHNICAL)
    sum_url = webhooks.get(WEBHOOK_SUMMARY)
    
    if not tech_url and not sum_url:
        print("ERROR: No DISCORD_WEBHOOK_URL or DISCORD_WEBHOOK_URLS found in maestro-discord.env")
        return False
    
    results = []
    
    # Send technical format to Webhook 1
    if tech_url:
        print(f"  → Sending technical format to Webhook 1 ({WEBHOOK_TECHNICAL})")
        results.append(send_webhook_to(tech_url, message_full, username))
    else:
        print(f"  ⚠️ Technical webhook {WEBHOOK_TECHNICAL} not found in env")
        results.append(False)
    
    # Send summary format to Webhook 2
    if sum_url:
        print(f"  → Sending summary format to Webhook 2 ({WEBHOOK_SUMMARY})")
        results.append(send_webhook_to(sum_url, message_summary, username))
    else:
        print(f"  ⚠️ Summary webhook {WEBHOOK_SUMMARY} not found in env")
        results.append(False)
    
    return all(results)


def send_webhook(message_text, username="Commit Watcher"):
    """LEGACY: Send message to ALL Discord webhooks (same format). Kept for compatibility."""
    webhooks = load_env()
    if not webhooks:
        print("ERROR: No DISCORD_WEBHOOK_URL or DISCORD_WEBHOOK_URLS found in maestro-discord.env")
        return False
    
    payload = {
        "username": username,
        "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png",
        "content": message_text[:2000]  # Discord limit
    }
    
    all_sent = True
    for wid, webhook_url in webhooks.items():
        cmd = [
            "curl", "-s", "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            webhook_url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"  Discord notification sent successfully to {wid}")
            else:
                print(f"  Discord send failed for {wid}: {result.stderr}")
                all_sent = False
        except Exception as e:
            print(f"  Discord send error for {wid}: {e}")
            all_sent = False
    
    return all_sent


def send_embed(title, fields, footer="Commit Watcher Bot"):
    """Send rich embed message to ALL Discord webhooks via curl."""
    webhooks = load_env()
    if not webhooks:
        print("ERROR: No DISCORD_WEBHOOK_URL or DISCORD_WEBHOOK_URLS found in maestro-discord.env")
        return False
    
    payload = {
        "username": "Commit Watcher",
        "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png",
        "embeds": [{
            "title": title,
            "color": 3066993,
            "fields": fields,
            "footer": {"text": footer}
        }]
    }
    
    all_sent = True
    for wid, webhook_url in webhooks.items():
        cmd = [
            "curl", "-s", "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            webhook_url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"  Discord embed sent successfully to {wid}")
            else:
                print(f"  Discord embed send failed for {wid}: {result.stderr}")
                all_sent = False
        except Exception as e:
            print(f"  Discord embed send error for {wid}: {e}")
            all_sent = False
    
    return all_sent


def load_queue():
    try:
        with open(QUEUE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def find_entry(entry_id):
    queue = load_queue()
    for entry in queue:
        if entry.get('id') == entry_id:
            return entry
    return None


def count_modified_files(diff_stats):
    """Count number of files modified from diff stats text."""
    if not diff_stats:
        return 0
    # diff --stat usually ends with "X files changed" line
    for line in diff_stats.strip().split('\n'):
        if 'files changed' in line:
            try:
                return int(line.strip().split()[0])
            except (ValueError, IndexError):
                pass
    # Fallback: count lines that look like file changes
    count = 0
    for line in diff_stats.strip().split('\n'):
        if '|' in line and not line.strip().startswith('-') and 'changed' not in line:
            count += 1
    return count


def parse_test_stats(text):
    """Robustly parse pass/fail counts from result text."""
    import re
    total = passed = failed = 0
    if not text:
        return total, passed, failed
    
    # Pattern: "5/7 passed" or "5 passed out of 7"
    m = re.search(r'(\d+)[/\s]+(?:out\s+of\s+)?(\d+)\s*(?:passed|tests?)', text, re.I)
    if m:
        passed = int(m.group(1))
        total = int(m.group(2))
        failed = total - passed
    
    # Pattern: "2 failed" or "failures: 2"
    m2 = re.search(r'(\d+)\s*(?:failed|failure|fail)', text, re.I)
    if m2:
        failed = int(m2.group(1))
    
    # Pattern: "passed: 5, failed: 2"
    m3 = re.search(r'passed[:\s]+(\d+)', text, re.I)
    m4 = re.search(r'failed[:\s]+(\d+)', text, re.I)
    if m3:
        passed = int(m3.group(1))
    if m4:
        failed = int(m4.group(1))
    
    # If we have both passed and failed, calculate total
    if passed > 0 or failed > 0:
        total = max(total, passed + failed)
    
    return total, passed, failed


def build_summary_message(entry, result_text="", technical=True):
    """
    Build Discord message. 
    technical=True  -> Full technical details for Webhook 1 (developers)
    technical=False -> Clean summary for Webhook 2 (managers/non-tech)
    """
    repo = entry.get('repo', 'unknown')
    branch = entry.get('branch', 'main')
    short_hash = entry.get('shortHash', 'unknown')
    commit_msg = entry.get('commitMessage', 'unknown')
    diff_stats = entry.get('diffStats', '')
    status = entry.get('status', 'unknown')
    
    # Map status to emoji
    status_emoji = {
        'done': '✅',
        'completed': '✅',
        'pending': '⏳',
        'in_progress': '⏳',
        'failed': '❌',
        'error': '❌',
    }.get(status.lower(), '⏳')
    
    file_count = count_modified_files(diff_stats)
    
    if technical:
        # === TECHNICAL FORMAT (Webhook 1) — EXACTLY as-is ===
        lines = [
            f"**Commit Change Processed: {repo}**",
            f"",
            f"**Branch:** {branch}",
            f"**Commit:** `{short_hash}` - {commit_msg}",
        ]
        
        if diff_stats:
            lines.append(f"**Files Changed:**")
            for line in diff_stats.strip().split('\n')[:15]:
                if '|' in line and 'changed' not in line:
                    lines.append(f"- {line.strip()}")
        
        if result_text:
            lines.append(f"")
            lines.append(f"**Maestro Update Result:**")
            lines.append(result_text)
        
        # Extract and show test stats in technical format too
        tests_total = entry.get('testsTotal', 0)
        tests_passed = entry.get('testsPassed', 0)
        tests_failed = entry.get('testsFailed', 0)
        if not tests_total and result_text:
            parsed_total, parsed_passed, parsed_failed = parse_test_stats(result_text)
            if parsed_total > 0:
                tests_total = parsed_total
                tests_passed = parsed_passed
                tests_failed = parsed_failed
        if tests_total > 0:
            lines.append(f"")
            lines.append(f"**Test Results:** ✅ {tests_passed} passed | ❌ {tests_failed} failed (total: {tests_total})")
        
        lines.append(f"")
        lines.append(f"**Status:** {status}")
        lines.append(f"---")
        lines.append(f"*Auto-generated by Commit Watcher*")
        
        return '\n'.join(lines)
    
    else:
        # === SUMMARY FORMAT (Webhook 2) — Clean, non-tech ===
        # Determine result for status line
        result_label = status_emoji
        if result_text:
            if 'SUCCESS' in result_text.upper() or '✅' in result_text:
                result_label = '✅ Completed'
            elif 'FAIL' in result_text.upper() or '❌' in result_text or 'error' in result_text.lower():
                result_label = '❌ Failed'
            elif 'pending' in status.lower():
                result_label = '⏳ Pending'
            else:
                result_label = f"{status_emoji} {status.title()}"
        else:
            result_label = f"{status_emoji} {status.title()}"
        
        # Format date from entry or use current time
        detected_at = entry.get('detectedAt', '')
        if detected_at:
            try:
                dt = datetime.fromisoformat(detected_at.replace('Z', '+00:00'))
                date_str = dt.strftime('%Y-%m-%d %H:%M UTC')
            except:
                date_str = detected_at[:16] if len(detected_at) >= 16 else detected_at
        else:
            date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        
        # Extract error type from result text for failed statuses
        error_type = "N/A"
        if status.lower() in ('failed', 'error'):
            if 'maestro' in result_text.lower() or 'flow' in result_text.lower():
                error_type = "Maestro Flow Error"
            elif 'selector' in result_text.lower() or 'element' in result_text.lower() or 'button' in result_text.lower():
                error_type = "Frontend UI Error"
            elif 'schema' in result_text.lower():
                error_type = "Schema Mismatch"
            elif 'api' in result_text.lower() or 'payload' in result_text.lower():
                error_type = "API Error"
            elif 'credit' in result_text.lower() or 'cost' in result_text.lower():
                error_type = "Credit Calculation Error"
            else:
                error_type = "General Error"
        
        # Extract test stats from result_text or entry
        tests_total = entry.get('testsTotal', 0)
        tests_passed = entry.get('testsPassed', 0)
        tests_failed = entry.get('testsFailed', 0)
        
        # Try to parse from result_text if not in entry
        if not tests_total and result_text:
            parsed_total, parsed_passed, parsed_failed = parse_test_stats(result_text)
            if parsed_total > 0:
                tests_total = parsed_total
                tests_passed = parsed_passed
                tests_failed = parsed_failed
        
        lines = [
            f"📦 Commit Update — {repo.title()}",
            f"",
            f"**Status:** {result_label}",
            f"**Project:** {repo}",
            f"**Branch:** {branch}",
            f"**Date:** {date_str}",
        ]
        
        if status.lower() in ('failed', 'error'):
            lines.append(f"**Error Type:** {error_type}")
        
        lines.extend([
            f"**What Changed:** {commit_msg}",
            f"**Files Modified:** {file_count} file{'s' if file_count != 1 else ''}",
        ])
        
        # Add test stats if available
        if tests_total > 0:
            lines.append(f"**Tests Run:** {tests_total} total | ✅ {tests_passed} passed | ❌ {tests_failed} failed")
        
        if result_text:
            # Keep it brief for non-tech people, but extract PR URL if present
            brief = result_text.strip().split('\n')[0][:120]
            lines.append(f"")
            lines.append(f"**Notes:** {brief}")
            
            # Extract PR URL if present in result_text (e.g., "PR created: https://github.com/...")
            import re
            pr_match = re.search(r'https://github\.com/[^\s]+/pull/\d+', result_text)
            if pr_match:
                pr_url = pr_match.group(0)
                lines.append(f"")
                lines.append(f"**PR:** {pr_url}")
        
        # Always add @Dixit Savaliya mention to summary webhook
        lines.append(f"")
        lines.append(f"**Assignee:** @Dixit Savaliya")
        
        return '\n'.join(lines)


def build_test_failure_message(project, test_type, error_type, description, action_taken="", status="failed", technical=True, tests_total=0, tests_passed=0, tests_failed=0, detected_at=""):
    """
    Build test failure message.
    technical=True  -> Full details for Webhook 1
    technical=False -> Clean summary for Webhook 2
    """
    status_emoji = '❌' if status.lower() == 'failed' else '✅'
    
    # Format date
    if detected_at:
        try:
            dt = datetime.fromisoformat(detected_at.replace('Z', '+00:00'))
            date_str = dt.strftime('%Y-%m-%d %H:%M UTC')
        except:
            date_str = detected_at[:16] if len(detected_at) >= 16 else detected_at
    else:
        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    
    if technical:
        # Technical format — full details
        lines = [
            f"**Test Failure Report: {project}**",
            f"",
            f"**Status:** {status.upper()}",
            f"**Project:** {project}",
            f"**Test Type:** {test_type}",
            f"**Error Type:** {error_type}",
            f"**Date:** {date_str}",
        ]
        if tests_total > 0:
            lines.append(f"**Tests:** {tests_total} total | ✅ {tests_passed} passed | ❌ {tests_failed} failed")
        lines.extend([
            f"",
            f"**Description:**",
            description,
        ])
        if action_taken:
            lines.append(f"")
            lines.append(f"**Action Taken:** {action_taken}")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"*Auto-generated by QA Tester*")
        return '\n'.join(lines)
    else:
        # Summary format — clean, non-tech
        lines = [
            f"🧪 Test Result — {project.title()}",
            f"",
            f"**Status:** {status_emoji} {'Failed' if status.lower() == 'failed' else 'Passed'}",
            f"**Project:** {project}",
            f"**Date:** {date_str}",
            f"**Test Type:** {test_type}",
            f"**Error Type:** {error_type}",
        ]
        if tests_total > 0:
            lines.append(f"**Tests Run:** {tests_total} total | ✅ {tests_passed} passed | ❌ {tests_failed} failed")
        lines.extend([
            f"",
            f"**What Happened:**",
            description,
        ])
        if action_taken:
            lines.append(f"")
            lines.append(f"**Action Taken:** {action_taken}")
        
        # Extract PR URL if present in description
        import re
        pr_match = re.search(r'https://github\.com/[^\s]+/pull/\d+', description)
        if pr_match:
            lines.append(f"")
            lines.append(f"**PR:** {pr_match.group(0)}")
        
        # Always add @Dixit Savaliya mention to summary webhook
        lines.append(f"")
        lines.append(f"**Assignee:** @Dixit Savaliya")
        
        return '\n'.join(lines)


def send_entry_dual(entry, result_text="", username="Commit Watcher"):
    """Send both technical and summary formats for a given entry dict."""
    message_full = build_summary_message(entry, result_text, technical=True)
    message_summary = build_summary_message(entry, result_text, technical=False)
    return send_to_both(message_full, message_summary, username)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "send":
        if len(sys.argv) < 3:
            print("Usage: discord-summary.py send <queue_entry_id> [result_text]")
            sys.exit(1)
        
        entry_id = sys.argv[2]
        result_text = sys.argv[3] if len(sys.argv) > 3 else ""
        
        entry = find_entry(entry_id)
        if not entry:
            print(f"Entry not found: {entry_id}")
            sys.exit(1)
        
        message_full = build_summary_message(entry, result_text, technical=True)
        message_summary = build_summary_message(entry, result_text, technical=False)
        
        print("=== TECHNICAL MESSAGE (Webhook 1) ===")
        print(message_full)
        print("=== SUMMARY MESSAGE (Webhook 2) ===")
        print(message_summary)
        print("=== SENDING ===")
        
        success = send_to_both(message_full, message_summary)
        if not success:
            sys.exit(1)
    
    elif cmd == "preview":
        if len(sys.argv) < 3:
            print("Usage: discord-summary.py preview <queue_entry_id> [result_text]")
            sys.exit(1)
        
        entry_id = sys.argv[2]
        result_text = sys.argv[3] if len(sys.argv) > 3 else ""
        
        entry = find_entry(entry_id)
        if not entry:
            print(f"Entry not found: {entry_id}")
            sys.exit(1)
        
        message_full = build_summary_message(entry, result_text, technical=True)
        message_summary = build_summary_message(entry, result_text, technical=False)
        
        print("=== TECHNICAL MESSAGE (Webhook 1) ===")
        print(message_full)
        print("")
        print("=== SUMMARY MESSAGE (Webhook 2) ===")
        print(message_summary)
    
    elif cmd == "daily":
        if len(sys.argv) < 9:
            print("Usage: discord-summary.py daily <date> <desktop_pass> <desktop_fail> <mobile_pass> <mobile_fail> <total_products> <run_dir> [log_dir]")
            sys.exit(1)
        
        date_str = sys.argv[2]
        desktop_pass = int(sys.argv[3])
        desktop_fail = int(sys.argv[4])
        mobile_pass = int(sys.argv[5])
        mobile_fail = int(sys.argv[6])
        total_products = int(sys.argv[7])
        run_dir = sys.argv[8]
        log_dir = sys.argv[9] if len(sys.argv) > 9 else run_dir
        
        total_pass = desktop_pass + mobile_pass
        total_fail = desktop_fail + mobile_fail
        
        # Build technical message for Webhook 1
        tech_lines = [
            f"📅 Daily Maestro Tests — {date_str}",
            f"",
            f"**Products:** {total_products}",
            f"**Desktop:** {desktop_pass} passed, {desktop_fail} failed",
            f"**Mobile:** {mobile_pass} passed, {mobile_fail} failed",
            f"**Total:** {total_pass} passed, {total_fail} failed",
            f"",
            f"**Run Directory:** {run_dir}",
        ]
        
        # Add log file summaries for technical webhook
        if log_dir and os.path.isdir(log_dir):
            tech_lines.append(f"**Log Files:**")
            for log_file in sorted(os.listdir(log_dir)):
                if log_file.endswith('.log'):
                    log_path = os.path.join(log_dir, log_file)
                    tech_lines.append(f"- {log_file}")
                    try:
                        with open(log_path, 'r') as f:
                            lines = f.readlines()[-20:]
                            if lines:
                                tech_lines.append("```")
                                tech_lines.extend([l.rstrip() for l in lines])
                                tech_lines.append("```")
                    except:
                        pass
        
        tech_msg = '\n'.join(tech_lines)
        
        # Build clean summary message for Webhook 2
        status_emoji = "✅" if total_fail == 0 else "❌"
        status_text = "All Passed" if total_fail == 0 else f"{total_fail} Failed"
        
        summary_lines = [
            f"📅 Daily Maestro Tests — {date_str}",
            f"",
            f"**Status:** {status_emoji} {status_text}",
            f"**Date:** {date_str}",
            f"**Products:** {total_products}",
            f"**Tests:** {total_pass} passed | {total_fail} failed",
            f"**Desktop:** ✅ {desktop_pass} | ❌ {desktop_fail}",
            f"**Mobile:** ✅ {mobile_pass} | ❌ {mobile_fail}",
        ]
        
        # Extract error types from log files for summary
        if total_fail > 0 and log_dir and os.path.isdir(log_dir):
            error_types = set()
            for log_file in os.listdir(log_dir):
                if log_file.endswith('.log'):
                    log_path = os.path.join(log_dir, log_file)
                    try:
                        with open(log_path, 'r') as f:
                            content = f.read()
                            if 'command not found' in content:
                                error_types.add("Command Not Found")
                            if 'Chrome instance exited' in content or 'ChromeDriver' in content or 'UnreachableBrowserException' in content:
                                error_types.add("Chrome/CDP Error")
                            if 'TimeoutException' in content:
                                error_types.add("Timeout")
                            if 'assert' in content and 'failed' in content:
                                error_types.add("Assertion Failed")
                            if 'maestro:' in content and 'command not found' not in content:
                                error_types.add("Maestro Error")
                    except:
                        pass
            
            if error_types:
                summary_lines.append(f"**Error Types:** {', '.join(sorted(error_types))}")
            else:
                summary_lines.append(f"**Error Types:** Unknown")
        
        summary_msg = '\n'.join(summary_lines)
        
        print("=== TECHNICAL MESSAGE (Webhook 1) ===")
        print(tech_msg)
        print("")
        print("=== SUMMARY MESSAGE (Webhook 2) ===")
        print(summary_msg)
        print("=== SENDING ===")
        
        success = send_to_both(tech_msg, summary_msg, "Daily Maestro Tests")
        if not success:
            sys.exit(1)
    
    elif cmd == "custom":
        if len(sys.argv) < 3:
            print("Usage: discord-summary.py custom <message_text> [--webhook=1|2|both]")
            sys.exit(1)
        
        # Parse args manually to handle optional --webhook flag
        message = sys.argv[2]
        webhook_target = "both"
        
        for arg in sys.argv[3:]:
            if arg.startswith("--webhook="):
                webhook_target = arg.split("=", 1)[1]
        
        webhooks = load_env()
        tech_url = webhooks.get(WEBHOOK_TECHNICAL)
        sum_url = webhooks.get(WEBHOOK_SUMMARY)
        
        print(f"=== SENDING CUSTOM MESSAGE (target={webhook_target}) ===")
        
        results = []
        if webhook_target in ("1", "both"):
            if tech_url:
                results.append(send_webhook_to(tech_url, message))
            else:
                print(f"  ⚠️ Technical webhook not found")
                results.append(False)
        
        if webhook_target in ("2", "both"):
            if sum_url:
                results.append(send_webhook_to(sum_url, message))
            else:
                print(f"  ⚠️ Summary webhook not found")
                results.append(False)
        
        if not any(results):
            sys.exit(1)
    
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
