---
name: self-evolution
description: >
  Iteratively evolve any measurable artifact (prompt, skill, code, idea, configuration,
  document, benchmarked experiment) through autonomous mutation-evaluate-gate loops.
  Supports both GT case suites and autoresearch-style scalar metric loops where a fixed
  command prints one score. Uses 8-phase iteration, 3-layer evaluation, deterministic
  keep/discard gates, trace-driven diagnosis, and layered mutation. Trigger on "evolve
  this", "optimize iteratively", "self-improve", "train this prompt", "iterate on this
  code", "make this better through iteration", "run evolution loop", "self-evolution",
  "evolve this skill", "train this skill", "optimize skill quality", "autonomous
  research", "autoresearch", or whenever the user has a measurable artifact that needs
  data-driven improvement with automatic keep/revert decisions.
---

# Evolve

You are the evolution controller. The user provides an artifact and a definition of "good" — either Ground Truth (GT) cases or a scalar metric. You drive the loop: mutate, evaluate, gate, keep or revert, repeat.

**Core principle:** Any artifact that can be evaluated can be trained. You need three things:
1. **Artifact** — the thing being improved (a prompt, a skill, code, an idea document, a config, an experiment)
2. **Oracle** — GT cases or a scalar metric that defines what "better" means
3. **Execution method** — how to produce output or a score from the artifact for evaluation

## Operating Modes

Choose the lightest loop that still has a real oracle:

1. **GT Suite Mode** — Use when quality is defined by multiple test cases or assertions. This is the default for prompts, skills, documents, configs, and broad behavior.
2. **Scoreboard Mode** — Use when a fixed command or harness prints one primary metric (accuracy, loss, val_bpb, latency, score). This is the autoresearch pattern: mutate one bounded surface, run the benchmark, keep only metric-improving changes, repeat.
3. **Hybrid Mode** — Use when a scalar metric is primary but regressions matter. Gate on the primary metric, plus a small regression suite for safety or correctness.

Do not force GT case generation when the user already has a fixed executable metric. A scalar metric with direction, command, editable scope, and hard constraints is enough to start.

## Prerequisites

Before starting, verify:
1. The artifact exists and is identifiable (a file, a directory, or a clearly scoped text block)
2. An oracle exists:
   - GT test cases exist or will be generated (see `references/ground-truth.md`), OR
   - a scalar metric command exists with metric name, direction (`minimize` or `maximize`), and parse rule
3. The editable scope and forbidden scope are explicit
4. The artifact's parent directory is under git (or you will init it)
5. An execution method is clear for the artifact type (see `references/artifact-guide.md`)

If neither GT nor scalar metric exists, help the user create one. Analyze the artifact, propose 10-15 test cases with assertions or one benchmark command with metric extraction, and ask for review.

**For skills specifically:** If `skill-creator` is installed, use `quick_validate.py` for L1 validation and skill-creator's grader for L2 evaluation. See `references/artifact-guide.md` for skill-specific execution methods.

---

## Phase 0 — Setup (One-Time)

### 0.1 Classify the Artifact

Determine the artifact type and run mode. This drives execution method and mutation layer definitions.

| Type | Artifact Is | Execution Method | Default Mode | Example |
|------|------------|------------------|--------------|---------|
| `prompt` | A text prompt/instruction | Send to LLM with test input, capture output | GT Suite | System prompt, few-shot template |
| `skill` | SKILL.md + references/scripts | Run claude with skill loaded | GT Suite | Claude Code skill |
| `code` | Source code files | Run/test via shell command | GT Suite or Scoreboard | Python function, JS module |
| `experiment` | Bounded code/config optimized by one benchmark | Run fixed command, parse scalar metric | Scoreboard | autoresearch `train.py` |
| `idea` | A document/proposal | LLM evaluates against criteria | GT Suite | Business plan, design doc |
| `config` | Configuration file | Apply config, run system, check behavior | GT Suite or Scoreboard | YAML config, .env settings |
| `custom` | User-defined | User provides execution command | GT Suite, Scoreboard, or Hybrid | Anything else |

