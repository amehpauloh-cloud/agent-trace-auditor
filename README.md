# Agent Trace Auditor

An offline Python CLI for inspecting tool-use traces and producing evidence-linked findings. It detects unsupported completion claims, missing tool arguments, unapproved tools, orphan results and references to failed or future evidence.

**Portfolio demonstration:** all examples are synthetic. This is original demonstration code, not an employer system or a production deployment.

## Why it matters

A polished final answer can conceal a failed tool call. This project checks the sequence behind a claim and returns call IDs so a reviewer can locate the failure. It separates structural validity from semantic correctness.

## Run

Python 3.11+; no third-party dependencies or API keys.

```bash
python -m unittest discover -s tests -v
python auditor.py examples/failing_trace.json
```

The supplied example produces two findings: `MISSING_ARGUMENT` and `INVALID_EVIDENCE`. Exit codes: **0** checks pass, **1** findings detected, **2** invalid input. Use `--output report.json` to save a report.

## Trace contract

The root contains `policy` and ordered `steps`. Each step has a unique string `id` and a `type`: `tool_call`, `tool_result`, or `final`. Tool calls provide `tool` and an `arguments` object. Results reference `call_id` and a `status` of `success` or `error`. A final step may set `claims_completion` and list call IDs in `evidence`. `policy.allowed_tools` is an explicit allowlist; an omitted list permits no tools.

The auditor never executes calls. It only accepts evidence whose successful result precedes the claim. An observed success status is **not proof** that the content is factually correct; that requires task-specific validators and human review.

## Design tradeoffs and limits

- Deterministic rules keep findings reproducible and inexpensive, but cannot judge whether an argument meaningfully answers a task.
- The caller supplies the policy and result statuses. Untrusted logs can lie.
- This is a compact JSON schema, not a universal vendor adapter. Adapters, typed schema validation and streaming support are future work.
- Do not put credentials, personal data or proprietary traces in public examples.

## Evaluation

Unit tests cover happy paths, failed and future evidence, missing inputs, malformed records, and duplicate/orphan results. The committed example report is generated with the CLI; no LLM judge is used.

MIT licensed. See `LICENSE`.
