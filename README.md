# Stellar-properties mass-function workflow

`run.py` is the single editable entry point for the paper's occurrence
calculations. It builds or loads the CLS stellar catalog, validates the named
stellar subsamples, and calls `occurrence.run.run_multiple()` once for each
selected entry in `RUN_CONFIGURATIONS`. `RUNS_TO_DO` lists the entries to run
by default; set it to `None` to run all of them, or pass `run_names` to
`main()` to override it.

## Machine-specific input paths

The injection-recovery files and companion posteriors are too large to keep
in the repository, so each machine records where they live in an untracked
`local_paths.json`. Create it from the template and edit both entries:

```bash
cp local_paths.example.json local_paths.json
```

```json
{
  "recoveries_dir": "/absolute/path/to/cls_recoveries",
  "posteriors_dir": "/absolute/path/to/resampled_posteriors_1ksamples"
}
```

`run.py` stops with an explanatory error if the file or either entry is
missing.

## Running

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

## Replotting saved fits

A `RUN_CONFIGURATIONS` entry with `"reuse_fits_from": "<run>"` replots another
run's fits without refitting, e.g. with a different `plot_models_list`. It
inherits the source run's edges and fit settings, may set only plot options
and subsets of the source's `tier1_list`/`tier2_list`, and writes to
`results/<tier1>/<tier2>/<its own name>/`. That folder's `saved_chains` and
`saved_dicts/fit_data.npz` are relative links to the source run's files, so the
source run must be fitted first.

The CLS source tables remain in the sibling `occurrence/cls_files` directory.
The exact derived catalog used here is cached in
`data/derived/star_catalog.json` when the workflow is first validated or run.
