# Tunisia study (simulated sensitivity and deployment modes)

**Status.**
- **SIMULATED on German SimBench grids.** Every scenario value is an ASSUMPTION
  ([TUNISIA_PARAMETER_PROVENANCE.md](TUNISIA_PARAMETER_PROVENANCE.md)). Nothing here was measured on
  STEG equipment or data, and nothing is reshaped to look Tunisian.
- **Produced by the code at commit 3ab24b8 on branch `tunisia-study`**, with results committed at
  1cbf994 on that branch. The code (`shahid.tunisia`, `shahid.deploy`) is not part of this branch. The
  files here are copies of that branch's documents and summary outputs; the only edit replaces the
  name of a development-tool instruction file with "project rule" in two sentences.
- **Protocol:** `docs/eval_protocol.md` addendum E on branch `tunisia-study`, committed (37dfb6a)
  before any number was computed. The detector is the frozen version 1; nothing was tuned.

## Files

| File | Content |
|---|---|
| [TUNISIA_EVIDENCE_REVIEW.md](TUNISIA_EVIDENCE_REVIEW.md) | public evidence on the Tunisian grid and AMI rollout, with unknowns |
| [TUNISIA_PARAMETER_PROVENANCE.md](TUNISIA_PARAMETER_PROVENANCE.md) | where every sensitivity value comes from |
| [TUNISIA_FEASIBILITY.md](TUNISIA_FEASIBILITY.md) | deployment feasibility and plan |
| [TUNISIA_RESULTS.md](TUNISIA_RESULTS.md) | generated tables |
| [TUNISIA_COMPARISON.md](TUNISIA_COMPARISON.md) | comparison with the frozen baseline, claims, verdict |
| `configs/tunisia/cells_v1.yaml` | the sensitivity cells and deployment modes |
| `results/tunisia/tn_eval.json`, `tn_safe_gate.json`, `tn_cells.png` | summary outputs |

Per-episode records (`results/tunisia/records/`) stay on branch `tunisia-study`. Ledger rows TN-H1 to
TN-H4, TN-LOSS and TN-SAFE in [CLAIMS_LEDGER.md](../CLAIMS_LEDGER.md) hold every number.

## Reproduce (on branch `tunisia-study`, not on this branch)

```
git worktree add ../shahid_tunisia tunisia-study
cd ../shahid_tunisia
python -m shahid.tunisia all
python -m shahid.tunisia analyse
python -m shahid.tunisia safe
```

Figures and tables contain information from the SimBench database, made available under the ODbL 1.0.