If the artifact or oracle is ambiguous, ask the user. If only the run mode is ambiguous, prefer GT Suite for semantic quality and Scoreboard for numeric optimization.

### 0.2 Define the Oracle and Scope Contract

Record the contract before the first mutation:

- **Editable scope:** exact file(s), directories, or text blocks the loop may change
- **Forbidden scope:** files, harnesses, generated outputs, dependencies, external services, or contracts that must not change
- **Oracle command:** the command, API call, evaluation procedure, or LLM grading method that produces the result
- **Metric:** pass_rate for GT Suite, or scalar metric name + direction for Scoreboard
- **Budget:** timeout, token/time ceiling, memory ceiling, or "none" if not relevant
- **Keep rule:** what counts as progress
- **Discard rule:** crashes, regressions, worse metrics, safety failures, or constraint violations

The oracle is the source of truth. Do not edit the oracle to make a mutation pass.

### 0.3 Workspace Initialization

Create workspace as a sibling to the artifact:

```
<artifact-name>-evolution/
├── evolve_plan.md          # Strategy document
├── results.tsv             # Per-iteration summary (append-only)
├── experiments.jsonl        # Structured experiment log (append-only)
├── gt/                     # GT Suite / Hybrid only
│   ├── dev.json
│   ├── holdout.json
│   └── regression.json
├── traces/                 # Per-iteration execution traces
└── iterations/             # Per-iteration snapshots and result JSON
```

For Scoreboard Mode, `results.tsv` must at minimum include:

```
iteration	commit	metric_name	metric_value	cost	status	description
```

Use tab-separated rows. Keep run logs and raw outputs in `traces/iteration-{N}/`.

### 0.4 Git State Check

- Clean git repo: proceed
- Dirty repo: ask user to commit or stash unless the dirty files are the explicit artifact under evolution
- No git init: run `git init && git add -A && git commit -m "pre-evolution baseline"`
- No git: tell user to install git

For Scoreboard Mode, create or reuse a dedicated experiment branch/tag when the repository workflow allows it. This keeps discarded experiments cheap to revert and makes the result ledger auditable.

### 0.5 GT or Scoreboard Preparation

For GT Suite / Hybrid:
- If the user provides a single GT file, split it:
  - **Dev (70%)**: Used every iteration for L2 evaluation
  - **Holdout (20%)**: Never shown to the proposer; used only in L3
  - **Regression (10%)**: Cases that already pass; guards against regression
- If fewer than 10 total cases, skip holdout. Read `references/ground-truth.md` for the full GT format and assertion types.

For Scoreboard:
- Write the metric extractor before mutation begins.
- Establish metric direction (`minimize` or `maximize`) and any minimum meaningful delta.
- Record hard constraints separately from soft costs. Example: "must finish under 10 minutes" is hard; "VRAM should not grow much" is soft.

### 0.6 Baseline Run

Run the current artifact state through the oracle. This is iteration 0.

- GT Suite: run L2 evaluation on the full dev set. Save traces to `traces/iteration-0/`, results to `iterations/iteration-0/l2_results.json`.
- Scoreboard: run the fixed command unchanged, parse the metric, save the raw log to `traces/iteration-0/`, and append the baseline row to `results.tsv`.

### 0.7 Generate Evolution Plan

Analyze the artifact, oracle, scope, and baseline results. Write `evolve_plan.md`:
- Artifact type and run mode
- Editable and forbidden scope
- Execution method and metric extraction
- Current baseline metric
- Target metric or stopping condition (user-specified or inferred)
- Starting mutation layer (default: Layer 1 unless Scoreboard scope already invites deeper changes)
- Gate thresholds and hard constraints
- L3 trigger conditions for GT Suite / Hybrid

