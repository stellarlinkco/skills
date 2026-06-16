# Per-Artifact-Type Guide

## Contents
- Prompt Optimization
- Skill Optimization
- Code Optimization
- Idea Optimization
- Config Optimization
- Custom Artifacts

---

## Prompt Optimization

### What You're Evolving
A text prompt (system prompt, few-shot template, instruction set) that drives LLM behavior.

### Execution Method
`llm` — send the prompt as system message + test input as user message. Capture the LLM response.

### GT Design Tips
- Each case is a (user_input, expected_behavior) pair
- Prefer `contains` and `not_contains` for checking key outputs
- Use `llm_judge` for tone, style, and reasoning quality
- Use `fact_coverage` when the prompt should produce specific knowledge points
- Include adversarial inputs: ambiguous queries, off-topic requests, boundary cases

### Mutation Patterns That Work
- **Layer 1:** Rephrase instructions for clarity, reorder few-shot examples, adjust formatting markers
- **Layer 2:** Add/remove constraints, restructure decision logic, add disambiguation rules, change output format
- **Layer 3:** Split into multi-turn chain-of-thought, add retrieval scaffolding, restructure entire prompt architecture

### Common Failure Modes
- **Over-instruction:** Too many rules cause the model to miss or contradict them. Simplify.
- **Example contamination:** Few-shot examples are too similar to test cases → overfitting. Diversify examples.
- **Instruction shadowing:** A later instruction overrides an earlier one. Reorder or consolidate.

---

## Skill Optimization

### What You're Evolving
A SKILL.md file plus optional references/ and scripts/ directories.

### Execution Method
`skill` — run claude with the skill loaded, pass the test prompt, capture output.

### GT Design Tips
- Test both triggering (does the skill activate?) and behavior (does it produce correct output?)
- Use `contains` for checking that outputs reference correct sources
- Use `file_exists` if the skill should produce files
- Use `script` to validate generated code or structured output

### Mutation Patterns That Work
- **Layer 1:** Improve description for better triggering, add trigger phrases
- **Layer 2:** Restructure instructions, add edge case handling, improve decision trees
- **Layer 3:** Add/modify reference files, write helper scripts, add routing indexes

### Common Failure Modes
- **Trigger miss:** Description doesn't match user intent. Fix at Layer 1.
- **Routing error:** Skill sends the model to wrong reference. Fix with disambiguation hints at Layer 2.
- **Reference gaps:** Knowledge not covered. Add reference file at Layer 3.

---

## Code Optimization

### What You're Evolving
Source code — a function, module, script, or codebase component.

### Execution Method
`shell` — run tests, benchmarks, or the code directly with test inputs.

### GT Design Tips
- `script` assertions are your primary tool: `pytest`, `go test`, custom benchmark scripts
- Use `contains`/`not_contains` for output format checks
- Use `regex` for structured output validation
- Include performance benchmarks as assertions: `{"type": "script", "value": "python bench.py --max-time 2.0"}`
- Include edge cases: empty input, large input, concurrent access, error conditions

### Mutation Patterns That Work
- **Layer 1:** Rename variables for clarity, adjust constants, fix formatting, update comments
- **Layer 2:** Rewrite function logic, change algorithm, improve error handling, optimize hot paths
- **Layer 3:** Restructure modules, change interfaces, add helper utilities, refactor architecture

### Common Failure Modes
- **Test-only optimization:** Code passes tests but introduces subtle bugs in untested paths. Expand GT.
- **Performance regression:** Correctness improves but speed degrades. The cost gate catches this.
- **Interface breakage:** Layer 3 change breaks callers. Check integration tests.

---


## Metric / Autoresearch Optimization

### What You're Evolving
One bounded editable surface optimized by a fixed benchmark or training/evaluation harness.

### Execution Method
`scoreboard` — run the fixed command, capture the full log, parse one primary metric with known direction.

### Contract Requirements
- Editable files are explicit
- Evaluation harness and metric extraction are forbidden to edit
- Metric direction is explicit (`minimize` or `maximize`)
- Timeout and hard constraints are recorded
- Baseline run is recorded before mutation

### Mutation Patterns That Work
- **Layer 1:** Constants, hyperparameters, batch sizes, threshold values
- **Layer 2:** Algorithm choices, control flow, optimizer/training loop behavior
- **Layer 3:** Architecture changes inside the editable scope

### Common Failure Modes
- **Oracle hacking:** Editing the metric, benchmark, parser, or data path. This invalidates the run.
- **Noisy tiny deltas:** Re-run near-ties before keeping or discarding.
- **Complexity creep:** A tiny metric gain may not justify a large, opaque change. Prefer equal-or-better simplifications.

---

## Idea Optimization

### What You're Evolving
A document — business plan, design proposal, research hypothesis, strategy document.

### Execution Method
`evaluate` — the artifact IS the output. Assertions evaluate the document directly.

### GT Design Tips
- Heavy on `llm_judge` and `fact_coverage` since ideas are inherently semantic
- `llm_judge` criteria should be specific and measurable:
  - Bad: "Is the idea good?"
  - Good: "Does the proposal identify at least 3 specific risks with mitigation strategies?"
- Use `contains` for required structural elements (section headers, key terms)
- Use `regex` for format requirements (numbered lists, citation format)
- Each "test case" represents an evaluation perspective (investor, engineer, end-user, critic)

### Mutation Patterns That Work
- **Layer 1:** Improve clarity, fix terminology, adjust framing, reorder sections
- **Layer 2:** Strengthen arguments, add evidence, address counterpoints, improve logical flow
- **Layer 3:** Reframe the entire approach, change target audience, restructure around a different thesis

### Common Failure Modes
- **Criteria drift:** LLM-judged assertions are noisy. Use multiple runs and majority vote.
- **Overfitting to evaluator:** Artifact satisfies the LLM judge but not human readers. Run L3 with holdout perspectives.
- **Circular improvement:** Each iteration adds more content without improving substance. Apply the Simplify priority.
- **Assertion-gaming (thin passes):** Adding the minimum content to flip an assertion (e.g., one dollar figure to pass "includes market data") without genuine depth. Each mutation should add substantive, professionally credible content. Think "would this convince the target audience?" not "does this pass the check?"

---

## Config Optimization

### What You're Evolving
Configuration files (YAML, JSON, TOML, .env, etc.) that control system behavior.

### Execution Method
`shell` — apply the config to the system, run it, check behavior.

### GT Design Tips
- `script` assertions that start the system and verify behavior
- `contains` / `not_contains` for log output checks
- `json_valid` or equivalent format validation

### Mutation Patterns That Work
- **Layer 1:** Adjust individual values (timeouts, thresholds, feature flags)
- **Layer 2:** Restructure sections, add/remove config blocks
- **Layer 3:** Change config schema, migrate format, add dependency configs

---

## Custom Artifacts

For anything not covered above:

1. Define the execution method in the GT file's `default_execution` field
2. Map the three mutation layers to your artifact's structure (surface → core → architecture)
3. Document the mapping in evolve_plan.md so the loop knows what's allowed at each layer
4. Assertions follow the same 8 types — pick what fits
