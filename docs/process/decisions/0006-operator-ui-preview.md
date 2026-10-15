# 0006: A minimal operator UI preview (Streamlit), as an exception to the scope fence

Date: 2026-10-13. Decided by the team.

**Context.** The project's scope fence excludes dashboards and UIs unless an experiment proves the
need. No experiment here proves it. The challenge scores "Prototype Functionality & Features", and
the brief requires an operator interface for the final phase (proposal Section V-C).

**Decision.** Build a minimal operator-queue preview in `ui/dashboard.py` with Streamlit. This is a
team decision about the challenge deliverable, **not** an experimental finding, and it changes no
method, result or claim.

**Scope of the preview.**
- It reads verdict records from a decision log (default `results/decision_log_demo.jsonl`, written
  by `python -m shahid.explain`) and shows the three item types of Section V-C, never merged.
- Approve, override (reason required) and defer actions are appended to a separate hash-chained
  operator log, `ui/operator_log.jsonl` (not tracked), with the same SHA-256 chaining as the
  decision log (`shahid.explain`).
- It is not connected to any live data, it is not validated with operators, and it is not used in
  any result. The proposal keeps describing the operator interface as PROPOSED.

**Consequences.** Streamlit 1.65.0 (Apache-2.0) is pinned in `requirements.txt`, but not in
`requirements.lock`: the pipeline, the tests and CI do not install it. The licence is recorded in
`docs/REUSE.md`.
