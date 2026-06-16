# Repository Guidelines

## Project Overview

This repository packages Stellarlink agent skills for work that needs more control than a single prompt. It currently ships three skills through `.claude-plugin/plugin.json`:

- `skills/harness` — long-running, multi-session task execution with Codex hooks and durable progress files.
- `skills/code-review` — high-recall review protocol for PRs, branch diffs, and working-tree diffs.
- `skills/self-evolution` — measurable mutation/evaluate/gate loops for prompts, skills, code, configs, and benchmarked experiments.

The repo is a skills package, not an application runtime. Most behavior is Markdown protocol plus Python helper scripts.

## Architecture & Data Flow

- Packaging starts at `.claude-plugin/plugin.json`. Its `skills` array is the package surface; add new shipped skills there and update `README.md` in the same change.
- Root `README.md` is the public install/orientation page. Keep links under `./skills/...` and keep the logo asset path `./assets/stellarlink-logo.svg` valid.
- Each skill is self-contained under `skills/<skill-name>/`. `SKILL.md` is the agent-facing entrypoint: YAML frontmatter for routing/metadata, Markdown body for the executable protocol.
- `skills/code-review` is pure protocol: gather diff/context → generate candidates from independent angles → verify → final gap sweep → capped JSON findings.
- `skills/self-evolution` routes from `SKILL.md` into `references/` and `scripts/`: artifact + oracle → L1 structural/safety check → L2 dev/scoreboard eval → optional L3 holdout/regression → binary KEEP/DISCARD gate → ledgers/traces.
- `skills/harness` is stateful at runtime. Codex invokes Python hooks; hooks discover a target project state root, read `harness-tasks.json` and `harness-progress.txt`, check `.harness-active`, then inject context, block stop/idle, or update task state.
- Harness concurrency uses `/tmp/harness-<root-hash>.lock`, `HARNESS_STATE_ROOT`, `HARNESS_WORKER_ID`, leases, and separate git worktrees/clones. Preserve those invariants when editing hook code.

## Key Directories

- `.claude-plugin/` — Claude plugin metadata. `plugin.json` lists shipped skill directories.
- `assets/` — static README assets. Currently `assets/stellarlink-logo.svg`.
- `skills/code-review/` — single-file review skill (`SKILL.md`).
- `skills/harness/` — long-running agent framework. Contains `SKILL.md`, Chinese install/ops guide `README.md`, and Python hook/helper scripts.
- `skills/harness/hooks/` — source for Codex lifecycle hooks and CLI helpers. Treat `.py` files as source; treat `__pycache__/` and `.pyc` files as generated cache.
- `skills/self-evolution/` — evolution controller skill.
- `skills/self-evolution/references/` — phase-specific docs for artifact types, evaluation, gate rules, GT formats, and mutation strategy.
- `skills/self-evolution/scripts/` — Python helper tools for assertions, structural checks, and result tracking.

## Development Commands

There is no discovered repo-wide build, lint, test, package-manager, Makefile, justfile, or CI command. Validate changes with the narrowest concrete check for the touched surface.

Useful commands documented by the repo:

```bash
# Install this collection via skills.sh
npx skills@latest add stellarlinkco/skills

# Harness install smoke check after copying the skill into ~/.codex/skills
python3 ~/.codex/skills/harness/hooks/harness-stop.py <<< '{}'
```

Skill support commands:

```bash
# Self-evolution structural/safety validation
python3 skills/self-evolution/scripts/structural_check.py <artifact-path> --type <prompt|skill|code|experiment|idea|config|custom>

# Fixed-metric experiment plan validation
python3 skills/self-evolution/scripts/structural_check.py <artifact-path> --type experiment --language <language> --plan-path <evolve_plan.md>

# Programmatic assertion evaluation
python3 skills/self-evolution/scripts/evaluate_assertions.py --output-file <path> --expectations '<json>'

# Evolution ledger helpers
python3 skills/self-evolution/scripts/results_tracker.py <workspace> init --mode scoreboard
python3 skills/self-evolution/scripts/results_tracker.py <workspace> summary
python3 skills/self-evolution/scripts/results_tracker.py <workspace> best
```

Harness user-facing commands are protocol commands, not repo maintenance commands:

```text
/harness init <project-path>
/harness run
/harness status
/harness add "task description"
```

## Code Conventions & Common Patterns

