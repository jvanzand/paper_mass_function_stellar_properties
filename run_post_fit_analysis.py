"""Make the paper's tables, LaTeX variables, and summary plots.

These products are built from the saved results of ``run_occurrence.py``.
Edit ``POST_FIT_PRODUCTS`` to define a product and ``PRODUCTS_TO_MAKE`` to
choose which of them run, or call :func:`main` from Python. Outputs are
written beneath ``results/paper_tables/`` (plots go to the matching
experiment's ``plots`` folder); ``collect_paper_items.py`` gathers the ones
the paper uses.

Each product names the ``RUN_CONFIGURATIONS`` entry whose results it reads,
so its Tier 3 folder comes from the run configuration and its Tier 1 and
Tier 2 choices are checked against that run before anything is made.
"""

from pathlib import Path

from config_dict import tier2_df_cuts_dict
from run_occurrence import RESULTS_DIR, resolve_run_configuration

from occurrence import post_fit_analysis as pfa


# Each entry becomes one call to ``occurrence.post_fit_analysis.<function>``.
# "run" names the RUN_CONFIGURATIONS entry to read (make_variables takes a list,
# "runs", and includes each run's own samples); "three_parameter_runs"
# (make_variables only) lists the three-parameter runs whose subset statistics
# are added to the variables file. Command names spell out the full results
# path: \McAllstarsPaperBoundsNstars for mtrue/allstars/paper_bounds, and
# \McStellarThreeParamsLowMstarLowFeHYoungNstars for the stellar3params subsets.
# plot_model_cdf_comparison products instead list "models" (columns) and
# "sample_pairs" (rows, e.g. "Mstar" for highMstar and lowMstar) from one run
# and tier1; the product name becomes the figure name.
# Every other key is passed through as a keyword argument.
POST_FIT_PRODUCTS = {

    # LaTeX variables for the main results, the no-GP escarpment fits, and
    # the three-parameter subsets. Each run contributes the samples it has.
    "variables": {
        "function": "make_variables",
        "runs": ["paper_bounds", "paper_bounds_noGP"],
        "three_parameter_runs": ["stellar3params", "stellar3params_Miyazaki"],
        "tier1_dirs": ["mtrue", "qtrue"],
        "tier2_types": ["allstars", "Mstar", "FeH", "Act"],
        "stack_dim": "a",
    },

    # Main text: Model parameters for the full sample (references variables.tex)
    "full_sample_parameter_table": {
        "function": "make_parameter_table",
        "run": "paper_bounds",
        "t1": "mtrue",
        "t2": "allstars",
        "models": ["logG", "sigmoid"],
        "caption": "Derived Model Parameters for Full Sample",
        "stack_bin": 0,
        "stack_dim": "a",
    },
    
    # Main text: Mass-metallicity-age occurrence tables (references variables.tex)
    "three_param_tables": {
        "function": "make_three_parameter_tables",
        "run": "stellar3params",
        "t1": "mtrue",
        "occurrence_model": "piecewise",
    },
    
    # Main text: Companions colored by host properties over the average completeness
    "companion_plots": {
        "function": "plot_companions_by_stellar_parameter",
        "run": "paper_bounds",
        "tier1_dirs": ["mtrue"],
        "tier2_types": ["allstars"],
        "stellar_parameters": ["Mstar", "FeH", "Age"],
    },

    # Appendix: Model parameters for every sample (references variables.tex)
    "appendix_parameter_table": {
        "function": "make_appendix_parameter_table",
        "run": "paper_bounds",
        "tier1_dirs": ["mtrue", "qtrue"],
        "tier2_types": ["allstars", "Mstar", "FeH", "Act"],
    },

    # Discussion: Three-parameter tables over the Miyazaki et al. (2023) cold-Jupiter
    #             region (references variables.tex)
    "three_param_tables_Miyazaki": {
        "function": "make_three_parameter_tables",
        "run": "stellar3params_Miyazaki",
        "t1": "mtrue",
        "occurrence_model": "piecewise",
        "reordered_label": "tab:three_param_OR_reordered_Miyazaki",
        "original_label": "tab:three_param_OR_Miyazaki",
    },
    
    # Discussion: normalized CDFs of every model (columns) for every pair of
    # stellar samples (rows), saved with the catalog plots in
    # results/<tier1>/allstars/<run>/plots/<product name>.png
    "cdf_comparison": {
        "function": "plot_model_cdf_comparison",
        "models": ["sigmoid", "logG"],          # one column each
        "sample_pairs": ["Mstar", "FeH", "Act"],  # one row each: high/low
        "run": "paper_bounds",
        "tier1": "mtrue",
        # Optional settings (defaults shown):
        "labels": {},                 # legend text by sample, e.g.
                                      # {"highAct": "Young"}; others use
                                      # the config_dict.py sample titles
        "title": "{model} CDF",       # heads each column; {model} -> name
        "credible": 0.68,             # shaded central posterior interval
        "stack_bin": 0,               # fitted stack bin
        "n_grid": 500,                # mass grid points across the bounds
        "max_samples": 2000,          # posterior samples used per curve
        "xticks": None,               # None: the run's piecewise bin edges,
                                      # as on the ORD plots; or a list
        "xlabel": None,               # None: companion mass or mass ratio
        "ylabel": "Cumulative fraction",
        "legend_loc": "lower right",  # legend in each row's first panel
        "legend_fontsize": None,      # None: the ORD plots' legend size
        "panel_size": (5, 3.5),       # inches per panel
        "colors": None,               # None: C0 for high, C1 for low
        "band_alpha": 0.25,
        "dpi": 300,
    },

#    # Optional: Mass-metallicity occurrence tables
#   "two_param_tables": {
#        "function": "make_two_parameter_tables",
#        "run": "stellar2params",
#        "t1": "mtrue",
#        "use_latex_variables": False,
 #   },

}


