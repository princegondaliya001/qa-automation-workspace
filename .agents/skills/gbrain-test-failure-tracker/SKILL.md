# GBrain Test Failure Tracker

Track test failures in GBrain for institutional memory and pattern recognition.

## When to use

- When a Maestro test fails and you want to store it for future reference
- When you want to check if a similar failure has happened before
- When you want to build a knowledge base of common failures and fixes
- When you want to query past failures to find patterns

## Installation

GBrain must be installed and configured:

```bash
# Check if gbrain is available
which gbrain

# If not, install it:
curl -fsSL https://bun.sh/install | bash
export PATH="$HOME/.bun/bin:$PATH"
bun install -g github:garrytan/gbrain

# Set up environment (add to ~/.bashrc or /root/.openclaw/workspace/state/maestro-discord.env)
export ZEROENTROPY_API_KEY=ze_...
export VOYAGE_API_KEY=pa_...
export PATH="$HOME/.bun/bin:$PATH"
```

## Initialize brain source

```bash
gbrain sources add testing-automation
```

## Usage

### Store a failure

```bash
python3 scripts/gbrain-test-failure-tracker.py store \
  <product> <test_type> <error_type> <description> \
  [--action="fix applied"] \
  [--result="pass/fail"]
```

Example:
```bash
python3 scripts/gbrain-test-failure-tracker.py store \
  deepswapper "schema-check" "chrome-cdp" \
  "Chrome instance exited unexpectedly during schema validation" \
  --action="Killed zombie Chrome processes, cleared temp profiles" \
  --result="pass"
```

### Query past failures

```bash
python3 scripts/gbrain-test-failure-tracker.py query "Chrome crash"
python3 scripts/gbrain-test-failure-tracker.py query "DeepSwapper selector"
python3 scripts/gbrain-test-failure-tracker.py query "schema mismatch"
```

### Get product summary

```bash
python3 scripts/gbrain-test-failure-tracker.py summary chromastudio
python3 scripts/gbrain-test-failure-tracker.py summary maxstudio
```

## Integration with failed-automation workflow

When a Captain Hook failure arrives:

1. **Triage** the failure (skill: failed-automation-queue)
2. **Store** the failure to GBrain:
   ```bash
   python3 scripts/gbrain-test-failure-tracker.py store \
     <product> <test_type> <error_type> <description> \
     --action="fix applied" --result="pass"
   ```
3. **Query** GBrain for similar past failures:
   ```bash
   python3 scripts/gbrain-test-failure-tracker.py query "<error keywords>"
   ```
4. If similar failure found, apply known fix
5. If new failure, investigate and store fix

## File structure

```
~/brain/
└── testing-automation/
    └── failures/
        ├── chromastudio-home-smoke-selector-missing-2026-06-01.md
        ├── deepswapper-schema-check-chrome-cdp-2026-06-01.md
        └── maxstudio-login-timeout-2026-05-31.md
```

## GBrain source

- **Source name:** `testing-automation`
- **Location:** `~/brain/`
- **Query:** `gbrain search <term> --source testing-automation`

## Benefits

1. **Pattern recognition** — "Has this error happened before?"
2. **Known fix lookup** — "What fixed this last time?"
3. **Trend analysis** — "Which products fail most often?"
4. **Onboarding** — New agents can query brain for common issues
5. **Runbook building** — Accumulate fixes into institutional knowledge

## Example query results

```
$ gbrain search "Chrome crash" --source testing-automation

[0.8763] inbox/2026-06-01-b29b14fd -- # Test Failure: DeepSwapper Schema Check
[0.8121] inbox/2026-06-01-e806e58a -- # Test Failure: ChromaStudio Home Smoke
```

## Maintenance

- Run `gbrain doctor --json` to check brain health
- Run `gbrain sync --source testing-automation` to re-index if needed
- Clean old failures (>90 days) periodically if storage grows

## Related

- `failed-automation-queue` skill — Discord failure triage
- `commit-to-maestro` skill — Commit watcher workflow
- `maestro-studio` skill — Maestro flow management
