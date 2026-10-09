# Repository map and review notes

The root contains the current fitted research Notebook, launch script and dependency files.

| Directory | Purpose |
|---|---|
| data/research | Newly simulated seed-level tables, empirical anchors and derived summaries |
| research | Complete case design, checkpointed simulations, summaries, independent 600x15 calibration and report rendering |
| calibration | Parameter fitting scripts, pinned input adapters, empirical reconstructions and fit evidence |
| calibration/deployment/master | Historical model and tables used only for provenance and precision controls |
| calibration/download | Byte-pinned original Notebook source |
| results/research | Fresh executed report, figures, computed tables and execution checks |
| results/calibrated | Live fitted-profile migration animation, event data and decoded MP4 |
| tests | Animation, CLI and registry regression tests |
| rebuild_scripts | Model loading and validated case/batch entry points |
| tools | Video export, project audit and test launcher |
| docs | Repository documentation and review evidence |

PR #47's useful deterministic threshold tie handling and static-competition generator are retained. Its removal of calibration, animation and regression tests is repaired. Duplicate download trees, duplicate output packages, root historical caches, scratch pickle experiments and obsolete generated reports are removed. Immutable hashed calibration sources are retained.

No PowerPoint presentation was included in the reviewed PR or repository tree, so PPT improvements cannot be verified from this repository.
