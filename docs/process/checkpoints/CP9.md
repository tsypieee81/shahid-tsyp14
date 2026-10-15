# CP9 — Goal coverage and documentation pack

## Implemented
- G2: `shahid/explain.py` with the verdict record (cause, probability, runner-up, evidence numbers, abstention reason), a deterministic template explanation, and an append-only, hash-chained decision log with verification. `tests/test_explain.py` enforces that every number in an explanation comes from the record, and that tampering is detected.
- G3: `configs/escalation.yaml` says which verdicts the automated statistical detector may handle alone and which need a human. DESIGN CHOICE, not validated with operators.
- G4: PROPOSED design note only, then in `docs/G4_knowledge_sharing.md`; now the single G4 design is `docs/PRELIMINARY_DESIGN.md` Section 5.4 (the note was removed during submission packaging and remains in the history at tag `phase1-frozen-cp12`).
- Demo: `python -m shahid.explain` → `results/decision_log_demo.jsonl`.
- Documentation: `README.md`, `docs/LIMITATIONS.md` (14 items), `docs/related_work_notes.md` (6 verified references, no novelty claim), `docs/RESULTS.md` (ledgered numbers only), `docs/REUSE.md` (licences read from package files).
- Dataset snapshot: `dataset/` with the fault-free year and one episode scenario (observed/context/labels, about 25 MB), ODbL attribution.
- Reproducibility: `shahid/reproduce.py` (every stage) and `shahid/verify_repro.py` (fresh-clone check).

## Measured
- C9-01: the demo shows one correct comms verdict and one confidently wrong verdict (a 7-meter outage called a comms failure with probability 0.996).
- C9-02: in a fresh clone with a fresh environment, all 14 tests pass, and the fast stages and the dataset regenerate identically.

## Failed or surprising
- The demo surfaced the method's most dangerous failure: confident comms verdicts can be wrong when another meter's delayed reading carries an unexpected load. It is documented (LIMITATIONS item 12) with a recommended escalation change. The change was not applied, so the reported results keep the frozen policy.
- The full pipeline was not re-run in a fresh clone because the long stages take hours and heat the laptop. Determinism of the fast stages and the dataset is verified.

## Assumptions remaining
- P7 (transformer meter), A-DIV (diversity), A-METERERR/A-TMETERERR/A-COMMS (error models), A-ESCAL and A-SELECT (policy choices) are untested against reality by construction.

## Decision and recommendation
- Phase 1 deliverables are complete. Before the 13 October freeze: optionally run `python -m shahid.reproduce` overnight in a fresh clone to confirm the long stages, and have the team read `docs/LIMITATIONS.md` before writing the proposal.
