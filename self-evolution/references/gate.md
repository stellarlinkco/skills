# 5-Dimension AND Gate

## Contents
- Why AND, Not Weighted Sum
- The 5 Dimensions
- Gate Decision Matrix
- Edge Cases
- Logging Gate Decisions

## Why AND, Not Weighted Sum

Weighted scoring lets a large gain in one dimension compensate for a loss in another:

- Quality up 10% but token cost 3x → weighted sum might PASS
- pass_rate up 5% but 2 regressions → weighted sum might PASS
- Safety warning appeared but pass_rate improved → weighted sum might PASS

AND logic prevents all of these. Every dimension must independently pass. No compensation across dimensions.

## The 5 Dimensions

### Dimension 1 — Structure

**Question:** Did L1 Quick Gate pass?

**PASS:** All structural checks pass, no critical safety violations.
**FAIL:** Any L1 critical check failed.

The cheapest gate — if the artifact is structurally broken, nothing else matters.

### Dimension 2 — Progress

**Question:** Did the artifact get at least as good as the previous best?

**GT Suite / Hybrid PASS:** `current_pass_rate >= previous_best_pass_rate`
**Scoreboard PASS:** primary scalar metric is better than the previous best in the configured direction, or tied while the artifact is simpler or cheaper.
**FAIL:** quality is worse than previous best, or the scalar metric moves in the wrong direction.

"Previous best" means the best kept iteration, not the immediately previous one (discarded iterations are skipped).

Ties are acceptable only when they buy simplification, lower cost, or another explicitly recorded benefit. A tie that only adds complexity is a discard.

### Dimension 3 — Regression

**Question:** Did any previously-passing case start failing?

**PASS:** No case went from PASS to FAIL.
**FAIL:** Any case regressed.

**Noise handling:** If exactly 1 case regressed while multiple others improved, run the regressed case 3x before declaring regression. If 2 of 3 runs pass → LLM noise, count as PASS. If 2 of 3 fail → real regression, count as FAIL.

### Dimension 4 — Cost

**Question:** Is resource cost acceptable?

**PASS:** Both token count and execution time within 2x of baseline per-case averages.
**FAIL:** Either exceeds 2x baseline.

The 2x threshold is the default (configurable in evolve_plan.md). For optimization-focused evolutions where cost IS the goal, tighten this.

Cost is per-case average, not total — if more cases pass, total cost naturally increases, and that's fine.

### Dimension 5 — Safety

**Question:** Are all safety rules satisfied?

**PASS:** Zero critical violations AND warning count did not increase from previous iteration.
**FAIL:** Any new critical violation, OR warning count increased.

Pre-existing warnings don't cause failure — only NEW warnings do.

## Gate Decision Matrix

```
All dimensions PASS → KEEP (changes stay, update "previous best")
Any dimension FAIL → DISCARD (revert/reset to previous best, log failure reason)
```

No "partial keep" or "keep with warning." Binary decision. Scoreboard Mode uses the same binary gate, but Dimension 2 compares the configured scalar metric instead of pass_rate.

## Edge Cases

**First iteration after baseline:** Previous best = baseline. No regression possible. Dimension 3 auto-passes.

**Tie on progress:** PASS only when the mutation simplifies the artifact, lowers soft cost, or delivers another explicitly recorded benefit. Otherwise discard ties to prevent complexity creep.

**L3 results and the gate:** L3 results inform future Phase 2 decisions but do NOT retroactively discard kept iterations. The gate operates on L1 and L2 only. Exception: if L3 regression set shows failures, those cases join the regression dimension for future iterations.

**Multiple consecutive discards:** After K consecutive discards at the same layer (K from evolve_plan.md, default 3), the layer is exhausted. Promote to next layer.

## Logging Gate Decisions

Every gate decision goes to experiments.jsonl:

```json
{
  "gate_details": {
    "structure": true,
    "progress": true,
    "regression": true,
    "cost": true,
    "safety": true,
    "decision": "KEEP",
    "failure_reasons": []
  }
}
```

For DISCARD decisions:

```json
{
  "failure_reasons": [
    "regression: case-03 PASS→FAIL (assertion 'contains: retention' no longer matches)"
  ]
}
```
