#!/usr/bin/env python3
"""Evaluate programmatic assertions against an output file.

Usage:
    python evaluate_assertions.py --output-file <path> --expectations '<json>'
    python evaluate_assertions.py --output-text "inline text" --expectations '<json>'

Assertions JSON format:
    [
        {"type": "contains", "value": "expected substring"},
        {"type": "not_contains", "value": "forbidden substring"},
        {"type": "regex", "value": "\\d{4}-\\d{2}-\\d{2}"},
        {"type": "file_exists", "value": "output/report.md"},
        {"type": "json_valid"},
        {"type": "script", "value": "pytest tests/ -x"}
    ]

Only evaluates programmatic types. LLM-judged types (llm_judge, fact_coverage)
are skipped with result "SKIPPED_LLM_REQUIRED".

Output: JSON array of results to stdout.
Exit code: 0 if all programmatic assertions pass, 1 if any fail, 2 on error.
"""

import argparse
import json
import os
import re
import subprocess
import sys


def load_output(args):
    if args.output_text:
        return args.output_text
    if args.output_file:
        if not os.path.exists(args.output_file):
            return None
        with open(args.output_file, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    return None


def check_contains(output, value):
    if output is None:
        return False, "Output is None"
    found = value in output
    if found:
        return True, f"Found '{value}'"
    return False, f"'{value}' not found in output"


def check_not_contains(output, value):
    if output is None:
        return True, "Output is None (vacuously true)"
    found = value in output
    if not found:
        return True, f"'{value}' correctly absent"
    return False, f"'{value}' found in output but should not be"


def check_regex(output, pattern):
    if output is None:
        return False, "Output is None"
    try:
        match = re.search(pattern, output, re.MULTILINE)
        if match:
            return True, f"Matched: '{match.group()}'"
        return False, f"Pattern '{pattern}' not found"
    except re.error as e:
        return False, f"Invalid regex: {e}"


def check_file_exists(_, path):
    if os.path.exists(path):
        return True, f"File exists: {path}"
    return False, f"File not found: {path}"


def check_json_valid(output, _=None):
    if output is None:
        return False, "Output is None"
    try:
        json.loads(output)
        return True, "Valid JSON"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"


def check_script(_, command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return True, f"Script passed (exit 0)"
        return False, f"Script failed (exit {result.returncode}): {result.stderr[:200]}"
    except subprocess.TimeoutExpired:
        return False, "Script timed out (60s)"
    except Exception as e:
        return False, f"Script error: {e}"


CHECKERS = {
    "contains": check_contains,
    "not_contains": check_not_contains,
    "regex": check_regex,
    "file_exists": check_file_exists,
    "json_valid": check_json_valid,
    "script": check_script,
}

LLM_TYPES = {"llm_judge", "fact_coverage"}


def evaluate(output, expectations):
    results = []
    for exp in expectations:
        exp_type = exp.get("type", "")
        exp_value = exp.get("value", "")

        if exp_type in LLM_TYPES:
            results.append({
                "type": exp_type,
                "value": exp_value,
                "passed": None,
                "evidence": "SKIPPED_LLM_REQUIRED",
            })
            continue

        checker = CHECKERS.get(exp_type)
        if not checker:
            results.append({
                "type": exp_type,
                "value": exp_value,
                "passed": False,
                "evidence": f"Unknown assertion type: {exp_type}",
            })
            continue

        passed, evidence = checker(output, exp_value)
        results.append({
            "type": exp_type,
            "value": exp_value,
            "passed": passed,
            "evidence": evidence,
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate programmatic assertions")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output-file", help="Path to the output file to check")
    group.add_argument("--output-text", help="Inline output text to check")
    parser.add_argument("--expectations", required=True, help="JSON array of assertions")

    args = parser.parse_args()

    try:
        expectations = json.loads(args.expectations)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid expectations JSON: {e}"}))
        sys.exit(2)

    output = load_output(args)
    results = evaluate(output, expectations)

    print(json.dumps(results, indent=2, ensure_ascii=False))

    programmatic_results = [r for r in results if r["passed"] is not None]
    if all(r["passed"] for r in programmatic_results):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
