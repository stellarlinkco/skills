#!/usr/bin/env python3
"""Track evolution results in TSV and JSONL formats.

Usage:
    python results_tracker.py <workspace> init
    python results_tracker.py <workspace> init --mode scoreboard

    python results_tracker.py <workspace> log \
        --iteration 5 --layer 2 --mutation-type "disambiguation" \
        --description "Added hint for ambiguous queries" \
        --pass-rate 0.86 --delta 0.04 --decision KEEP \
        --tokens 12400 --duration 91.3

    python results_tracker.py <workspace> log --mode scoreboard \
        --iteration 0 --layer 0 --mutation-type "baseline" \
        --description "Baseline run" \
        --metric-name val_bpb --metric-value 1.0000 --metric-direction minimize \
        --delta 0.0 --decision BASELINE

    python results_tracker.py <workspace> log --mode scoreboard \
        --iteration 5 --layer 2 --mutation-type "optimizer-change" \
        --description "Changed optimizer schedule" \
        --metric-name val_bpb --metric-value 0.9975 --metric-direction minimize \
        --delta -0.0025 --decision KEEP --duration 91.3

    python results_tracker.py <workspace> summary
    python results_tracker.py <workspace> best
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone


GT_TSV_HEADER = "iteration\tlayer\tmutation_type\tdescription\tpass_rate\tdelta\tdecision\ttokens\tduration_s\ttimestamp\n"
SCOREBOARD_TSV_HEADER = "iteration\tlayer\tmutation_type\tdescription\tmetric_name\tmetric_value\tmetric_direction\tdelta\tdecision\ttokens\tduration_s\ttimestamp\n"


def fail(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(2)


def format_float(value):
    return f"{value:.10g}"


def tsv_cell(value):
    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")


def init_workspace(workspace, mode="gt"):
    os.makedirs(workspace, exist_ok=True)
    if mode != "scoreboard":
        os.makedirs(os.path.join(workspace, "gt"), exist_ok=True)
    os.makedirs(os.path.join(workspace, "traces"), exist_ok=True)
    os.makedirs(os.path.join(workspace, "iterations"), exist_ok=True)

    tsv_path = os.path.join(workspace, "results.tsv")
    if not os.path.exists(tsv_path):
        header = SCOREBOARD_TSV_HEADER if mode == "scoreboard" else GT_TSV_HEADER
        with open(tsv_path, "w") as f:
            f.write(header)

    jsonl_path = os.path.join(workspace, "experiments.jsonl")
    if not os.path.exists(jsonl_path):
        open(jsonl_path, "w").close()

    print(f"Workspace initialized: {workspace} (mode={mode})")


def log_result(workspace, args):
    timestamp = datetime.now(timezone.utc).isoformat()

    experiment = {
        "iteration": args.iteration,
        "layer": args.layer,
        "mutation_type": args.mutation_type,
        "description": args.description,
        "delta": args.delta,
        "decision": args.decision,
        "tokens": args.tokens,
        "duration_seconds": args.duration,
        "timestamp": timestamp,
    }

    if args.mode == "scoreboard":
        if args.metric_name is None:
            fail("--metric-name is required in scoreboard mode")
        if args.metric_value is None:
            fail("--metric-value is required in scoreboard mode")
        if args.metric_direction is None:
            fail("--metric-direction is required in scoreboard mode")
        if args.delta is None:
            fail("--delta is required in scoreboard mode")

        tsv_line = (
            f"{args.iteration}\t{args.layer}\t{tsv_cell(args.mutation_type)}\t"
            f"{tsv_cell(args.description)}\t{tsv_cell(args.metric_name)}\t{format_float(args.metric_value)}\t"
            f"{args.metric_direction}\t{args.delta:+.4f}\t{args.decision}\t"
            f"{args.tokens}\t{args.duration:.1f}\t{timestamp}\n"
        )
        experiment.update({
            "metric_name": args.metric_name,
            "metric_value": args.metric_value,
            "metric_direction": args.metric_direction,
        })
        status_text = f"{args.metric_name}={format_float(args.metric_value)}, delta={args.delta:+.4f}"
    else:
        if args.pass_rate is None:
            fail("--pass-rate is required in gt mode")
        if args.delta is None:
            fail("--delta is required in gt mode")

        tsv_line = (
            f"{args.iteration}\t{args.layer}\t{tsv_cell(args.mutation_type)}\t"
            f"{tsv_cell(args.description)}\t{args.pass_rate:.4f}\t{args.delta:+.4f}\t"
            f"{args.decision}\t{args.tokens}\t{args.duration:.1f}\t{timestamp}\n"
        )
        experiment["pass_rate"] = args.pass_rate
        status_text = f"pass_rate={args.pass_rate:.4f}, delta={args.delta:+.4f}"

    tsv_path = os.path.join(workspace, "results.tsv")
    with open(tsv_path, "a") as f:
        f.write(tsv_line)

    if args.gate_details:
        try:
            experiment["gate_details"] = json.loads(args.gate_details)
        except json.JSONDecodeError:
            experiment["gate_details_raw"] = args.gate_details

    if args.target_cases:
        experiment["target_cases"] = args.target_cases.split(",")

    if args.regressions:
        experiment["regressions"] = args.regressions.split(",")
    else:
        experiment["regressions"] = []

    jsonl_path = os.path.join(workspace, "experiments.jsonl")
    with open(jsonl_path, "a") as f:
        f.write(json.dumps(experiment, ensure_ascii=False) + "\n")

    print(f"Logged iteration {args.iteration}: {args.decision} ({status_text})")


def is_scoreboard_entry(exp):
    return "metric_value" in exp or "metric_after" in exp


def parse_metric_value(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        if "/" in value:
            numerator, denominator = value.split("/", 1)
            try:
                return float(numerator) / float(denominator)
            except ValueError:
                return None
        try:
            return float(value)
        except ValueError:
            return None
    return None


def comparable_metric(exp):
    if "metric_value" in exp:
        value = parse_metric_value(exp["metric_value"])
        if value is not None:
            return value, exp.get("metric_direction", "maximize")
    if "pass_rate" in exp:
        return float(exp["pass_rate"]), "maximize"
    if "metric_after" in exp:
        value = parse_metric_value(exp["metric_after"])
        if value is not None:
            return value, exp.get("metric_direction", "maximize")
    return None


def is_better(candidate, incumbent):
    candidate_metric = comparable_metric(candidate)
    if candidate_metric is None:
        return False
    if incumbent is None:
        return True
    incumbent_metric = comparable_metric(incumbent)
    if incumbent_metric is None:
        return True

    candidate_value, direction = candidate_metric
    incumbent_value, _ = incumbent_metric
    if direction == "minimize":
        return candidate_value < incumbent_value
    return candidate_value > incumbent_value


def best_kept_experiment(experiments):
    best = None
    for exp in experiments:
        if exp["decision"] in {"KEEP", "BASELINE"} and is_better(exp, best):
            best = exp
    return best


def format_metric(exp):
    metric = comparable_metric(exp)
    if metric is None:
        return "unscored"
    value, direction = metric
    if "metric_name" in exp:
        return f"{exp['metric_name']}: {format_float(value)} ({direction})"
    if "metric_after" in exp:
        return f"metric_after: {format_float(value)} ({direction})"
    return f"pass_rate: {value:.4f}"


def show_summary(workspace):
    jsonl_path = os.path.join(workspace, "experiments.jsonl")
    if not os.path.exists(jsonl_path):
        print("No experiments found.")
        return

    experiments = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                experiments.append(json.loads(line))

    if not experiments:
        print("No experiments found.")
        return

    total = len(experiments)
    baseline = sum(1 for e in experiments if e["decision"] == "BASELINE")
    kept = sum(1 for e in experiments if e["decision"] == "KEEP")
    discarded = sum(1 for e in experiments if e["decision"] == "DISCARD")
    best = best_kept_experiment(experiments)
    latest = experiments[-1]

    print(f"Total iterations: {total}")
    print(f"Baseline: {baseline}")
    print(f"Kept: {kept}, Discarded: {discarded}")
    if best:
        print(f"Best {format_metric(best)} (iteration {best['iteration']})")
    print(f"Latest {format_metric(latest)} (iteration {latest['iteration']})")

    by_layer = {}
    for e in experiments:
        layer = e.get("layer", "unknown")
        if layer not in by_layer:
            by_layer[layer] = {"baseline": 0, "kept": 0, "discarded": 0}
        if e["decision"] == "BASELINE":
            by_layer[layer]["baseline"] += 1
        elif e["decision"] == "KEEP":
            by_layer[layer]["kept"] += 1
        else:
            by_layer[layer]["discarded"] += 1

    print("\nPer-layer breakdown:")
    for layer in sorted(by_layer, key=str):
        stats = by_layer[layer]
        print(f"  Layer {layer}: {stats['baseline']} baseline, {stats['kept']} kept, {stats['discarded']} discarded")


def show_best(workspace):
    jsonl_path = os.path.join(workspace, "experiments.jsonl")
    if not os.path.exists(jsonl_path):
        print(json.dumps({"error": "No experiments found"}))
        sys.exit(1)

    experiments = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                experiments.append(json.loads(line))

    best = best_kept_experiment(experiments)

    if best:
        print(json.dumps(best, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"error": "No kept iterations found"}))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Evolution results tracker")
    parser.add_argument("workspace", help="Path to evolution workspace")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize workspace")
    init_parser.add_argument("--mode", choices=["gt", "scoreboard"], default="gt")

    log_parser = subparsers.add_parser("log", help="Log an iteration result")
    log_parser.add_argument("--mode", choices=["gt", "scoreboard"], default="gt")
    log_parser.add_argument("--iteration", type=int, required=True)
    log_parser.add_argument("--layer", type=int, required=True)
    log_parser.add_argument("--mutation-type", required=True)
    log_parser.add_argument("--description", required=True)
    log_parser.add_argument("--pass-rate", type=float)
    log_parser.add_argument("--metric-name")
    log_parser.add_argument("--metric-value", type=float)
    log_parser.add_argument("--metric-direction", choices=["minimize", "maximize"])
    log_parser.add_argument("--delta", type=float, required=True)
    log_parser.add_argument("--decision", choices=["BASELINE", "KEEP", "DISCARD"], required=True)
    log_parser.add_argument("--tokens", type=int, default=0)
    log_parser.add_argument("--duration", type=float, default=0.0)
    log_parser.add_argument("--gate-details", default=None)
    log_parser.add_argument("--target-cases", default=None)
    log_parser.add_argument("--regressions", default=None)

    subparsers.add_parser("summary", help="Show evolution summary")
    subparsers.add_parser("best", help="Show best kept iteration")

    args = parser.parse_args()

    if args.command == "init":
        init_workspace(args.workspace, args.mode)
    elif args.command == "log":
        log_result(args.workspace, args)
    elif args.command == "summary":
        show_summary(args.workspace)
    elif args.command == "best":
        show_best(args.workspace)


if __name__ == "__main__":
    main()
