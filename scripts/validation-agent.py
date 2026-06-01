#!/usr/bin/env python3
"""
validation-agent.py — Validate Maestro YAML flows before deployment

Usage:
  python3 validation-agent.py validate <flow_file_or_folder>
    - Validate a single YAML file or all YAML files in a folder
  python3 validation-agent.py validate --product=chromastudio
    - Validate all flows for a specific product
  python3 validation-agent.py report <output_file>
    - Generate validation report and save to file

Checks:
  1. YAML syntax validity
  2. Duplicate step detection (same action repeated)
  3. Selector verification (valid patterns, not empty)
  4. Flow dependency check (referenced flows exist)
  5. Required fields present (appId, flow structure)
"""

import sys
import os
import re
import yaml
import json
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

# Maestro field patterns
SELECTOR_PATTERNS = {
    "data-maestro": re.compile(r'data-maestro="([^"]+)"'),
    "data-testid": re.compile(r'data-testid="([^"]+)"'),
    "id": re.compile(r'id="([^"]+)"'),
    "text": re.compile(r'text:\s*"([^"]+)"'),
    "class": re.compile(r'class="([^"]+)"'),
    "css": re.compile(r'css:\s*"([^"]+)"'),
}

VALID_MAESTRO_ACTIONS = {
    "launchApp", "openLink", "tapOn", "doubleTapOn", "longPressOn",
    "assertVisible", "assertNotVisible", "assertTrue", "assertNotTrue",
    "waitForAnimationToEnd", "stopApp", "takeScreenshot", "scrollUntilVisible",
    "scroll", "swipe", "inputText", "clearState", "evalScript",
    "runFlow", "runScript", "repeat", "copyTextFrom", "pasteText",
    "hideKeyboard", "pressKey", "setLocation", "travel", "eraseText",
    "addMedia", "removeMedia", "mockNetwork", "setAirplaneMode",
    "setBluetooth", "setWifi", "setCellular", "setBrightness",
    "setVolume", "setScreenBrightness", "setScreenOffTimeout",
    "setScreenOrientation", "setScreenReader", "setScreenSize",
    "setScreenDensity", "setScreenDpi", "setScreenInsets",
    "setScreenWidth", "setScreenHeight", "setScreenRefreshRate",
    "setScreenDensityDpi", "setScreenDensityX", "setScreenDensityY",
    "setScreenDensityX", "setScreenDensityY", "setScreenDensityDpi",
    "extendedWaitUntil", "waitUntil", "waitUntilVisible", "waitUntilNotVisible",
    "checkWebview", "checkWebView", "checkWebViewElement",
    "isVisible", "isNotVisible", "isTrue", "isNotTrue",
    "ifVisible", "ifNotVisible", "optional", "loop",
    "addStep", "addStepLabel", "label", "stepLabel",
    "setAirplaneMode", "setBluetooth", "setWifi", "setCellular",
    "setBrightness", "setVolume", "setScreenBrightness",
    "setScreenOffTimeout", "setScreenOrientation", "setScreenReader",
    "setScreenSize", "setScreenDensity", "setScreenDpi", "setScreenInsets",
    "setScreenWidth", "setScreenHeight", "setScreenRefreshRate",
    "setScreenDensityDpi", "setScreenDensityX", "setScreenDensityY",
    "setScreenDensityX", "setScreenDensityY", "setScreenDensityDpi",
    "setScreenDensityX", "setScreenDensityY", "setScreenDensityDpi",
}

VALID_SELECTOR_TYPES = {
    "id", "text", "css", "xpath", "point", "containsDescendants",
    "containsChild", "containsDescendants", "containsChildren",
    "rightOf", "leftOf", "above", "below", "containsText",
    "containsId", "containsClassName", "containsTag",
}