Ask only if contract choices remain ambiguous. If the user already supplied a fixed metric command and editable scope, record the plan and start the loop.

---

## Iteration Loop

Use the loop shape that matches the selected operating mode.

**GT Suite / Hybrid checklist:**

```
Iteration {N}:
- [ ] Phase 1: Review — read memory + traces
- [ ] Phase 2: Ideate — propose ONE atomic change with trace evidence
- [ ] Phase 3: Modify — execute the change
- [ ] Phase 4: Commit — git commit (before verify)
- [ ] Phase 5: Verify — L1 → L2 (→ L3 if triggered)
- [ ] Phase 6: Gate — deterministic AND gate → KEEP or DISCARD
- [ ] Phase 7: Log — results.tsv + experiments.jsonl + traces
- [ ] Phase 8: Loop — continue / promote / stop
```

For Scoreboard Mode, use the lean autoresearch loop in the dedicated section below. It keeps the same invariants: one mutation, one run, one ledger entry, deterministic keep/discard.

### Phase 1 — Review

Read the evolution memory:
1. Last 20 lines of `results.tsv`
2. Last 10 entries from `experiments.jsonl`
3. Last 20 git log entries in the artifact directory
4. Failed cases from previous iteration traces (skip on first iteration)

Extract 5 signals:
1. Which mutation patterns succeeded — exploit them
2. Which mutation patterns failed — avoid repeating
3. Which cases persistently fail — prioritize them
4. Which cases are fragile (flipped recently) — treat as regression guards
5. Whether you're stuck (3+ consecutive discards) — escalate strategy

### Phase 2 — Ideate

Propose ONE atomic change. Follow the priority ladder:

1. **Fix crashes** — cases that error out
2. **Exploit success patterns** — apply a proven mutation type to new failing cases
3. **Attack persistent failures** — cases failing 3+ consecutive iterations
4. **Explore new directions** — try an untested approach
5. **Simplify** — remove content that isn't contributing
6. **Aggressive mutation** — restructure (only after 5+ consecutive discards)

**Hard rule: evidence before action.** Cite specific trace evidence:

> "Case {id} failed because {observed behavior}. Trace at {path} shows {evidence}. If I change {X}, the output should change from {current} to {expected}."

No trace citation, no mutation allowed. On the first iteration, cite baseline L2 results as evidence.

**Atomicity test:** If describing the change requires the word "and", split into two iterations.

**Depth over assertion-gaming.** When the artifact is a document or idea, passing GT assertions is necessary but not sufficient. Each mutation should make the artifact genuinely stronger, not just add the minimum content to flip an assertion from FAIL to PASS. If a case expects "market data with dollar figures," add real analysis — not a single throwaway number. The GT is a lower bound on quality, not the target.

**When all cases already pass:** If dev pass_rate is 1.0, shift priority to Simplify (Priority 5). Look for instructions, code, or content that can be removed without dropping pass_rate. Shorter, cleaner artifacts are better than padded ones. Do not waste iterations on cosmetic changes that add no behavioral value.

Read `references/mutation.md` for layer rules and per-artifact mutation guidance.

### Phase 3 — Modify

Execute the proposed change:
- Stay within the current mutation layer
- Touch only files relevant to the change
- After modifying, `git diff --stat` — if >5 files changed, probably not atomic

### Phase 4 — Commit

Commit BEFORE verifying. This preserves the audit trail even for failed mutations.

```bash
git add <artifact-files> && git commit -m "evolve: iteration-{N} — {one-line description}"
```

Only stage artifact files. Never `git add -A` — workspace artifacts must not be committed.

### Phase 5 — Verify

Run the 3-layer evaluation pipeline. Read `references/evaluation.md` for details.

**L1 Quick Gate (every iteration):**
- Structural validity check for the artifact type
- Safety scan (no secrets, no dangerous operations)
- 3 random GT cases structural check
- L1 fails → skip L2, go to Phase 6 with DISCARD

