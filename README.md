# Stellar-properties mass-function workflow

`run_occurrence.py` is the single editable entry point for the paper's
occurrence calculations. It builds or loads the CLS stellar catalog, validates the named
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

`run_occurrence.py` stops with an explanatory error if the file or either entry is
missing.

## Running

The default executable behavior is:

```bash
python run_occurrence.py
```

For interactive use, import `main` and choose behavior with function arguments:

```python
from run_occurrence import main

main(validate_only=True)
main(dry_run=True, run_names=["paper_bounds"])
main(plots_only=True)
main(rebuild_star_catalog=True)
```

Scientific binning and sample choices live near the top of
`run_occurrence.py` and in
`config_dict.py`. Results are written beneath `results/`. Existing Tier 1 and
Tier 2 directories are reused; delete one when its products should be
regenerated. Tier 3 fits rerun and overwrite existing products whenever
`run_fits=True`; use `plots_only=True` to reuse saved fits.

## Convergence checks

After fitting, each experiment's `saved_chains/convergence.txt` lists every
sampled parameter's autocorrelation time and whether the chain spans at least
`convergence_target` (default 50) of them, and the run ends with a warning
naming any fits that do not. To check results that already exist:

```bash
python -c "import run_occurrence; from occurrence import convergence; convergence.summarize('results')"
```

## Tables, variables, and summary plots

`run_post_fit_analysis.py` builds the paper's LaTeX variables, tables, and
companion plots from saved results. Each entry in `POST_FIT_PRODUCTS` names the
`RUN_CONFIGURATIONS` entry it reads, so its Tier 3 folder comes from that run
and its Tier 1 and Tier 2 choices are checked against it. `PRODUCTS_TO_MAKE`
selects the products to build by default:

```bash
python run_post_fit_analysis.py
```

The `cdf_comparison` product draws one grid of normalized model CDFs: one
column per entry in `models` (e.g. sigmoid, logG) and one row per entry in
`sample_pairs` (e.g. `Mstar` for `highMstar` vs `lowMstar`), labeled with the
`config_dict.py` sample titles unless `labels` overrides them. Every sample
must have a chain for every model, and all are checked before plotting. Every
option is listed in the product, and the figure goes to
`results/<tier1>/allstars/<run>/plots/cdf_comparison.png`, next to the
catalog plots.

Products stop with a message naming the missing result folders if their runs
have not been completed. Outputs go to `results/paper_tables/`; plots go to the
matching experiment's `plots` folder. It needs only `results/`, not the
recoveries or posteriors, so it can run on any machine holding the results.

Subset LaTeX commands carry their run's name with digits spelled out, so
`stellar3params` gives `\McStellarThreeParamsLowMstarLowFeHYoungNstars` and
`stellar3params_Miyazaki` gives
`\McStellarThreeParamsMiyazakiLowMstarLowFeHYoungNstars`.

`variables.tex` also has a labeled section comparing every high/low sample
pair (e.g. `highMstar` vs `lowMstar`) in each run: rates get a `Ratio`, log10
locations (sigmoid center, logG mu) a `Diff` in dex and its `Factor`, widths a
`Diff`, and every quantity a `Significance`, e.g.
`\McMstarPaperBoundsSigmoidParamCenterFactorBinaZero`. Activity compares old
relative to young.

## Collecting items for the paper

`collect_paper_items.py` rebuilds `paper_items/` with every figure, table, and
`variables.tex` the paper uses, laid out like the LaTeX project (tables at the
top level, figures in `Figures/`):

```bash
python collect_paper_items.py
```

Copy that folder from the remote machine and merge it over the LaTeX project,
e.g. `rsync -a paper_items/ /path/to/latex_project/`. Figures are named
`<plot>_<tier1>_<tier2>_<run>.png` (e.g. `ORD_mtrue_highFeH_paper_bounds.png`);
`PAPER_FIGURES` and `PAPER_TABLES` list what is collected. Every source must
exist before anything is copied, and the folder is emptied first so it holds
only current items.

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
