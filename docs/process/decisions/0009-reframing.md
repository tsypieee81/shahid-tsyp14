# 0009: Reframing the report

Date: 2026-10-14. Decided by the team (submission brief, section 0).

**Decision.** Reframing changes voice and placement, never content: every measured number, negative
result and open question remains in the report; no sentence implies a capability that was not
measured.

**How it is applied.**
- Limitations move into one decision-boundary table (`docs/REPORT.md` section 8). Each former
  LIMITATIONS item keeps its number and figures; nothing is deleted.
- Anything designed but not built or not measured is labelled PROPOSED, wherever it appears.
- Every number in the report has a ledger row; `python -m shahid.check_numbers --doc docs/REPORT.md`
  must report zero unmatched.
- Where a brief's wording disagrees with a measurement, the measurement wins and the difference is
  reported to the team.