**L2 Dev Eval (every iteration):**
- Run all dev GT cases through the artifact using the execution method
- Record per-case pass/fail with evidence
- Save traces to `traces/iteration-{N}/`
- Calculate aggregate pass_rate
- **Capture timing:** Record wall-clock duration and token count for each case. These feed the Cost gate (Dimension 4). Without timing data, the Cost gate cannot function — record actual measurements, not zeros.

**L3 Strict Eval (conditional):**
Triggered when: every N iterations / dev pass_rate exceeds threshold / before layer promotion.
Runs holdout set + regression set. Detects overfitting.

### Phase 6 — Gate

Apply the 5-dimension AND gate. ALL must pass — any NO triggers `git revert HEAD`.

| Dim | Question | Check |
|-----|----------|-------|
| Structure | Did L1 pass? | L1 result |
| Progress | pass_rate >= previous best? | Compare results.tsv |
| Regression | No previously-passing case now fails? | Diff per-case results |
| Cost | Token/time within 2x baseline? | Timing data |
| Safety | No new safety violations? | L1 safety scan |

Read `references/gate.md` for edge cases and noise handling.

### Phase 7 — Log

Append to `results.tsv`:
```
iteration  layer  mutation_type  description  pass_rate  delta  decision  tokens  duration_s  timestamp
```

Append to `experiments.jsonl`:
```json
{
  "iteration": 5,
  "artifact_type": "prompt",
  "layer": 2,
  "mutation": "Added disambiguation hint for ambiguous queries",
  "target_cases": ["case-12"],
  "pass_rate_before": 0.82,
  "pass_rate_after": 0.86,
  "regressions": [],
  "decision": "KEEP",
  "gate_details": {"structure": true, "progress": true, "regression": true, "cost": true, "safety": true}
}
```

Save per-case traces to `traces/iteration-{N}/case-{id}.md`.

### Phase 8 — Loop Decision

Three outcomes:
1. **Continue** — more cases to fix at current layer
2. **Layer promotion** — K consecutive discards at this layer → promote. Run L3 before promoting.
3. **Stop** — all layers exhausted / target reached / max iterations hit

On stop, generate a final evolution report:
- Starting vs ending pass_rate (dev + holdout)
- Total iterations (kept vs discarded)
- Per-layer breakdown
- Unfixable cases (candidates for GT review)
- Recommended next steps

---

## Scoreboard Mode — Autoresearch-Style Loop

Use this mode when the oracle is one scalar metric from a fixed command. The model is not optimizing a checklist; it is doing experimental research under a bounded benchmark.

### Scoreboard Contract

Before iteration 1, write this contract in `evolve_plan.md`:

```
editable_scope:
forbidden_scope:
run_command:
metric_name:
metric_direction: minimize|maximize
metric_parse_rule:
timeout_seconds:
hard_constraints:
soft_costs:
keep_rule:
discard_rule:
```

The reference pattern is `references/autoresearch/program.md`: a tiny repo, one editable file, one fixed evaluation function, one primary metric, and a ledger of experiments.

### Lean Loop

Repeat until the user stops you, the target is reached, or the configured iteration limit is exhausted:

1. **Review** — Read `results.tsv`, `experiments.jsonl`, the current diff, and the latest trace. Identify the current best metric and recent failed ideas.
2. **Choose one hypothesis** — Change exactly one concept. The idea may be shallow or deep if the editable scope allows it, but the experiment must still be explainable in one sentence.
3. **Modify only editable scope** — Never touch the metric extractor, benchmark harness, forbidden files, dependencies, or external setup unless the contract explicitly allows it.
4. **Commit the mutation** — Commit before the run so a bad experiment has a precise rollback point.
5. **Run the oracle** — Execute the fixed command with the configured timeout. Capture the full raw output in the trace. Do not summarize logs into the prompt; preserve them for diagnosis.
6. **Parse the metric** — Extract the primary metric and hard-constraint values using the recorded parse rule.
7. **Gate**:
   - Crash, timeout, parse failure, or hard-constraint violation → `crash`/`discard`
   - Worse primary metric → `discard`
   - Equal primary metric with simpler artifact or lower soft cost → `keep`
   - Better primary metric within hard constraints → `keep`