- Keep `SKILL.md` as the primary protocol surface. Add supporting docs/scripts only when the skill explains when and why to use them.
- Frontmatter matters. Preserve `name`, `version`, and especially `description`; description text is routing/trigger surface, not decorative copy.
- Use path-stable support files. If `SKILL.md` references a file in `references/`, `scripts/`, or `hooks/`, update references and files together.
- Prefer existing protocol shapes: phases, gates, checklists, explicit output formats, and concrete commands. Do not add a second convention beside an existing one.
- Verification belongs in the skill. A skill that changes behavior should tell the agent how to prove success.
- Do not hide behavior in scripts. Runtime behavior in `scripts/` or `hooks/` must be reflected in `SKILL.md` or adjacent docs.
- Harness state writes must stay atomic: write `.bak`, write `.tmp`, then replace. Preserve `.harness-active` as the master guard; hooks should no-op when inactive.
- Harness logs are single-line and grep-friendly: ISO timestamp, `SESSION-N`, type, optional task/category, message. `harness-progress.txt` is append-only.
- Harness tasks require a non-empty `validation.command`; missing validation is a CONFIG error, not a completed task.
- Self-evolution keeps the oracle sacred. Do not edit the oracle, benchmark harness, metric parser, forbidden scope, or eval data to make a mutation pass.
- Self-evolution uses one atomic mutation per iteration and a binary KEEP/DISCARD gate. No partial keep.
- Code-review optimizes recall first. Do not apply fixes or post comments unless the user asks for fix/comment mode.

## Important Files

- `README.md` — public package overview, install command, skill list, and repo design notes.
- `.claude-plugin/plugin.json` — plugin package manifest. Current manifest paths: `./skills/harness`, `./skills/code-review`, `./skills/self-evolution`.
- `assets/stellarlink-logo.svg` — README logo asset.
- `skills/harness/SKILL.md` — harness protocol and hook frontmatter.
- `skills/harness/README.md` — harness installation, `~/.codex/config.toml` hook setup, env vars, failure recovery, and uninstall notes.
- `skills/harness/hooks/_harness_common.py` — shared state discovery, JSON I/O, locking, task eligibility, lease, and hook-output helpers.
- `skills/harness/hooks/harness-stop.py` — stop blocker and completion/reflection handoff.
- `skills/harness/hooks/harness-sessionstart.py` — active harness context injection.
- `skills/harness/hooks/harness-claim.py` and `skills/harness/hooks/harness-renew.py` — concurrent-mode claim/lease helpers.
- `skills/code-review/SKILL.md` — review protocol and JSON output contract.
- `skills/self-evolution/SKILL.md` — evolution controller protocol, workspace layout, loop phases, and script routing.
- `skills/self-evolution/references/evaluation.md` — L1/L2/L3 evaluation contract.
- `skills/self-evolution/references/gate.md` — five-dimension KEEP/DISCARD gate.
- `skills/self-evolution/references/ground-truth.md` — universal GT case schema.
- `skills/self-evolution/references/gt-format.md` — skill-creator-compatible eval format; different from `ground-truth.md`.
- `skills/self-evolution/scripts/structural_check.py` — structural/safety validator.
- `skills/self-evolution/scripts/evaluate_assertions.py` — deterministic assertion evaluator.
- `skills/self-evolution/scripts/results_tracker.py` — evolution ledger helper.

## Runtime/Tooling Preferences

- Python scripts target Python 3.10+ and use the standard library. Do not add dependencies without a clear maintenance reason.
- Harness runtime assumes Codex CLI, Codex hook payloads, Python 3.10+, and Git in the target project.
- This repository is installed with `npx skills@latest add stellarlinkco/skills`, but no Node package metadata is present. Do not assume `npm install`, `npm test`, or Node-based tooling exists here.
- Harness hook paths in `SKILL.md` and `skills/harness/README.md` point to `$HOME/.codex/skills/harness/hooks/...`; update docs and frontmatter together if paths move.
- Generated runtime artifacts do not belong in normal repo edits unless intentionally documented as fixtures: `harness-tasks.json`, `harness-progress.txt`, `.harness-active`, `.harness-reflect`, `.harness-stop-counter`, `harness-tasks.json.bak`, `harness-tasks.json.tmp`, evolution `results.tsv`, `experiments.jsonl`, `traces/`, `iterations/`, `gt/`, `.DS_Store`, and `__pycache__/`.

## Testing & QA

No authoritative repo-wide test suite or coverage threshold was discovered. Use targeted checks:

- Packaging changes: validate `.claude-plugin/plugin.json` parses, every listed skill directory exists, and each has `SKILL.md`.
- README changes: validate local links and the logo asset path.
- Skill-content changes: run or reason through `skills/self-evolution/scripts/structural_check.py` for the changed skill when practical.
- Self-evolution changes: preserve L1/L2/L3 evaluation semantics, traces, timing/cost capture, ledgers, and deterministic gate behavior.
- Harness hook changes: smoke the relevant hook with representative JSON stdin and verify inactive no-op behavior when `.harness-active` is absent. For stateful changes, exercise a temporary harness state root rather than editing real project state.
- Code-review changes: verify the final output contract remains a JSON array of at most 15 findings and that candidate verification categories stay intact.

Prefer deterministic checks (`contains`, `regex`, `json_valid`, `file_exists`, `script`) over LLM-judged assertions where possible. If a task needs LLM judging, use temperature 0 and keep raw traces.