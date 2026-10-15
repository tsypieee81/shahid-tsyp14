# Reuse register

Licences were read on 2026-10-07 (notebook tooling on 2026-10-11) from each installed package's licence file or METADATA in
`.venv/Lib/site-packages/<package>.dist-info/`, or from the official page named.
Origin: REUSED / ADAPTED / ORIGINAL.

| Resource | Source | Version | Licence (where read) | Origin | Used for |
|----------|--------|---------|----------------------|--------|----------|
| SimBench networks and profiles | pip `simbench` | 1.6.3 | Database ODbL 1.0; contents DbCL 1.0 (METADATA) | REUSED | LV networks and load/PV profiles. Any derived dataset we publish (`dataset/`) falls under ODbL share-alike and needs attribution |
| simbench (code) | pip | 1.6.3 | BSD-3-Clause (METADATA) | REUSED | loading networks, absolute profiles |
| pandapower | pip | 3.5.5 | BSD-3-Clause (licenses/LICENSE) | REUSED | AC power flow, topology graph |
| numba | pip | 0.68.0 | BSD (METADATA "License: BSD"; licenses/LICENSE, BSD-style) | REUSED | pandapower speed-up only |
| llvmlite | pip | 0.50.0 | BSD-style (LICENSE) | REUSED | numba dependency |
| numpy | pip | 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 (License-Expression) | REUSED | arrays |
| pandas | pip | 2.3.3 | BSD 3-Clause (LICENSE) | REUSED | tables |
| pyarrow | pip | 25.0.1 | Apache-2.0 (License-Expression, licenses/LICENSE.txt, NOTICE.txt) | REUSED | parquet files |
| scipy | pip | 1.17.1 | BSD 3-clause style (LICENSE.txt) | REUSED | Student-t, statistics |
| scikit-learn | pip | 1.9.1 | BSD-3-Clause (licenses/COPYING) | REUSED | gradient boosting in the expected-load forecaster test; Isolation Forest; the classifier-comparison study |
| matplotlib | pip | 3.11.2 | Matplotlib License Agreement, PSF-style (LICENSE) | REUSED | figures |
| PyYAML | pip | 6.0.3 | MIT (licenses/LICENSE) | REUSED | configs |
| pytest | pip | 9.1.1 | MIT (licenses/LICENSE) | REUSED | tests |
| networkx | pip | 3.6.1 | BSD-3-Clause (licenses/LICENSE.txt) | REUSED | zone derivation (via pandapower topology) |
| nbformat | pip (dev only, `requirements-dev.txt`) | 5.11.1 | BSD 3-Clause (METADATA, licenses/LICENSE) | REUSED | notebooks |
| nbclient | pip (dev only) | 0.11.0 | BSD 3-Clause (METADATA, licenses/LICENSE) | REUSED | executing notebooks |
| nbconvert | pip (dev only) | 7.17.1 | BSD 3-Clause (METADATA, licenses/LICENSE) | REUSED | notebook tooling |
| ipykernel | pip (dev only) | 7.4.0 | BSD-3-Clause (License-Expression, licenses/LICENSE) | REUSED | notebook kernel |
| shap | pip (dev only) | 0.51.0 | MIT (METADATA "License: MIT License"; licenses/LICENSE, read 2026-10-12) | REUSED | SHAP explanations in the classifier-comparison study only |
| slicer | pip (dev only, shap dependency) | 0.0.8 | MIT (METADATA classifier; LICENSE, read 2026-10-12) | REUSED | shap dependency |
| streamlit | pip (UI preview only, `requirements.txt`, not in the lock file) | 1.65.0 | Apache-2.0 (License-Expression in METADATA, read 2026-10-13) | REUSED | operator UI preview `ui/dashboard.py` (decision 0006) |
| altair | pip (UI preview only, installed as a streamlit dependency, not in the lock file) | 6.3.0 | BSD-3-Clause (licenses/LICENSE in the installed package, read 2026-10-13) | REUSED | charts of the operator UI preview `ui/panels/` (decision 0006) |
| pypdf | pip (dev only) | 6.20.1 | BSD-3-Clause (License-Expression; licenses/LICENSE, read 2026-10-13) | REUSED | text extraction for the number check of the built proposal PDF |
| ruff | pip (dev only) | 0.17.0 | MIT (License-Expression; licenses/LICENSE, read 2026-10-13) | REUSED | lint inventory (`ruff check --select F`) |
| Tectonic | official release binary, github.com/tectonic-typesetting/tectonic | 0.17.0 | MIT (LICENSE in the official repository, read 2026-10-13) | REUSED | builds the proposal PDF (not a Python dependency; `proposal/README.md`) |
| IEEEtran class and bibliography style | Tectonic bundle | class V1.8b, style 1.14 | LaTeX Project Public License (header of IEEEtran.cls) | REUSED | proposal layout and references |
| TeX Gyre Termes font | Tectonic bundle | font files `texgyretermes-*.otf` | GUST Font License (copyright string in the font's name table) | REUSED | proposal body text, embedded in the PDF |
| Amiri font | Tectonic bundle | `Amiri-Regular.ttf` | SIL Open Font License 1.1 (licence field in the font's name table) | REUSED | the Arabic word in the proposal title, embedded in the PDF |
| STIX fonts | shipped with matplotlib | matplotlib 3.11.2 | SIL Open Font License 1.1 (`mpl-data/fonts/ttf/LICENSE_STIX`) | REUSED | text in the proposal figures, embedded in the figure PDFs |
| UCI ElectricityLoadDiagrams20112014 | UCI page, DOI 10.24432/C58C86 | — | CC BY 4.0 (official page) | not used | candidate only |
| Low Carbon London smart-meter data | London Datastore page | — | "Creative Commons Attribution" (version not shown on summary) | not used | candidate only |

Full transitive versions are in `requirements.lock`. Everything in `shahid/` is ORIGINAL unless a
module docstring says otherwise. `shahid/grid.py` is ADAPTED: a stepping loop around REUSED
pandapower and simbench calls.

## Licences of this repository (decided 2026-10-11)
- **Code** (`shahid/`, `tests/`, `notebooks/`, configs): MIT, see `LICENSE`.
- **Generated dataset** (`dataset/`): Open Database License (ODbL 1.0), because it is derived from the SimBench database, which is ODbL 1.0 with contents under DbCL 1.0 (simbench 1.6.3 licence file). Attribution and terms in `dataset/LICENSE.md`. The team chose ODbL over CC BY 4.0 because ODbL share-alike applies to derivative databases, and whether the simulated readings are a derivative database or a produced work was not settled.
