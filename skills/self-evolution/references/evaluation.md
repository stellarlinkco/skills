# 3-Layer Evaluation Pipeline

## Contents
- Overview
- L1 — Quick Gate (seconds, every iteration)
- L2 — Dev Eval (minutes, every iteration)
- L3 — Strict Eval (conditional)
- LLM Evaluation Noise Mitigation

## Overview

Evaluation is a pipeline of increasing cost and rigor:

| Layer | Cost | Frequency | What It Catches |
|-------|------|-----------|-----------------|
| L1 Quick Gate | Seconds | Every iteration | Structural breakage, safety violations |
| L2 Dev/Scoreboard Eval | Minutes | Every iteration | Behavioral regressions, pass_rate changes, scalar metric changes |
| L3 Strict Eval | ~10 min | Conditional | Overfitting, holdout failures, A/B quality |

Cheap checks run first. L1 fails → skip L2. L2 shows no improvement → don't trigger L3.

---

## L1 — Quick Gate

Pure programmatic checks. No LLM calls. Target: <5 seconds.

### Checks by Artifact Type

**All types:**
1. Artifact file(s) exist and are non-empty
2. Safety scan: no hardcoded secrets (API keys, passwords, tokens), no dangerous shell commands (recursive force-delete, destructive SQL), no hardcoded absolute paths to system directories

**GT Suite / Hybrid:**
3. Random sample of 3 GT cases — verify each has `id`, `prompt`, and at least 1 assertion

**Scoreboard:**
3. `evolve_plan.md` records metric name, direction, parse rule, run command, timeout, and forbidden scope

**Prompt/Idea/Config:**
4. File is valid text (not binary, not truncated)
5. Character count within reasonable bounds (not empty, not >100k chars without good reason)

**Skill:**
4. SKILL.md has valid YAML frontmatter with `name` and `description`
5. All files referenced in SKILL.md exist

**Code:**
4. Syntax check passes (language-specific: `python -m py_compile`, `node --check`, `go vet`, etc.)
5. No import of removed/renamed modules

Run `scripts/structural_check.py <artifact-path> --type <type>` for the automated checks.

### Decision

- Any critical safety violation → BLOCK (L1 fails, skip L2)
- Structural check fails → BLOCK
- GT Suite / Hybrid GT sample corrupt → BLOCK
- Scoreboard contract missing metric, direction, parse rule, command, timeout, or forbidden scope → BLOCK
- Warnings only → PASS with warnings logged for Phase 2 reference

---

## L2 — Dev / Scoreboard Eval

Run all dev set cases against the current artifact version, or one fixed benchmark run in Scoreboard Mode.

### Execution

For each case or scoreboard run:

1. **Run the artifact** using the execution method:
   - `llm`: Send artifact as system prompt + case prompt as user message. Capture response.
   - `shell`: Run the command with case prompt as input. Capture stdout/stderr.
   - `skill`: Run claude with skill loaded. Capture output.
   - `evaluate`: The artifact IS the output — pass directly to assertions.
   - `scoreboard`: Run the fixed command, capture full output, parse the primary scalar metric.
   - `custom`: Run user-defined command. Capture specified output.
2. **Capture output and trace** — save the full execution log (not just final output) to `traces/iteration-{N}/case-{id}.md`. Include: the input, the execution command, the raw output, timing, and token count.

3. **Evaluate assertions or parse metric**:
   - Programmatic assertion types (`contains`, `regex`, `script`, etc.): use `scripts/evaluate_assertions.py`
   - LLM-judged assertion types (`llm_judge`, `fact_coverage`): prompt an LLM with YES/NO question at temperature 0
   - Scoreboard: parse the primary scalar metric and hard-constraint values from the raw output

4. **Capture timing**: Record wall-clock start/end time and token count or benchmark cost for each execution. Save to the L2 results JSON. These values feed the Cost gate — without them, Dimension 4 cannot function and defaults to PASS, removing a critical safety check.

5. **Compute result**: GT Suite computes per-case pass_rate (`passed_assertions / total_assertions`); Scoreboard records the parsed scalar metric in the configured direction.

### Aggregation

- Per-case: `{id, passed, total, case_pass_rate, failed_assertions}`
- Aggregate: `dev_pass_rate = sum(all_passed) / sum(all_total)` across all cases
- Regressions: compare per-case results with **previous best** iteration (not previous iteration — discarded iterations are skipped)


For Scoreboard Mode, aggregation is a single result object:

```json
{
  "iteration": 5,
  "metric_name": "val_bpb",
  "metric_direction": "minimize",
  "metric_value": 0.9979,
  "previous_best": 1.0012,
  "hard_constraints_passed": true,
  "cost": {"duration_seconds": 325.9, "peak_vram_mb": 45060.2},
  "trace_path": "traces/iteration-5/run.log"
}
```

### Output

For GT Suite, save to `iterations/iteration-{N}/l2_results.json`:

```json
{
  "iteration": 5,
  "dev_pass_rate": 0.86,
  "tokens": 12400,
  "duration_seconds": 91.3,
  "cases": [
    {
      "id": "case-01",
      "passed": 3,
      "total": 4,
      "pass_rate": 0.75,
      "failed_assertions": [{"type": "contains", "value": "retention", "result": "FAIL"}],
      "trace_path": "traces/iteration-5/case-01.md"
    }
  ],
  "regressions": ["case-03"],
  "new_passes": ["case-12"]
}
```

For Scoreboard Mode, save the scalar result object shown above to the same `l2_results.json` path.

---

## L3 — Strict Eval (GT Suite / Hybrid)

Expensive, high-confidence validation. Conditional trigger for case-based evaluation. Scoreboard Mode uses metric re-runs for noisy near-ties instead of L3 holdouts unless the contract defines a regression suite.

### Trigger Conditions

1. **Periodic**: Every N iterations (default N=5, configurable in evolve_plan.md)
2. **Threshold**: Dev pass_rate exceeds target threshold (default 0.9)
3. **Layer promotion**: Before moving from Layer K to Layer K+1

### What L3 Runs

1. **Holdout eval**: Same process as L2, on holdout set. The optimizer has never seen these results.
   - Holdout pass_rate >15% lower than dev → overfitting warning
   - Holdout below baseline → overfitting confirmed, consider reverting recent iterations

2. **Regression eval**: Run all regression cases. Every one must pass. Failures are added to the regression dimension for future gates.

3. **A/B comparison** (optional): Blind-compare current artifact output vs baseline output on 3-5 randomly selected cases using an independent LLM judge.

### Output

Save to `iterations/iteration-{N}/l3_results.json`:

```json
{
  "holdout_pass_rate": 0.82,
  "dev_pass_rate": 0.86,
  "overfitting_gap": 0.04,
  "regression_pass_rate": 1.0,
  "ab_comparison": {"current_wins": 3, "baseline_wins": 1, "ties": 1}
}
```

---

## LLM Evaluation Noise Mitigation

Same artifact, same GT, same LLM — run 4 times and pass_rates may range 0.79–0.92.

### Strategies

1. **Prefer programmatic assertions**: `contains` and `regex` are deterministic. Use wherever possible.
2. **Multiple runs**: For LLM-judged assertions, run 3x and take majority vote (costs 3x more).
3. **Temperature 0**: Always use temperature 0 for LLM-as-judge.
4. **Significance threshold**: Don't count pass_rate changes <2% as meaningful.

The gate's regression check (Dimension 3) is most vulnerable. If exactly 1 case regressed while others improved, run that case 3x before declaring regression.