8. **Apply decision**:
   - KEEP: leave the commit in history and mark it as the new best
   - DISCARD/CRASH: revert/reset to the previous best state, then continue
9. **Log** — Append `results.tsv` and `experiments.jsonl` with commit, metric, cost, status, and short description.

### When Stuck

If several consecutive experiments fail:
- Re-read the best and worst traces for hidden constraints
- Try combining two previous near-misses only if the combined hypothesis is still one concept
- Prefer simplification experiments: delete complexity and keep if the metric ties or improves
- Escalate mutation layer only after the cheaper layer stops producing gains
- If the metric appears noisy, re-run the current best and candidate once before discarding a tiny delta

Do not pause between successful experiments just to ask whether to continue. The user can redirect, stop, or adjust the contract at any time.

---

## Human Intervention

The loop runs autonomously, but the user can intervene at any time:

- **Redirect**: "Focus on case X" → next Phase 2 prioritizes it
- **Inject**: "Try restructuring the routing logic" → next Phase 3 applies it
- **Adjust**: "Relax the cost constraint" → update evolve_plan.md
- **Pause**: "Stop after this iteration" → complete current iteration, stop
- **Mark unfixable**: "Case X has bad GT" → exclude from all evaluation sets

---

## Reference Files

Read these when entering the relevant phase:
- `references/ground-truth.md` — GT case format, 8 assertion types, split strategy, generation
- `references/evaluation.md` — 3-layer evaluation pipeline, scoreboard execution, noise mitigation
- `references/gate.md` — 5-dimension AND gate, scalar metric edge cases, logging
- `references/mutation.md` — Layered mutation strategy, priority ladder, evidence protocol
- `references/artifact-guide.md` — Per-artifact-type guidance, including metric/autoresearch optimization
- `references/autoresearch/program.md` — Minimal reference pattern for fixed-metric autonomous research loops

## Scripts

Run these directly — do not load source into context:
- `scripts/evaluate_assertions.py --output-file <path> --expectations '<json>'` — Evaluate programmatic assertions
- `scripts/results_tracker.py <workspace> log --iteration N --layer L ...` — Append GT Suite results to results.tsv + experiments.jsonl
- `scripts/results_tracker.py <workspace> init --mode scoreboard` — Initialize a Scoreboard workspace
- `scripts/results_tracker.py <workspace> log --mode scoreboard --iteration N --layer L --mutation-type <type> --description <text> --metric-name <name> --metric-value <value> --metric-direction minimize|maximize --delta <delta> --decision BASELINE|KEEP|DISCARD` — Append scalar metric results
- `scripts/structural_check.py <artifact-path> --type <artifact-type>` — L1 structural validator

Run the experiment-mode validator when evolving fixed-metric benchmark artifacts:

```bash
scripts/structural_check.py <artifact-path> --type experiment --language <language> --plan-path <evolve_plan.md>
```

## Key Constraints

- **Git is the safety net.** Every mutation is committed before verification. Reverts are clean.
- **Program controls flow, LLM generates content.** The gate is deterministic — no "maybe keep" decisions. KEEP or DISCARD, binary.
- **Traces are the diagnostic brain.** Never summarize traces for the proposer — point to the file path and let it read the raw evidence.
- **GT quality = ceiling in GT Suite Mode.** If a case fails 5+ consecutive iterations, suspect the GT before the artifact.
- **Metric integrity = ceiling in Scoreboard Mode.** If the parser, benchmark, or data can be edited, the loop can cheat; freeze them in forbidden scope.
- **First 3-5 iterations benefit from human oversight.** After memory accumulates, the loop runs more accurately.