# Names from POST_FIT_PRODUCTS to make when main() is called without
# product_names (including ``python run_post_fit_analysis.py``). Set to None
# to make every product.
#PRODUCTS_TO_MAKE = ["variables"]
PRODUCTS_TO_MAKE = None


# How each supported function receives the experiment's Tier 3 folder and,
# for the subset tables, its Tier 2 folders.
TIER3_ARGUMENTS = {
    "make_variables": "tier3_dirs",
    "make_parameter_table": "t3",
    "make_appendix_parameter_table": "t3",
    "make_two_parameter_tables": "t3",
    "make_three_parameter_tables": "t3",
    "plot_companions_by_stellar_parameter": "tier3_dirs",
    "calculate_all_delta_bics": "tier3_dirs",
}
TIER2_DIRS_FUNCTIONS = {
    "make_two_parameter_tables", "make_three_parameter_tables",
}
PRODUCT_KEYS = {"function", "run", "runs", "three_parameter_runs"}


def _selected_product_names(product_names):
    if product_names is None:
        product_names = PRODUCTS_TO_MAKE
    names = (
        list(POST_FIT_PRODUCTS) if product_names is None
        else list(product_names)
    )
    unknown = sorted(set(names) - set(POST_FIT_PRODUCTS))
    if unknown:
        raise ValueError("unknown post-fit products: {}".format(unknown))
    if not names:
        raise ValueError("product_names must select at least one product")
    return names


def _expand_tier2_types(tier2_types):
    """Mirror occurrence's expansion of "Mstar" into highMstar and lowMstar."""
    directories = []
    for tier2_type in tier2_types:
        if str(tier2_type).lower() == "allstars":
            directories.append(str(tier2_type))
        else:
            directories.extend(
                ["high{}".format(tier2_type), "low{}".format(tier2_type)]
            )
    return directories


def _run_tier3(product_name, run_name):
    try:
        configuration = resolve_run_configuration(run_name)
    except KeyError:
        raise ValueError("{} reads unknown run {!r}".format(
            product_name, run_name
        )) from None
    if len(configuration["tier3_list"]) != 1:
        raise ValueError("{} must read a run with one Tier 3 folder".format(
            product_name
        ))
    return configuration, configuration["tier3_list"][0]


def _check_subset(product_name, source, label, requested, available):
    extra = [item for item in requested if item not in available]
    if extra:
        raise ValueError("{} requests {} not in {}: {}".format(
            product_name, label, source, extra
        ))


CDF_FUNCTION = "plot_model_cdf_comparison"