class ValidationResult:
    """Stores validation results for a single file."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.errors = []
        self.warnings = []
        self.info = []
        self.valid = True

    def add_error(self, message, line=None):
        self.valid = False
        if line:
            self.errors.append(f"[Line {line}] {message}")
        else:
            self.errors.append(message)

    def add_warning(self, message, line=None):
        if line:
            self.warnings.append(f"[Line {line}] {message}")
        else:
            self.warnings.append(message)

    def add_info(self, message):
        self.info.append(message)

    def to_dict(self):
        return {
            "filepath": self.filepath,
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


class MaestroValidator:
    """Validates Maestro YAML flow files."""

    def __init__(self, maestro_repo="/root/.openclaw/workspace/repos/maestro-studio"):
        self.maestro_repo = maestro_repo
        self.results = []
        self.all_files = set()

    def scan_all_files(self, product=None):
        """Scan all YAML files in maestro repo."""
        if product:
            base = os.path.join(self.maestro_repo, product)
        else:
            base = self.maestro_repo

        for root, dirs, files in os.walk(base):
            # Skip non-Maestro directories
            if any(skip in root for skip in ["__pycache__", ".git", "node_modules"]):
                continue
            for f in files:
                if f.endswith(".yaml") or f.endswith(".yml"):
                    self.all_files.add(os.path.join(root, f))

    def validate_file(self, filepath):
        """Validate a single Maestro YAML file."""
        result = ValidationResult(filepath)

        if not os.path.exists(filepath):
            result.add_error(f"File not found: {filepath}")
            return result

        # Check 1: YAML syntax validity
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                raw_lines = content.split("\n")
        except Exception as e:
            result.add_error(f"Cannot read file: {e}")
            return result

        # Check for YAML syntax
        try:
            docs = list(yaml.safe_load_all(content))
        except yaml.YAMLError as e:
            result.add_error(f"YAML syntax error: {e}")
            return result
        except Exception as e:
            result.add_error(f"YAML parse error: {e}")
            return result

        # Check for appId in first document
        if not docs or not docs[0]:
            result.add_error("Missing or empty YAML document")
            return result

        first_doc = docs[0]
        if isinstance(first_doc, dict):
            if "appId" not in first_doc:
                result.add_error("Missing required field: appId (must be in first document)")
        else:
            result.add_error("First document must be a mapping with appId")

        # Check 2: Duplicate step detection
        seen_steps = defaultdict(int)
        for i, doc in enumerate(docs):
            if isinstance(doc, list):
                for j, step in enumerate(doc):
                    if isinstance(step, dict):
                        step_str = json.dumps(step, sort_keys=True)
                        seen_steps[step_str] += 1
                        if seen_steps[step_str] > 1:
                            # Find the line number
                            line_num = self._find_step_line(raw_lines, step, j)
                            result.add_warning(
                                f"Duplicate step detected (appears {seen_steps[step_str]} times): {self._summarize_step(step)}",
                                line=line_num,
                            )

        # Check 3: Selector verification
        for i, doc in enumerate(docs):
            if isinstance(doc, list):
                for j, step in enumerate(doc):
                    if isinstance(step, dict):
                        self._validate_selectors(step, result, raw_lines, j)
                        self._validate_action(step, result, raw_lines, j)

        # Check 4: Flow dependency check
        for i, doc in enumerate(docs):
            if isinstance(doc, list):
                for j, step in enumerate(doc):
                    if isinstance(step, dict):
                        self._validate_dependencies(step, result, filepath, raw_lines, j)

        # Check 5: Required fields in specific actions
        for i, doc in enumerate(docs):
            if isinstance(doc, list):
                for j, step in enumerate(doc):
                    if isinstance(step, dict):
                        self._validate_required_fields(step, result, raw_lines, j)

        result.add_info(f"Validated {len(docs)} YAML document(s)")
        return result

    def _find_step_line(self, raw_lines, step, step_index):
        """Find approximate line number for a step."""
        try:
            step_str = json.dumps(step, sort_keys=True)
            for i, line in enumerate(raw_lines):
                if any(
                    key in line for key in step.keys()
                ):
                    return i + 1
        except:
            pass
        return step_index + 1

    def _summarize_step(self, step):
        """Create a short summary of a step for warnings."""
        if not step:
            return "empty step"
        action = list(step.keys())[0] if step else "unknown"
        if action == "tapOn":
            sel = step.get("tapOn", "")
            return f"tapOn: {str(sel)[:50]}"
        elif action == "assertVisible":
            sel = step.get("assertVisible", "")
            return f"assertVisible: {str(sel)[:50]}"
        elif action == "openLink":
            url = step.get("openLink", "")
            return f"openLink: {str(url)[:50]}"
        elif action == "runFlow":
            flow = step.get("runFlow", "")
            return f"runFlow: {str(flow)[:50]}"
        return f"{action}: {str(step.get(action, ''))[:50]}"

    def _validate_selectors(self, step, result, raw_lines, step_index):
        """Validate selectors in a step."""
        for action, value in step.items():
            if action in ["tapOn", "assertVisible", "assertNotVisible", "scrollUntilVisible"]:
                if isinstance(value, str):
                    # Simple text selector
                    if not value.strip():
                        line = self._find_step_line(raw_lines, step, step_index)
                        result.add_error(
                            f"Empty selector in {action} (text selector cannot be empty)",
                            line=line,
                        )
                    elif len(value) < 2:
                        line = self._find_step_line(raw_lines, step, step_index)
                        result.add_warning(
                            f"Very short selector in {action}: '{value}'",
                            line=line,
                        )
                elif isinstance(value, dict):
                    # Complex selector with keys like id, text, css, etc.
                    has_valid_selector = False
                    for key in value.keys():
                        if key in VALID_SELECTOR_TYPES:
                            has_valid_selector = True
                            sel_value = value[key]
                            if not sel_value or (isinstance(sel_value, str) and not sel_value.strip()):
                                line = self._find_step_line(raw_lines, step, step_index)
                                result.add_error(
                                    f"Empty selector value for '{key}' in {action}",
                                    line=line,
                                )
                            # Check for data-maestro / data-testid patterns
                            if key in ["id", "text"] and isinstance(sel_value, str):
                                if sel_value.startswith("data-maestro") and "=" in sel_value:
                                    match = SELECTOR_PATTERNS["data-maestro"].search(sel_value)
                                    if not match or not match.group(1).strip():
                                        line = self._find_step_line(raw_lines, step, step_index)
                                        result.add_error(
                                            f"Invalid data-maestro selector: {sel_value}",
                                            line=line,
                                        )
                                elif sel_value.startswith("data-testid") and "=" in sel_value:
                                    match = SELECTOR_PATTERNS["data-testid"].search(sel_value)
                                    if not match or not match.group(1).strip():
                                        line = self._find_step_line(raw_lines, step, step_index)
                                        result.add_error(
                                            f"Invalid data-testid selector: {sel_value}",
                                            line=line,
                                        )
                    if not has_valid_selector and action not in ["evalScript", "runFlow"]:
                        # Allow standard Maestro keys that are not in SELECTOR_TYPES
                        standard_keys = {"element", "direction", "timeout", "speed", "maxDepth", "childIndex", "index", "parentId", "containsDescendants", "containsChild", "optional", "label", "when", "enabled", "visible", "checked"}
                        non_standard = [k for k in value.keys() if k not in VALID_SELECTOR_TYPES and k not in standard_keys]
                        if non_standard:
                            line = self._find_step_line(raw_lines, step, step_index)
                            result.add_warning(
                                f"Selector in {action} uses non-standard keys: {non_standard}",
                                line=line,
                            )

    def _validate_action(self, step, result, raw_lines, step_index):
        """Validate Maestro action names."""
        for action in step.keys():
            if action not in VALID_MAESTRO_ACTIONS:
                line = self._find_step_line(raw_lines, step, step_index)
                result.add_warning(
                    f"Unknown action: '{action}' (might be a custom or deprecated action)",
                    line=line,
                )

    def _validate_dependencies(self, step, result, filepath, raw_lines, step_index):
        """Check if runFlow references exist."""
        if "runFlow" in step:
            flow_ref = step["runFlow"]
            if isinstance(flow_ref, str):
                # Check if it's a relative or absolute path
                if flow_ref.startswith("/") or flow_ref.startswith("./") or flow_ref.startswith("../"):
                    # Check if file exists
                    base_dir = os.path.dirname(filepath)
                    possible_paths = [
                        os.path.join(base_dir, flow_ref),
                        os.path.join(self.maestro_repo, flow_ref),
                        flow_ref,
                    ]
                    found = any(os.path.exists(p) for p in possible_paths)
                    if not found:
                        line = self._find_step_line(raw_lines, step, step_index)
                        result.add_error(
                            f"Referenced flow not found: {flow_ref}",
                            line=line,
                        )
                elif flow_ref.startswith("subflows/") or flow_ref.startswith("flows/"):
                    # Check relative to maestro repo
                    possible_path = os.path.join(self.maestro_repo, flow_ref)
                    if not os.path.exists(possible_path) and not os.path.exists(possible_path + ".yaml"):
                        line = self._find_step_line(raw_lines, step, step_index)
                        result.add_error(
                            f"Referenced flow not found: {flow_ref}",
                            line=line,
                        )
                else:
                    # Just a filename, check in same directory and common locations
                    base_dir = os.path.dirname(filepath)
                    possible_paths = [
                        os.path.join(base_dir, flow_ref),
                        os.path.join(base_dir, flow_ref + ".yaml"),
                        os.path.join(base_dir, "subflows", flow_ref),
                        os.path.join(base_dir, "subflows", flow_ref + ".yaml"),
                        os.path.join(base_dir, "shared", flow_ref),
                        os.path.join(base_dir, "shared", flow_ref + ".yaml"),
                    ]
                    found = any(os.path.exists(p) for p in possible_paths)
                    if not found:
                        line = self._find_step_line(raw_lines, step, step_index)
                        result.add_error(
                            f"Referenced flow not found: {flow_ref} (checked: {', '.join(possible_paths)})",
                            line=line,
                        )
            elif isinstance(flow_ref, dict):
                # runFlow with 'when' condition, etc.
                file_ref = flow_ref.get("file", "")
                if file_ref:
                    self._validate_dependencies({"runFlow": file_ref}, result, filepath, raw_lines, step_index)

    def _validate_required_fields(self, step, result, raw_lines, step_index):
        """Check required fields for specific actions."""
        for action, value in step.items():
            if action == "openLink":
                if not value or (isinstance(value, str) and not value.strip()):
                    line = self._find_step_line(raw_lines, step, step_index)
                    result.add_error(
                        "openLink requires a URL value",
                        line=line,
                    )
                elif isinstance(value, str) and not value.startswith(("http://", "https://")):
                    line = self._find_step_line(raw_lines, step, step_index)
                    result.add_warning(
                        f"openLink URL should start with http:// or https://: {value}",
                        line=line,
                    )
            elif action == "tapOn":
                if not value or (isinstance(value, str) and not value.strip()):
                    line = self._find_step_line(raw_lines, step, step_index)
                    result.add_error(
                        "tapOn requires a selector value",
                        line=line,
                    )
            elif action == "inputText":
                if not value or (isinstance(value, str) and not value.strip()):
                    line = self._find_step_line(raw_lines, step, step_index)
                    result.add_error(
                        "inputText requires a text value",
                        line=line,
                    )

    def validate_folder(self, folder_path, recursive=True):
        """Validate all YAML files in a folder."""
        results = []
        pattern = "**/*.yaml" if recursive else "*.yaml"
        yaml_files = Path(folder_path).glob(pattern)

        for yaml_file in yaml_files:
            # Skip non-Maestro files
            if any(skip in str(yaml_file) for skip in ["__pycache__", ".git", "node_modules"]):
                continue
            result = self.validate_file(str(yaml_file))
            results.append(result)
            self.results.append(result)

        return results

    def validate_product(self, product_name):
        """Validate all flows for a specific product."""
        product_path = os.path.join(self.maestro_repo, product_name)
        if not os.path.exists(product_path):
            print(f"ERROR: Product not found: {product_name}")
            return []
        return self.validate_folder(product_path, recursive=True)

    def generate_report(self, output_file=None):
        """Generate validation report."""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_files": len(self.results),
            "valid_files": sum(1 for r in self.results if r.valid),
            "invalid_files": sum(1 for r in self.results if not r.valid),
            "total_errors": sum(len(r.errors) for r in self.results),
            "total_warnings": sum(len(r.warnings) for r in self.results),
            "files": [r.to_dict() for r in self.results],
        }

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            print(f"Report saved to: {output_file}")

        return report

    def print_summary(self):
        """Print validation summary to console."""
        print("\n" + "=" * 70)
        print("  MAESTRO VALIDATION REPORT")
        print("=" * 70)
        print(f"  Total files checked: {len(self.results)}")
        print(f"  ✅ Valid: {sum(1 for r in self.results if r.valid)}")
        print(f"  ❌ Invalid: {sum(1 for r in self.results if not r.valid)}")
        print(f"  ⚠️ Warnings: {sum(len(r.warnings) for r in self.results)}")
        print(f"  📝 Errors: {sum(len(r.errors) for r in self.results)}")
        print("=" * 70)

        for result in self.results:
            if not result.valid or result.warnings:
                status = "❌ INVALID" if not result.valid else "⚠️ WARNINGS"
                print(f"\n{status}: {result.filepath}")
                for error in result.errors:
                    print(f"  ❌ {error}")
                for warning in result.warnings:
                    print(f"  ⚠️ {warning}")

        print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Maestro YAML Validation Agent")
    parser.add_argument("command", choices=["validate", "report"], help="Command to run")
    parser.add_argument("target", nargs="?", help="File or folder to validate")
    parser.add_argument("--product", help="Validate specific product (chromastudio, maxstudio, etc.)")
    parser.add_argument("--output", "-o", help="Output file for report")
    parser.add_argument("--repo", default="/root/.openclaw/workspace/repos/maestro-studio", help="Maestro repo path")

    args = parser.parse_args()

    validator = MaestroValidator(maestro_repo=args.repo)

    if args.command == "validate":
        if args.product:
            results = validator.validate_product(args.product)
        elif args.target:
            if os.path.isfile(args.target):
                result = validator.validate_file(args.target)
                validator.results.append(result)
            elif os.path.isdir(args.target):
                results = validator.validate_folder(args.target)
            else:
                print(f"ERROR: Target not found: {args.target}")
                sys.exit(1)
        else:
            # Validate entire repo
            results = validator.validate_folder(args.repo)

        validator.print_summary()

    elif args.command == "report":
        if args.product:
            validator.validate_product(args.product)
        elif args.target:
            if os.path.isfile(args.target):
                result = validator.validate_file(args.target)
                validator.results.append(result)
            elif os.path.isdir(args.target):
                validator.validate_folder(args.target)
        else:
            validator.validate_folder(args.repo)

        report = validator.generate_report(args.output)
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
