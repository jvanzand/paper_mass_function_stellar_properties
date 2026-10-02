# Stellar-properties mass-function workflow

`run.py` is the single editable entry point for the paper's occurrence
calculations. It builds or loads the CLS stellar catalog, validates the named
stellar subsamples, and calls `occurrence.run.run_multiple()` once for each
entry in `RUN_CONFIGURATIONS`.

The default executable behavior is:

```bash
python run.py
```

For interactive use, import `main` and choose behavior with function arguments:

```python
from run import main

main(validate_only=True)
main(dry_run=True, run_names=["stellar2params"])
main(plots_only=True)
main(rebuild_star_catalog=True)
```

Scientific binning and sample choices live near the top of `run.py` and in
`config_dict.py`. Results are written beneath `results/`; each occurrence tier
contains a manifest used to reject stale cached products after relevant catalog
or configuration changes.

The CLS source tables remain in the sibling `occurrence/cls_files` directory.
The exact derived catalog used here is cached in
`data/derived/star_catalog.json` when the workflow is first validated or run.