def _resolve_cdf_product(product_name, spec, results_dir):
    """Resolve a grid of model CDFs for pairs of stellar samples.

    Each entry of ``sample_pairs`` (e.g. ``"Mstar"``) becomes a row holding
    its high and low samples, labeled with their config_dict.py titles unless
    ``labels`` overrides them. Every sample must have a saved chain for every
    model; the chain files are returned with the folders so they are checked
    before anything is made. The figure is saved with the catalog plots, so
    the run's full-sample (allstars) folder must exist too.
    """
    reserved = sorted({"results_dir", "name", "rows", "runs"} & set(spec))
    if reserved:
        raise ValueError("{} sets {}; rows come from sample_pairs and the "
                         "product name is the figure name".format(
                             product_name, reserved))
    missing = sorted({"models", "sample_pairs", "run", "tier1"} - set(spec))
    if missing:
        raise ValueError("{} must set {}".format(product_name, missing))
    models = list(spec["models"])
    pairs = list(spec["sample_pairs"])
    if not models or not pairs:
        raise ValueError("{} must list models and sample_pairs".format(
            product_name
        ))
    run_name, tier1 = spec["run"], spec["tier1"]
    configuration, tier3 = _run_tier3(product_name, run_name)
    _check_subset(product_name, "run {!r}".format(run_name),
                  "Tier 1 folders", [tier1], configuration["tier1_list"])
    rows = [_expand_tier2_types([pair]) for pair in pairs]
    tier2_dirs = [tier2 for row in rows for tier2 in row]
    _check_subset(product_name, "run {!r}".format(run_name),
                  "Tier 2 folders", tier2_dirs, configuration["tier2_list"])
    labels = dict(spec.get("labels") or {})
    _check_subset(product_name, "its sample_pairs", "labels for",
                  list(labels), tier2_dirs)

    _check_subset(product_name, "run {!r}".format(run_name),
                  "Tier 2 folders (for saving)", ["allstars"],
                  configuration["tier2_list"])

    stack_bin = spec.get("stack_bin", 0)
    files_read = [Path(results_dir) / tier1 / "allstars" / tier3 / "plots"]
    for tier2 in tier2_dirs:
        folder = Path(results_dir) / tier1 / tier2 / tier3
        files_read.append(folder)
        files_read.extend(
            folder / "saved_chains" /
            "chains_{}_bin{}.npz".format(model, stack_bin)
            for model in models
        )
    arguments = {
        key: value for key, value in spec.items()
        if key not in {"function", "sample_pairs", "run", "tier1", "labels"}
    }
    arguments.update(
        results_dir=Path(results_dir), name=product_name,
        rows=[[{"label": labels.get(tier2, tier2_df_cuts_dict[tier2][1]),
                "t1": tier1, "t2": tier2, "t3": tier3}
               for tier2 in row] for row in rows],
    )
    return CDF_FUNCTION, arguments, files_read


