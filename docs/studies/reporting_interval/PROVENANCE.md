# Provenance of the cadence-v1 study

**The protocol was written before the runs, but it was not committed before them.** Nothing in this
worktree is committed: branch `cadence-study` is still at 1cbf994, and every cadence file is
uncommitted. The order of events therefore **cannot be verified from git history**. The facts
below are file modification times (which a user can alter, so they are not proof) and SHA-256
hashes. The study is **not** pre-registered in any verifiable sense. At most, the protocol hash was
recorded by the run code at run start, and the protocol is unchanged since then.

## Facts

| File | Last modified (local time, 2026-10-11) | SHA-256 |
|---|---|---|
| `docs/cadence/PROTOCOL_cadence_v1.md` | 14:41:58 | b6643404031a4ea8669a741da021a180fca03213a82b8cf3af059103035343f6 |
| `shahid/detect.py` (cadence generalisation) | 14:42:56 | 3c3be43ce80a0d69e67fccf2482091ef75ad54d9945a70bfac973f29a0e664b2 |
| `shahid/baselines.py` | 14:42:56 | 8cb891daf0adc3e3c55854be26f425314d410df2c19d994da9259d512a62eb34 |
| `shahid/observe.py` | 14:43:14 | b8ebb26fbac6062fd0c5000ecdb893b6a95a6a6fa4bc2e20a924bce1f32ae6a7 |
| `shahid/scenario.py` | 14:43:27 | 8f7fb3581b8f5ad1b3749f7534051616ade5c84c6f505252ef9580b27b5cf3e7 |
| `configs/cadence/cadence_v1.yaml` | 14:44:22 | 52c16f0e3339c93e4e5f97e8f69322c72ae60df8a0a8cd1cb95a1847c308f2a6 |
| `shahid/cadence.py` | 14:44:23 | 4ff85d7b6c075a0ef068e0ed65de2cda8e1b333f37d94312384f8cc26d190051 |
| `tests/test_cadence.py` | 14:45:13 | 1a43f5fc4135f49ca00d05b6c9a9185364986e7d207065df246656eea713d29b |
| `results/cadence_v1/protocol_sha256_dev.txt` (written by `run("dev")`) | 14:46:39 | file content records the protocol hash b6643404…43f6 |
| `shahid/cadence_analysis.py` | 14:47:27 | b05dcc7ad3c830fe04148ab433e2b8794b6263dccd4d916451bdd48752669a78 |
| first raw result `results/cadence_v1/raw/dev_semiurb5_15__episodes.parquet` | 14:47:45 | 5db6af5b2286c63d5a3fdb3786b128cfdbc38451b10edc56ce27f07b7e08b687 |
| `results/cadence_v1/protocol_sha256_eval.txt` (written by `run("eval")`) | 14:50:47 | records the same protocol hash |
| first evaluation result `results/cadence_v1/raw/eval_semiurb5_15__episodes.parquet` | 14:53:29 | 742231b3b67ec686dc94b3acecb003f8148232e97fbf2562295e3c141e179821 |

- The evaluation ran from 14:50:45 to 15:03:29.
- After the run, the hashes of the protocol, the configuration and every simulation, detector,
  matching and runner code file were recomputed. They are identical to the values above.
- The analysis code `shahid/cadence_analysis.py` was written after the protocol and before the
  evaluation run (14:47:27 < 14:50:45). It was not changed afterwards.
- `results/cadence_v1/summary.json` carries the stamp commit `1cbf994-dirty`, because the code was
  uncommitted. The code state at run time is identified only by the hashes above.

## What these facts support

- The protocol file was last modified before any code of the study and before the first result
  file, and it is unchanged since. That is consistent with "written before the runs", but it
  cannot exclude an earlier, different version.
- The design decisions were approved by the user before the protocol was written. The protocol
  records them; it did not originate them independently of the user dialogue.
- The development run (seed 701) was inspected before the evaluation run, for plumbing only. Its
  K = 1 undetected counts were examined and judged a property of the rule; no code changed.
- **Post-hoc material:** everything in `results/cadence_v1/posthoc/` was added after the
  evaluation results were inspected. That includes `diagnose.py`, `posthoc_analysis.py`,
  `posthoc.json` and the onset-offset analysis.
