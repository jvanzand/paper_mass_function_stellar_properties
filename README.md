# Stellar-properties mass-function workflow

`run.py` is the single editable entry point for the paper's occurrence
calculations. It builds or loads the CLS stellar catalog, validates the named
stellar subsamples, and calls `occurrence.run.run_multiple()` once for each
selected entry in `RUN_CONFIGURATIONS`. `RUNS_TO_DO` lists the entries to run
by default; set it to `None` to run all of them, or pass `run_names` to
`main()` to override it.

The default executable behavior is:

```bash
python run.py
```

For interactive use, import `main` and choose behavior with function arguments:

```python
from run import main

main(validate_only=True)
main(dry_run=True, run_names=["paper_bounds"])
main(plots_only=True)
main(rebuild_star_catalog=True)
```

Scientific binning and sample choices live near the top of `run.py` and in
`config_dict.py`. Results are written beneath `results/`. Existing Tier 1 and
Tier 2 directories are reused; delete one when its products should be
regenerated. Tier 3 fits rerun and overwrite existing products whenever
`run_fits=True`; use `plots_only=True` to reuse saved fits.

The CLS source tables remain in the sibling `occurrence/cls_files` directory.
The exact derived catalog used here is cached in
`data/derived/star_catalog.json` when the workflow is first validated or run.