def resolve_product(product_name, results_dir=RESULTS_DIR):
    """Return ``(function_name, arguments, folders_read)`` for a product.

    ``folders_read`` lists the Tier 3 result folders the product reads, so
    their existence can be checked before anything is made.
    """
    spec = dict(POST_FIT_PRODUCTS[product_name])
    function_name = spec.get("function")
    if function_name == CDF_FUNCTION:
        return _resolve_cdf_product(product_name, spec, results_dir)
    if function_name not in TIER3_ARGUMENTS:
        raise ValueError("{} uses unsupported function {!r}; supported: "
                         "{}".format(product_name, function_name,
                                     sorted(set(TIER3_ARGUMENTS) |
                                            {CDF_FUNCTION})))
    run_key = "runs" if function_name == "make_variables" else "run"
    other_key = "run" if run_key == "runs" else "runs"
    if run_key not in spec or other_key in spec:
        raise ValueError("{} must name what it reads with {!r}".format(
            product_name, run_key
        ))
    run_names = (
        list(spec["runs"]) if run_key == "runs" else [spec["run"]]
    )
    if not run_names or len(set(run_names)) != len(run_names):
        raise ValueError("{} must list distinct runs".format(product_name))
    tier3_argument = TIER3_ARGUMENTS[function_name]
    reserved = {tier3_argument, "results_dir", "three_parameter_t3"}
    if function_name in TIER2_DIRS_FUNCTIONS:
        reserved.add("tier2_dirs")
    overridden = sorted(reserved & set(spec))
    if overridden:
        raise ValueError(
            "{} sets {}, which come from its run configuration".format(
                product_name, overridden
            )
        )

    runs = [(name,) + _run_tier3(product_name, name) for name in run_names]
    arguments = {
        key: value for key, value in spec.items() if key not in PRODUCT_KEYS
    }
    arguments["results_dir"] = Path(results_dir)
    tier3s = [tier3 for _, _, tier3 in runs]
    arguments[tier3_argument] = (
        tier3s if tier3_argument == "tier3_dirs" else tier3s[0]
    )

    tier1_dirs = (
        [arguments["t1"]] if "t1" in arguments
        else list(arguments.get("tier1_dirs", ["mtrue"]))
    )
    if "t2" in arguments:
        tier2_dirs = [arguments["t2"]]
    elif "tier2_types" in arguments:
        tier2_dirs = _expand_tier2_types(arguments["tier2_types"])
    else:
        tier2_dirs = list(runs[0][1]["tier2_list"])
        if function_name in TIER2_DIRS_FUNCTIONS:
            arguments["tier2_dirs"] = tier2_dirs

    # Each run contributes the requested samples it has; together the runs
    # must cover every requested sample, and every run must contribute.
    run_label = (
        "run {!r}".format(run_names[0]) if len(runs) == 1
        else "runs {}".format(run_names)
    )
    _check_subset(product_name, run_label, "Tier 1 folders", tier1_dirs,
                  [t1 for _, c, _ in runs for t1 in c["tier1_list"]])
    _check_subset(product_name, run_label, "Tier 2 folders", tier2_dirs,
                  [t2 for _, c, _ in runs for t2 in c["tier2_list"]])
    folders_read = []
    for run_name, configuration, tier3 in runs:
        run_folders = [
            Path(results_dir) / tier1 / tier2 / tier3
            for tier1 in tier1_dirs if tier1 in configuration["tier1_list"]
            for tier2 in tier2_dirs if tier2 in configuration["tier2_list"]
        ]
        if not run_folders:
            raise ValueError("{} reads none of run {!r}'s samples".format(
                product_name, run_name
            ))
        folders_read.extend(run_folders)

    if "three_parameter_runs" in spec and function_name != "make_variables":
        raise ValueError(
            "{}: three_parameter_runs only applies to make_variables".format(
                product_name
            )
        )
    if function_name == "make_variables":
        # An empty list keeps occurrence from looking for a "stellar3params"
        # folder that this product did not ask for.
        arguments["three_parameter_t3"] = []
        for three_run in spec.get("three_parameter_runs", []):
            three_configuration, three_tier3 = _run_tier3(
                product_name, three_run
            )
            arguments["three_parameter_t3"].append(three_tier3)
            folders_read.extend(
                Path(results_dir) / tier1 / tier2 / three_tier3
                for tier1 in tier1_dirs
                if tier1 in three_configuration["tier1_list"]
                for tier2 in three_configuration["tier2_list"]
            )
    return function_name, arguments, folders_read


def _check_folders_exist(product_name, paths_read):
    missing = [str(path) for path in paths_read if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "{} reads results that do not exist yet; run them with "
            "run_occurrence.py first. Missing: {}".format(product_name, missing)
        )


def main(product_names=None, results_dir=RESULTS_DIR, dry_run=False):
    """Validate and make the selected post-fit products.

    ``product_names`` selects keys from ``POST_FIT_PRODUCTS``; when omitted,
    ``PRODUCTS_TO_MAKE`` is used, and ``None`` there means every product.
    Every selected product is checked, including that its results exist,
    before any is made. ``dry_run`` stops after those checks.
    """
    names = _selected_product_names(product_names)
    resolved = {
        name: resolve_product(name, results_dir) for name in names
    }
    for name, (_, _, folders_read) in resolved.items():
        _check_folders_exist(name, folders_read)

    print("Results: {}".format(results_dir))
    for name, (function_name, arguments, folders_read) in resolved.items():
        print("{}: {} from {} result folders".format(
            name, function_name, len(folders_read)
        ))
    if dry_run:
        return {}

    outputs = {}
    for name, (function_name, arguments, _) in resolved.items():
        outputs[name] = getattr(pfa, function_name)(**arguments)
    return outputs


if __name__ == "__main__":
    print(main())
