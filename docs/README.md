# Documents

Every result is SIMULATED; read [LIMITATIONS.md](LIMITATIONS.md) before any number.

## Start here

| Document | What it answers |
|---|---|
| [BRIEF_COVERAGE.md](BRIEF_COVERAGE.md) | each brief item, with status and evidence |
| [RESULTS.md](RESULTS.md) | every result table, generated from result files |
| [LIMITATIONS.md](LIMITATIONS.md) | where the method fails or is untested |
| [CLAIMS_LEDGER.md](CLAIMS_LEDGER.md) | every result, with file, command and commit |
| [EXTENDED_REPORT.md](EXTENDED_REPORT.md) | the full engineering record |

## Method and data

| Document | What it answers |
|---|---|
| [METHOD.md](METHOD.md) | how a silent group is formed, scored and decided |
| [data_contract.md](data_contract.md) | the columns the detector reads, and reading arrival |
| [anomaly_generation.md](anomaly_generation.md) | how events and data-quality faults are injected |
| [ASSUMPTIONS.md](ASSUMPTIONS.md) | every assumption, its type and status |
| [eval_protocol.md](eval_protocol.md) | the evaluation protocol, frozen before the held-out test |
| [REPRODUCE.md](REPRODUCE.md) | one command per stage; what a fresh clone reproduced |
| [REUSE.md](REUSE.md) | reused packages and their licences |

## Deployment

| Document | What it answers |
|---|---|
| [BUSINESS_CASE.md](BUSINESS_CASE.md) | cost and prerequisites for one STEG district, in TND |
| [PRELIMINARY_DESIGN.md](PRELIMINARY_DESIGN.md) | the design per challenge goal, built or not |
| [COMPLIANCE.md](COMPLIANCE.md) | superseded by BRIEF_COVERAGE.md |
| [tunisia/](tunisia/README.md) | simulated Tunisian conditions and deployment modes |

## Studies and literature

| Document | What it answers |
|---|---|
| [studies/classifier_comparison/](studies/classifier_comparison/README.md) | trained classifiers against the frozen method, post-hoc |
| [studies/reporting_interval/](studies/reporting_interval/README.md) | the effect of 15, 30 and 60 min readings, post-hoc |
| [literature/REVIEW.md](literature/REVIEW.md) | positioning against published work ([references](literature/REFERENCES.md)) |
| [related_work_notes.md](related_work_notes.md) | working notes on related work |

## Process records

| Folder | Content |
|---|---|
| [process/protocols/](process/protocols/) | study protocols, each committed before its run |
| [process/findings/](process/findings/) | one finding per checkpoint or protocol |
| [process/checkpoints/](process/checkpoints/) | checkpoint reports |
| [process/decisions/](process/decisions/) | design decisions |
| [process/people_study/](process/people_study/README.md) | the registered people study of the explanations, results pending |
| [process/AUDIT.md](process/AUDIT.md) | the scientific audit before the Phase 1 freeze |
| [process/phase2_candidates.md](process/phase2_candidates.md) | Phase 2 candidates, not implemented |

[number_allowlist.yaml](number_allowlist.yaml) lists document numbers that are not results, each with a
reason. Console screenshots: [figures/](figures/). Explainer video files: [media/](media/).
