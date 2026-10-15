# Reporting-interval study (post-hoc, simulated)

**Question.** How does the customer-meter reporting interval (15, 30 or 60 minutes) affect the
detector's ability to tell a physical outage from a communication failure?

**Status:**
- **Post-hoc and simulated.** It ran on three SimBench low-voltage networks that earlier work had
  already examined, so it is a sensitivity study, not a confirmatory test. It contains no Tunisian
  data.
- **Produced by the code at commit 6853c6e on branch `cadence-study`.** That code is not part of this
  branch. The files here are unchanged copies of that commit's outputs and documents.
- **The protocol was written before the run but not committed before it.** The order can only be
  supported by file times and hashes, not by git history ([PROVENANCE.md](PROVENANCE.md)). The study
  is therefore not pre-registered in a verifiable sense.

## Files

| File | Content |
|---|---|
| [PROTOCOL_cadence_v1.md](PROTOCOL_cadence_v1.md) | Hypotheses, conditions, frozen and refitted parameters, metrics, acceptance criteria |
| [INTERPRETATION.md](INTERPRETATION.md) | Answers to the five questions; supported findings, findings added after the results, negative results, limitations |
| [PROVENANCE.md](PROVENANCE.md) | Modification times and SHA-256 hashes of the protocol, code and first result files |
| [DEVIATIONS.md](DEVIATIONS.md) | Deviations from the protocol (none) and analyses added after the results |
| [V2_CANDIDATES.md](V2_CANDIDATES.md) | Method changes suggested by the findings; not implemented |
| `results/studies/reporting_interval/summary.json` | Pre-specified analysis |
| `results/studies/reporting_interval/posthoc.json`, `mechanisms.json` | Analyses added after the results |
| `results/studies/reporting_interval/cadence_summary.png` | Summary figure |

Ledger rows CAD-1 to CAD-14, CAD-L1, CAD-L2 and CAD-A1 to CAD-A4 in
[docs/CLAIMS_LEDGER.md](../../CLAIMS_LEDGER.md) hold every number. The main findings:
- coverage falls as the interval grows (CAD-1);
- at 60 minutes the detector is unsafe, mainly because short events become unobservable (CAD-4,
  CAD-8);
- two flaws of the frozen detector appear at coarse intervals: late stored readings counted as
  reported energy, and outages starting partway through an interval (CAD-10, CAD-11, CAD-L1,
  CAD-L2).

Figures and tables contain information from the SimBench database, made available under the
ODbL 1.0.

## Reproduce (on branch `cadence-study`, not on this branch)

```
git worktree add ../shahid_cadence cadence-study
cd ../shahid_cadence
python -m shahid.cadence run          # 3 networks x 3 intervals; at most 2 workers
python -m shahid.cadence analyse      # writes results/cadence_v1/summary.json
python results/cadence_v1/posthoc/diagnose.py
python results/cadence_v1/posthoc/posthoc_analysis.py
python results/cadence_v1/posthoc/mechanisms.py
```

On that branch the outputs are in `results/cadence_v1/`. The copies here were taken from commit
6853c6e.
