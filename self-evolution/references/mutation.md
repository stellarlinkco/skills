# Layered Mutation Strategy

## Contents
- Why Layers
- Three Layers (universal definition + per-artifact-type mapping)
- Cross-Layer Rules
- Priority Ladder
- Evidence-Based Mutation Protocol

## Why Layers

Not all mutations are equal. Changing a keyword is cheap and low-risk. Restructuring architecture is expensive and high-risk. Start with the cheapest changes, escalate only when cheaper options are exhausted.

Analogous to learning rate schedules — large cheap adjustments first, then expensive fine-tuning.

## Three Layers

### Layer 1 — Surface

The cheapest, lowest-risk changes. Metadata, naming, formatting, shallow content.

| Artifact Type | What You CAN Change | What You CANNOT Change |
|--------------|--------------------|-----------------------|
| Prompt | Phrasing, keyword choices, formatting, examples order | Core instructions, logic flow |
| Skill | Frontmatter description, trigger keywords, first section | SKILL.md body, references, scripts |
| Code | Variable names, constants, config values, comments, formatting | Function logic, algorithms, architecture |
| Idea | Title, framing, word choice, section order | Arguments, evidence, conclusions |
| Config | Individual values, feature flags | Structure, key names, dependencies |
| Experiment | Run tag, description, metric parser wording, hyperparameters/constants | Benchmark harness, metric direction, forbidden scope |

**When exhausted:** K consecutive discards (default K=3). Surface quality is already good — problems lie deeper.

### Layer 2 — Core Content

The primary logic and substance. Medium cost, medium risk.

| Artifact Type | What You CAN Change | What You CANNOT Change |
|--------------|--------------------|-----------------------|
| Prompt | Instructions, decision logic, examples, constraints, output format | External references, helper scripts |
| Skill | SKILL.md instruction body, decision trees, routing, format specs | Reference files, scripts |
| Code | Function implementations, algorithm logic, control flow, error handling | Module boundaries, public interfaces, external dependencies |
| Idea | Arguments, evidence, logical structure, supporting data | Fundamental premise (unless explicitly allowed) |
| Config | Structural reorganization, adding/removing sections | External schema requirements |
| Experiment | Algorithm choices, training loop behavior, optimizer/scheduler logic inside editable scope | Evaluation harness, data path, metric parser, dependencies |

**When exhausted:** K consecutive discards. Core is solid — problems are in supporting infrastructure.

### Layer 3 — Architecture

The most expensive, highest-risk changes. Supporting materials, structure, dependencies.

| Artifact Type | What You CAN Change | Everything |
|--------------|--------------------|-|
| Prompt | Split into sub-prompts, add chain-of-thought scaffolding, restructure entirely | |
| Skill | Reference files, scripts, add new supporting files | |
| Code | Module structure, interfaces, dependencies, add helper modules | |
| Idea | Fundamental framing, target audience, core premise | |
| Config | Schema changes, migration to different format | |
| Experiment | Architecture changes inside editable scope, helper modules allowed by contract | |

**When exhausted:** Evolution is complete. All layers have been tried.

## Cross-Layer Rules

1. **Start at Layer 1, progress sequentially.** Can override starting layer in evolve_plan.md when baseline analysis shows a layer is irrelevant. Once chosen, exhaust current layer before promoting.
2. **Never cross layers in one iteration.** If at Layer 2, don't also change architecture. Split into two iterations.
3. **Layer promotion requires L3 evaluation.** Checkpoint holdout performance before moving up.
4. **Layer demotion is allowed.** If at Layer 3 you realize a Layer 1 fix would help, drop back — but stay within the demoted layer's scope.

## Priority Ladder

Regardless of layer, follow this order for choosing WHAT to change:

### Priority 1 — Fix Crashes
Cases that error out instead of producing output. A crash yields zero diagnostic information.

### Priority 2 — Exploit Success Patterns
If mutation type X worked on case A, try the same pattern on case B. Disambiguation hints that fixed case-12 may fix case-17 too.

### Priority 3 — Attack Persistent Failures
Cases failing 3+ consecutive iterations. Review their traces carefully — the pattern of failure often reveals a systematic issue.

### Priority 4 — Explore New Directions
Try a mutation type not yet attempted. Prevents getting stuck in a local optimum.

### Priority 5 — Simplify
Remove content that isn't contributing. Shorter artifacts often perform better — less instruction means less confusion. Check if removing a section maintains pass_rate.

### Priority 6 — Aggressive Mutation
Only after 5+ consecutive discards. Restructure a section, change the approach, try a fundamentally different strategy. High risk, necessary when incremental changes stall.

## Evidence-Based Mutation Protocol

Every mutation proposal MUST include:

1. **Target case(s):** Which specific cases this mutation aims to fix
2. **Trace evidence:** Specific content from the trace showing WHY the case failed
3. **Counterfactual:** "If I change X, the output should change from Y to Z"
4. **Risk assessment:** Which currently-passing cases might be affected

This prevents "vibe-based" mutations — changes made because they "feel right" rather than because evidence supports them.

The trace is the diagnostic tool. Don't summarize — read the raw trace. The difference between correct and incorrect behavior is often one sentence, one condition, one example.
