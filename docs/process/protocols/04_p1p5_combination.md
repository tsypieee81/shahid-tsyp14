# Protocol 04 — Interaction of priorities 1 and 5: evaluation order and the combined method

Registered 2026-10-14, before any code for protocols 01 or 03 exists. Frame: protocol 00.

## Why they interact
After splitting (P5), most tiny silent groups are single-meter losses, which is what the
size-dependent prior (P1) addresses. P1 fitted on unsplit groups may be miscalibrated on split ones.

## Registered order
1. **P1 alone**: selected on development validation (protocol 01).
2. **P5 alone**: no parameter (protocol 03).
3. **P1+5**: P5 grouping, then P1's model **refitted on split development training groups** (same
   candidates P1a/P1b, same bins, same band grid) and its band chosen by rule v3 on split development
   validation. Chosen on development validation ONLY, before any confirmatory row exists.
4. All three, plus version 1, are frozen and evaluated **once** in protocol 05, with the same safety
   rule. No candidate is re-selected after a confirmatory row is seen.

## Endpoints (confirmatory, protocol 05)
- The H1 endpoints of protocol 01 for P1+5 against v1.
- The H5 endpoints of protocol 03 for P1+5 against v1.
- Descriptive: P1+5 against P1 and against P5 on the same rows.

## Compute ESTIMATE
Refit and selection reuse the protocol 03 split tables: minutes.
