# Phase 13: Testing And CI

> This phase made InvoiceFlow prove its reliability automatically through backend tests, eval thresholds, and a passing GitHub Actions workflow.

---

## In Plain English

InvoiceFlow now has an automatic quality gate on GitHub. That means every push to the main branch can run checks without someone manually opening the app and hoping everything still works.

The key idea is simple: if the backend breaks, the tests should fail. If the finance workflow quality drops, the eval gate should fail. If both pass, the project looks more disciplined and production-aware.

This phase matters because AI projects can look fragile when they only have demos. A CI pipeline shows that InvoiceFlow has repeatable checks, not just a polished screen.

## What Is CI?

CI means continuous integration. In plain English, it is a robot checklist that runs when code is pushed.

For InvoiceFlow, CI checks:

- dependencies install correctly
- backend modules compile
- API reliability tests pass
- eval thresholds pass
- eval results are uploaded as an artifact

This turns the project from “it worked on my machine” into “GitHub can prove it works too.”

## The Problem It Solves

Before this phase, the repo already had an evaluation workflow, but it did not run the new backend tests. That meant the eval gate could pass while API reliability behavior was not checked in GitHub Actions.

This phase connected both pieces:

```text
compile backend
  -> run API tests
  -> run eval threshold gate
  -> upload eval report
```

Now CI checks both product reliability and AI workflow quality.

## What We Built

### Updated GitHub Workflow

Plain English: GitHub now runs backend tests before running the eval gate.

File changed:

```text
.github/workflows/eval.yml
```

The workflow was renamed:

```text
InvoiceFlow Eval Gate -> InvoiceFlow CI
```

The job was renamed:

```text
Finance-agent eval thresholds -> Backend tests and eval thresholds
```

This makes the workflow name more accurate because it now does more than eval.

### Compile Check

Plain English: GitHub checks that the backend Python files can be imported/compiled.

Command:

```text
python -m compileall api app tests
```

This catches syntax errors before tests or evals run.

### Backend Tests

Plain English: GitHub runs the API reliability tests from Phase 12.

Command:

```text
python -m unittest discover -s tests -p "test_*.py"
```

This checks the backend behavior for:

- health endpoint
- missing sample ID
- invalid extractor mode
- empty upload
- unsupported upload type
- text upload fallback

### Eval Threshold Gate

Plain English: GitHub checks that the AI workflow still meets quality thresholds.

Command:

```text
python -m app.eval.check_eval_thresholds --output eval-results.json
```

This protects:

- workflow routing
- extraction field match
- citation coverage
- grounding support
- anomaly detection
- AR draft checks
- RAG repair behavior
- latency threshold

### Eval Artifact Upload

Plain English: GitHub saves the eval output so someone can inspect the run later.

Artifact:

```text
eval-results.json
```

This helps prove reliability without requiring a local terminal.

## GitHub Verification

The latest GitHub Actions run passed:

```text
Workflow: InvoiceFlow CI
Run ID: 28461115515
Job: Backend tests and eval thresholds
Conclusion: success
```

Successful steps:

```text
Check out repository
Set up Python
Install dependencies
Compile backend modules
Run backend tests
Run eval threshold gate
Upload eval report
```

This confirms the CI workflow does not just exist in YAML. It actually ran successfully on GitHub.

## Why This Improves InvoiceFlow

This phase improves the project in three ways.

First, it makes the repo more professional. Recruiters and clients can see a real quality gate.

Second, it protects future changes. If a later edit breaks API behavior or eval quality, CI should catch it.

Third, it strengthens the “engineered, not just prompted” story. InvoiceFlow now has visible tests and measurable eval checks.

## Edge Cases And Gotchas

### CI Is Only As Strong As Its Tests

In plain English: Passing CI does not mean the whole product is perfect.

Technical cause: CI only checks the cases we write into tests and evals.

How to improve: Keep adding tests when new workflows or bug fixes are added.

### Eval Dataset Is Synthetic

In plain English: The evals are useful proof, but they are still based on bundled demo cases.

Technical cause: The dataset is local and synthetic, not real production invoice traffic.

How to improve: Add more realistic fixtures over time.

### Local Python Can Differ From CI Python

In plain English: GitHub uses Python 3.11, which is cleaner for this repo than the local Python 3.9 compatibility shim.

Technical cause: The repo uses newer Python features like `dataclass(slots=True)`.

How to improve: Document Python 3.10+ or 3.11 as the expected local runtime.

## How It Connects To Other Concepts

- **Backend reliability**: CI runs the reliability tests from Phase 12.
- **Evaluation dashboard**: CI produces the same eval result artifact the product can display.
- **Guardrails**: Tests and evals are quality guardrails around the workflow.
- **Portfolio readiness**: Passing GitHub Actions is visible proof of engineering discipline.
- **Deployment readiness**: CI lowers the chance of pushing broken code before deployment.

## Quick Reference

### Files Changed

```text
.github/workflows/eval.yml
steps.md
```

### CI Commands

```text
python -m compileall api app tests
python -m unittest discover -s tests -p "test_*.py"
python -m app.eval.check_eval_thresholds --output eval-results.json
```

### GitHub Run Checked

```text
Run ID: 28461115515
Conclusion: success
```

## Quiz Questions

1. Why should backend tests run before the eval gate?
2. What does the eval threshold gate prove that unit tests do not?
3. Why is uploading `eval-results.json` useful?
4. Why does a passing GitHub Actions run make the repo more portfolio-ready?
5. What is the difference between local verification and CI verification?

---

*Generated: 2026-06-30 | Project: invoiceflow-ai | Files: .github/workflows/eval.yml, tests/test_api_reliability.py, app/eval/check_eval_thresholds.py, steps.md*
