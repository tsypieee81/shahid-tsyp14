# SHAHID Phase 1 dataset (simulated)

**SIMULATED**: not utility data and not Tunisian data. Read [../docs/LIMITATIONS.md](../docs/LIMITATIONS.md)
before using it.

| Folder | Content | Regenerate |
|--------|---------|------------|
| `baseline_semiurb5/` | fault-free year 2016, development grid SimBench `1-LV-semiurb5--0-sw`, nominal parameters | `python -m shahid.scenario configs/baseline.yaml dataset/baseline_semiurb5` |
| `episodes_semiurb5_seed101/` | same grid with 340 injected outage and communication-failure events (standard episode mix, seed 101) | `python -m shahid.scenario configs/cp5_episodes.yaml dataset/episodes_semiurb5_seed101` |

Each folder holds `observed/` (what a utility export could contain) and `context/` (concentrator and zone
maps, installed PV). `labels/` holds the injector's ground truth, `manifest.json` the config, hash, commit
and date. Columns: [../docs/data_contract.md](../docs/data_contract.md). Generation rules:
[../docs/anomaly_generation.md](../docs/anomaly_generation.md).

`truth/`, the hidden power-flow state (about 76 MB per folder), is not committed. Generation is
deterministic and seeded, so the regenerate command recreates it identically.

## Licence and attribution

Derived from the SimBench database (simbench 1.6.3) under the Open Database License (ODbL 1.0), with
contents under the Database Contents License (DbCL 1.0). This dataset is shared under the same ODbL terms. Attribution: SimBench, University of Kassel, TU Dortmund, RWTH Aachen University
and Fraunhofer IEE (from the simbench package licence text).
