# Deviations from PROTOCOL_cadence_v1.md

**None** affecting simulation, evidence, verdicts or matching. No bug fix was made, and no
condition was rerun.

**Additions after results** are listed here for transparency. They are not deviations, because
they change no pre-specified quantity:
- `results/cadence_v1/posthoc/diagnose.py` regenerates the evaluation simulations
  deterministically, checks that every lr_band verdict is identical to the stored raw results (all
  18 grid × seed × cadence jobs matched), and records the evidence-window contents.
- `results/cadence_v1/posthoc/posthoc_analysis.py` adds:
  - the transition table and coverage decomposition;
  - timing relative to event end;
  - decisions after event end;
  - K = 1 merging;
  - the outage start offset.

**One protocol statement corrected in interpretation, not in the protocol text:**
- Protocol §7 calls an episode "observable" if it suppresses at least K consecutive readings, and
  the code computes this as the number of coarse transmission times inside the event.
- For communication failures this counts *delayed* readings, not lost ones. For outages it counts
  readings never sent. The two are equivalent for silence detection, so no change was needed.
