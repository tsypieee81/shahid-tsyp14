# People study pack (protocol 07b)

Protocol: `docs/process/protocols/07b_people_study.md` (with addendum A). Instructions and consent text:
[INSTRUCTIONS.md](INSTRUCTIONS.md). Booklets: `booklet_1.md`, `booklet_2.md`. Answer sheet:
`answer_sheet_template.csv`. Answer key (never shown to participants): `results/p7/people_key.json`.

## After submission, without assistance

1. **Collect.** One anonymous sheet per participant in `docs/process/people_study/answers/P01.csv`,
   `P02.csv`, … (copied from the template). These files stay on the team's machine: they are
   gitignored and never committed.
2. **Analyse.** From the repository root:
   ```bash
   python -m shahid.p7_people analyse
   ```
   It writes `results/p7/people_study.json` (stamped). With fewer than 8 participants every hypothesis
   is reported as underpowered.
3. **Ledger rows.** Add one row per reported number to `docs/CLAIMS_LEDGER.md`, after the last P2C row,
   with this template:
   ```
   | P7B-01 | [Phase 2, protocol 07b, people study, N participants outside the team] Form B cause agreement <rate> (Wilson <lo>–<hi>), H7a <verdict>; Form A action agreement <rate> (<lo>–<hi>), H7b <verdict>; Fleiss' kappa <B> / <A>; confident-wrong item followed <k> of <n> | results/p7/people_study.json | `python -m shahid.p7_people analyse` | <commit from the stamp> | <config_hash from the stamp> |
   ```
   Copy every value from `results/p7/people_study.json` exactly as printed there.
4. **Finding note.** Write `docs/process/findings/17_people_study.md`: question, participants (count and
   background categories only), results with the ledger row, interpretation, limits.
5. **Check.**
   ```bash
   python -m shahid.check_numbers
   python -m shahid.check_numbers --doc docs/process/findings/17_people_study.md
   ```
   Both must report zero unmatched numbers.
6. **Report.** Replace "RESULTS PENDING" in `docs/EXTENDED_REPORT.md` (sections 5 and 7, row B36) with the result
   and its ledger row; then `python -m shahid.check_numbers --doc docs/EXTENDED_REPORT.md` and
   `python -m shahid.build_report`.
7. **Commit** with this message template:
   ```
   People study results (protocol 07b): N participants; H7a <verdict>, H7b <verdict>; ledger P7B-01; finding 17; report updated
   ```

**Rule.** A people-study result enters the repository only with a ledger row and a finding note. No
result is reported from memory, from a partial count, or without the stamped result file.
