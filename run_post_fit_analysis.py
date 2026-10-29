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

import contextlib
import io
import json
import re
import time
from pathlib import Path

from config_dict import SAMPLE_DEFINITIONS, tier2_df_cuts_dict
from run_occurrence import (
    RESULTS_DIR, load_or_make_star_df, resolve_run_configuration,
)

from occurrence import post_fit_analysis as pfa
from occurrence.convergence import format_duration

# Full return values of the latest main() call, beside the paper tables
POST_FIT_SUMMARY_NAME = "post_fit_summary.json"


# Each entry becomes one call to ``occurrence.post_fit_analysis.<function>``.
# "run" names the RUN_CONFIGURATIONS entry to read (make_variables takes a list,
# "runs", and includes each run's own samples); "model_runs" (appendix table
# only) maps a model to the run its fits come from; "three_parameter_runs" and
# "two_parameter_runs" (make_variables only) list the three- and
# two-parameter runs whose subset statistics are added to the variables file. Command names spell out the full results
# path: \McAllstarsPaperBoundsNstars for mtrue/allstars/paper_bounds, and
# \McStellarThreeParamsLowMstarLowFeHYoungNstars for the stellar3params subsets.
# plot_model_cdf_comparison products instead list "models" (columns) and
# "sample_pairs" (rows, e.g. "Mstar" for highMstar and lowMstar) from one run
# and tier1, and save to "filename" (default cdf_comparison.png) in that
# tier1's plots folder, independent of the product name.
# Every other key is passed through as a keyword argument. Table notes live
# here as "note" so they survive every regeneration of their tables.
POST_FIT_PRODUCTS = {

    # LaTeX variables for the main results, the no-GP escarpment fits, and
    # the three-parameter subsets. Each run contributes the samples it has.
    "variables": {
        "function": "make_variables",
        "runs": ["paper_bounds", "paper_bounds_noGP",
                 "Cui_comparison_discussion"],
        "three_parameter_runs": ["stellar3params", "stellar3params_Miyazaki"],
        # Mass-metallicity subsets for the two-parameter tables
        "two_parameter_runs": ["stellar2params"],
        "tier1_dirs": ["mtrue", "qtrue"],
        "tier2_types": ["allstars", "Mstar", "FeH", "Act"],
        # Samples used as-is rather than expanded into high/low pairs
        "standalone_tier2_dirs": ["Cui_cuts"],
        "stack_dim": "a",
        # Runs whose per-bin statistics follow mass ("m") instead of
        # separation, and runs whose integrated rates are quoted in percent:
        # the Cui+2026 comparison needs rates for each mass bin in percent
        "tier3_stack_dims": {"Cui_comparison_discussion": "m"},
        "percent_tier3_dirs": ["Cui_comparison_discussion"],
        # High/low sample comparisons (ratios, shifts, significances) run
        # high relative to low, except activity: old (lowAct) relative to
        # young (highAct)
        "low_first_comparisons": ["Act"],
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
        # Note on the reordered table (LaTeX), kept here so regenerating
        # the table keeps it
        "reordered_note": (
            r"Analogous to Table \ref{tab:two_param_OR_reordered} for stellar "
            r"mass, metallicity, and age. The last column indicates the ratio "
            r"between the median values of the high and low subsamples indicated "
            r"in each row. Dividing on three stellar parameters reduces the "
            r"typical number of effective companions per sample to the point "
            r"that none of the listed experiments exceed $3\sigma$ significance."
        ),
    },
    
    # Results: Integrated occurrence of the high/low mass and metallicity
    # samples from the 1D fits, with each pair's significance and median
    # ratio, in one table (references variables.tex)
    "one_param_table": {
        "function": "make_one_parameter_table",
        "run": "paper_bounds",
        "t1": "mtrue",
        "tier2_types": ["Mstar", "FeH"],
        # Table note (LaTeX), kept here so regenerating the table keeps it
        "note": (
            r"Stellar masses are given in $\Msun$ and metallicities are given in "
            r"dex, with the dividing values for each at $1.0~\Msun$ and 0.0 dex, "
            r"respectively. Occurrence rates have units of companions per star, "
            r"and are calculated using the histogram model. The last two columns "
            r"give the ratio between the median values of the listed stellar "
            r"parameter in the two samples. For metallicity, the ratios are "
            r"between linear abundances, $10^{\Delta[\text{Fe/H}]}$."
        ),
    },
    
    # Discussion: Mass-metallicity occurrence tables over all 719 stars
    # (references variables.tex; needs "two_parameter_runs" there)
    "two_param_tables": {
        "function": "make_two_parameter_tables",
        "run": "stellar2params",
        "t1": "mtrue",
        "use_latex_variables": True,
        # Note on the reordered table (LaTeX), kept here so regenerating
        # the table keeps it
        "reordered_note": (
            r"This table contains the same occurrence rates as Table "
            r"\ref{tab:two_param_OR}, reordered to aid comparison across stellar "
            r"parameters. Each row lists a fixed stellar parameter, the "
            r"occurrence rate as a function of the parameter being tested, the "
            r"statistical significance of the difference of those rates, and the "
            r"ratio of median stellar mass and metallicity for the subsample in "
            r"question."
        ),
        # Note on the original table (LaTeX)
        "original_note": (
            r"Analogous to Table \ref{tab:one_param_OR}, controlling for both "
            r"mass and metallicity. We use the same mass and metallicity "
            r"divisions at $1.0~\Msun$ and 0.0 dex, respectively."
        ),
    },


    # Main text: Companions colored by host properties over the average completeness
    "companion_plots": {
        "function": "plot_companions_by_stellar_parameter",
        "run": "paper_bounds",
        "tier1_dirs": ["mtrue"],
        "tier2_types": ["allstars"],
        "stellar_parameters": ["Mstar", "FeH", "Age"],
    },

    # Sample: stellar mass against metallicity for the full sample, with
    # marginal histograms; points are colored by mass sample and shaped by
    # metallicity sample, and dotted lines mark the dividing values. Drawn
    # from the star catalog rather than any run and saved in
    # results/paper_figures
    "stellar_scatter": {
        "function": "plot_stellar_mass_feh_scatter",
    },

    # Appendix: histograms of the full sample's stellar properties ("Mstar",
    # "FeH", and/or "Age"), drawn from the star catalog rather than any run
    # and saved in results/paper_figures; a dotted line marks the high/low
    # dividing value. The paper uses only the age histogram, since the
    # scatter plot shows mass and metallicity.
    "stellar_histograms": {
        "function": "plot_stellar_parameter_histograms",
        "stellar_parameters": ["Age"],
    },

    # Appendix: Model parameters for every sample (references variables.tex)
    "appendix_parameter_table": {
        "function": "make_appendix_parameter_table",
        "run": "paper_bounds",
        "tier1_dirs": ["mtrue", "qtrue"],
        "tier2_types": ["allstars", "Mstar", "FeH", "Act"],
        # The loglinear model is fit only for the full sample in true mass,
        # to a subset of the mass range, so its integrated occurrence is
        # not reliable
        "model_samples": {"loglinear": [("mtrue", "allstars")]},
        "omit_occurrence": ["loglinear"],
        # Its BIC covers only that subset, so it is not comparable
        "omit_bic": ["loglinear"],
        # Models fit in other runs, listed in the matching experiment's
        # rows: the escarpment is fit without GP smoothing to the full
        # samples in mass and mass ratio
        "model_runs": {"escarpment": "paper_bounds_noGP"},
        # Start the mass-ratio section on a new page, so no experiment's
        # rows are split across pages
        "tier1_page_breaks": True,
        # Names shown in the first two columns
        "tier1_labels": {"mtrue": "$M_c$", "qtrue": "$q$"},
        "sample_labels": {
            "allstars": "All Stars",
            "highMstar": r"High $M_\star$", "lowMstar": r"Low $M_\star$",
            "highFeH": "High [Fe/H]", "lowFeH": "Low [Fe/H]",
            "highAct": "Young", "lowAct": "Old",
        },
        # Table note (LaTeX), kept here so regenerating the table keeps it
        "note": (
            r"Stellar mass, metallicity, and age subsamples are divided at "
            r"$1~\Msun$, 0.0 dex, and 5.0 Gyr, respectively. Integrated "
            r"occurrence rates have units of companions per star. Lower BIC "
            r"values are preferred, and BICs can be compared only between "
            r"models fit to the same sample. We omit the integrated "
            r"occurrence rate and BIC for the log-linear "
            r"model because we fit it to only a subset of the catalog. We fit "
            r"the escarpment model in only two experiments: the full sample in "
            r"companion mass and the whole sample in mass ratio. In both cases, "
            r"we removed GP smoothing."
        ),
    },

    # Appendix: histogram ORD in every mass bin for every sample, with each
    # run's N_star, N_eff, and completeness. Unlike the other tables, its
    # values are read from the saved summary dictionaries, not variables.tex.
    "appendix_ord_table": {
        "function": "make_appendix_ord_table",
        "run": "paper_bounds",
        "tier1_dirs": ["mtrue", "qtrue"],
        "tier2_types": ["allstars", "Mstar", "FeH", "Act"],
        # No forced page break before the mass-ratio section
        "tier1_page_breaks": False,
        # A row of bin limits, with every other cell blank, opens each Tier 1
        # section (mass and mass ratio are binned differently); set False to
        # omit it. Mass limits are in Jupiter masses; mass ratio limits are
        # in percent, rounded to two significant figures
        "show_bin_limits": True,
        "bin_limit_styles": {
            "mtrue": {"unit": r"~\Mjup"},
            "qtrue": {"scale": 100, "sig_figs": 2, "unit": r"\%"},
        },
        # Names shown in the first two columns
        "tier1_labels": {"mtrue": "$M_c$", "qtrue": "$q$"},
        "sample_labels": {
            "allstars": "All Stars",
            "highMstar": r"High $M_\star$", "lowMstar": r"Low $M_\star$",
            "highFeH": "High [Fe/H]", "lowFeH": "Low [Fe/H]",
            "highAct": "Young", "lowAct": "Old",
        },
        # Table note (LaTeX), kept here so regenerating the table keeps it
        "note": (
            r"Each bin lists the posterior mode of the histogram model's "
            r"occurrence rate density (ORD) and its 68\% highest-density "
            r"interval, in companions per star per $\Delta\log a$ per "
            r"$\Delta\log$ of the mass variable. Mass bin limits are exact; "
            r"mass ratio bin limits, equal to the corresponding mass limit "
            r"divided by $1~\Msun$, have been rounded for concision. Stellar "
            r"subsamples are divided at $1~\Msun$, 0.0 dex, and 5.0 Gyr for "
            r"stellar mass, metallicity, and age, respectively. $N_\star$ is "
            r"the number of stars, $N_{\mathrm{eff}}$ the effective number "
            r"of companions, and the completeness is averaged over the "
            r"region of interest."
        ),
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
    # results/<tier1>/allstars/<run>/plots/<filename>
    "cdf_comparison_mtrue": {
        "function": "plot_model_cdf_comparison",
        "models": ["sigmoid", "logG"],          # one column each
        "sample_pairs": ["Mstar", "FeH"],  # one row each: high/low
        "run": "paper_bounds",
        "tier1": "mtrue",
        # Optional settings (defaults shown):
        "filename": "cdf_comparison.png",  # saved in the tier1 plots folder
        "row_labels": {},             # label centered above each row, by
                                      # sample pair; defaults: Stellar
                                      # Mass, Stellar Metallicity, Stellar Age
        "labels": {},                 # legend text by sample, e.g.
                                      # {"highAct": "Young"}; others use
                                      # the config_dict.py sample titles
        "title": None,                # optional column heading, e.g.
                                      # "{model} CDF"; None: untitled
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
        "model_colors": None,         # None: model colors of the ORD plots
                                      # (sigmoid blue, logG tomato, ...)
        "linestyles": ("-", "--"),    # high, low sample medians
        "band_styles": ("fill", "hatch"),  # high band shaded, low band
                                      # hatched ("outline" draws edges)
        "band_alpha": 0.3,            # opacity of filled bands
        "hatch": "++++",              # hatch pattern: dense square grid
        "hatch_alpha": 0.6,           # opacity of the hatch lines
        "hatch_linewidth": 0.6,       # width of the hatch lines
        "hatch_edge_width": 0.8,      # solid edges of hatched bands
        "significance_panel": True,   # panel above each CDF panel showing
                                      # the pointwise significance of the
                                      # difference between two samples
        "significance_method": "draws",  # "draws": median/facing 1-sigma
                                      # error of paired draw differences;
                                      # "quadrature": median difference over
                                      # both curves' errors in quadrature
        "significance_pair": (0, 1),  # positions of the two samples in each
                                      # row (first minus second): high - low
        "significance_seed": 0,       # seeds the pairing of draws
        "significance_threshold": 2,  # red dotted line at this value;
                                      # None omits it
        "significance_height": 0.35,  # its height relative to a CDF panel
        "significance_ylabel": r"$|\Delta|/\sigma$",
        "outline_style": ":",         # line style of outlined band edges
        "outline_width": 1.2,
        "dpi": 300,
    },
    "cdf_comparison_qtrue": {
        "function": "plot_model_cdf_comparison",
        "models": ["sigmoid", "logG"],          # one column each
        "sample_pairs": ["Mstar", "FeH"],  # one row each: high/low
        "run": "paper_bounds",
        "tier1": "qtrue",
        "filename": "cdf_comparison.png",
    },

}


# Names from POST_FIT_PRODUCTS to make when main() is called without
# product_names (including ``python run_post_fit_analysis.py``). Set to None
# to make every product.
PRODUCTS_TO_MAKE = None


# How each supported function receives the experiment's Tier 3 folder and,
# for the subset tables, its Tier 2 folders.
TIER3_ARGUMENTS = {
    "make_variables": "tier3_dirs",
    "make_parameter_table": "t3",
    "make_appendix_parameter_table": "t3",
    "make_appendix_ord_table": "t3",
    "make_one_parameter_table": "t3",
    "make_two_parameter_tables": "t3",
    "make_three_parameter_tables": "t3",
    "plot_companions_by_stellar_parameter": "tier3_dirs",
    "calculate_all_bics": "tier3_dirs",
}
# Functions that select each sample's stars from the catalog themselves
SAMPLE_CATALOG_FUNCTIONS = {"make_variables"}
# Plots the full sample from the star catalog; reads no results
HISTOGRAM_FUNCTIONS = {
    "plot_stellar_parameter_histograms", "plot_stellar_mass_feh_scatter",
}
TIER2_DIRS_FUNCTIONS = {
    "make_two_parameter_tables", "make_three_parameter_tables",
}
PRODUCT_KEYS = {"function", "run", "runs", "three_parameter_runs",
                "two_parameter_runs", "model_runs"}


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
# File a CDF figure is saved as, in its tier1's allstars plots folder, unless
# the product sets "filename".
CDF_DEFAULT_FILENAME = "cdf_comparison.png"
# Default row labels for CDF comparisons, by sample pair.
CDF_ROW_LABELS = {"Mstar": "Stellar Mass", "FeH": "Stellar Metallicity",
                  "Act": "Stellar Age"}


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
                         "figure is named with filename".format(
                             product_name, reserved))
    filename = Path(spec.get("filename", CDF_DEFAULT_FILENAME))
    if (filename.name != str(filename) or not filename.stem or
            filename.suffix not in {"", ".png"}):
        raise ValueError("{}: filename must be a bare .png file name, not "
                         "{!r}".format(product_name, str(filename)))
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
    row_labels = dict(spec.get("row_labels") or {})
    _check_subset(product_name, "its sample_pairs", "row labels for",
                  list(row_labels), pairs)

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
        if key not in {"function", "sample_pairs", "run", "tier1", "labels",
                       "row_labels", "filename"}
    }
    arguments.update(
        row_labels=[row_labels.get(pair, CDF_ROW_LABELS.get(pair, pair))
                    for pair in pairs],
        results_dir=Path(results_dir), name=filename.stem,
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
    if function_name in HISTOGRAM_FUNCTIONS:
        arguments = {
            key: value for key, value in spec.items() if key != "function"
        }
        arguments["results_dir"] = Path(results_dir)
        arguments["sample_catalog"] = load_or_make_star_df()
        return function_name, arguments, []
    if function_name not in TIER3_ARGUMENTS:
        raise ValueError("{} uses unsupported function {!r}; supported: "
                         "{}".format(product_name, function_name,
                                     sorted(set(TIER3_ARGUMENTS) |
                                            {CDF_FUNCTION} | HISTOGRAM_FUNCTIONS)))
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
    reserved = {tier3_argument, "results_dir", "three_parameter_t3",
                "two_parameter_t3", "sample_queries", "sample_catalog",
                "model_tier3"}
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
        tier2_dirs = _expand_tier2_types(arguments["tier2_types"]) + [
            tier2_dir for tier2_dir in arguments.get("standalone_tier2_dirs", [])
        ]
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

    if "model_runs" in spec:
        # Models whose fits come from another run, e.g. the escarpment
        # from the no-GP run; their rows join the matching experiment
        if function_name != "make_appendix_parameter_table":
            raise ValueError(
                "{}: model_runs only applies to "
                "make_appendix_parameter_table".format(product_name)
            )
        arguments["model_tier3"] = {}
        for model, model_run in spec["model_runs"].items():
            model_configuration, model_tier3 = _run_tier3(
                product_name, model_run
            )
            arguments["model_tier3"][model] = model_tier3
            folders_read.extend(
                Path(results_dir) / tier1 / tier2 / model_tier3
                for tier1 in tier1_dirs
                if tier1 in model_configuration["tier1_list"]
                for tier2 in model_configuration["tier2_list"]
                if tier2 in tier2_dirs
            )
    for key in ("three_parameter_runs", "two_parameter_runs"):
        if key in spec and function_name != "make_variables":
            raise ValueError(
                "{}: {} only applies to make_variables".format(
                    product_name, key
                )
            )
    if function_name in SAMPLE_CATALOG_FUNCTIONS:
        # Stellar properties of every sample come from the catalog and
        # sample queries the fits used.
        arguments["sample_queries"] = {
            name: query for name, (query, _) in SAMPLE_DEFINITIONS.items()
        }
        arguments["sample_catalog"] = load_or_make_star_df()
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
        arguments["two_parameter_t3"] = []
        for two_run in spec.get("two_parameter_runs", []):
            two_configuration, two_tier3 = _run_tier3(product_name, two_run)
            arguments["two_parameter_t3"].append(two_tier3)
            folders_read.extend(
                Path(results_dir) / tier1 / tier2 / two_tier3
                for tier1 in tier1_dirs
                if tier1 in two_configuration["tier1_list"]
                for tier2 in two_configuration["tier2_list"]
            )
    return function_name, arguments, folders_read


def _check_folders_exist(product_name, paths_read):
    missing = [str(path) for path in paths_read if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "{} reads results that do not exist yet; run them with "
            "run_occurrence.py first. Missing: {}".format(product_name, missing)
        )


def _output_paths(value):
    """Return every file path in a product function's return value."""
    if isinstance(value, (str, Path)):
        return [Path(value)]
    if isinstance(value, dict):
        return [path for item in value.values() for path in _output_paths(item)]
    if isinstance(value, (list, tuple)):
        return [path for item in value for path in _output_paths(item)]
    return []


def _describe_output(value, results_dir):
    """Name a product's output files relative to the results directory."""
    paths = []
    for path in _output_paths(value):
        try:
            paths.append(path.relative_to(results_dir))
        except ValueError:
            paths.append(path)
    if not paths:
        return "done"
    if len(paths) == 1:
        return str(paths[0])
    parents = {path.parent for path in paths}
    if len(parents) == 1:
        return "{} files in {}/".format(len(paths), parents.pop())
    return "{} files in {} folders".format(len(paths), len(parents))


def _variables_report(changes, previous_existed):
    """Summarize how variables.tex changed relative to the version it replaced."""
    if not previous_existed:
        return ["variables.tex: {} commands (new file)".format(
            changes["commands"]
        )]
    if not (changes["added"] or changes["removed"] or changes["changed"]):
        return ["variables.tex: unchanged ({} commands)".format(
            changes["commands"]
        )]
    lines = ["variables.tex: {} commands; {} new, {} removed, {} values "
             "changed".format(changes["commands"], len(changes["added"]),
                              len(changes["removed"]),
                              len(changes["changed"]))]
    if changes["largest"]:
        lines.append("  Largest changes:")
        lines.extend("    \\{}: {} -> {}".format(name, old, new)
                     for name, old, new in changes["largest"])
    return lines


def write_post_fit_summary(outputs, variables, warnings, path):
    """Save every product's outputs, the variables changes, and warnings."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = {"outputs": outputs, "variables_changes": variables,
               "warnings": warnings}
    with path.open("w") as stream:
        json.dump(summary, stream, indent=2, default=str)
        stream.write("\n")
    return path


def main(product_names=None, results_dir=RESULTS_DIR, dry_run=False):
    """Validate and make the selected post-fit products.

    ``product_names`` selects keys from ``POST_FIT_PRODUCTS``; when omitted,
    ``PRODUCTS_TO_MAKE`` is used, and ``None`` there means every product.
    Every selected product is checked, including that its results exist,
    before any is made. ``dry_run`` stops after those checks.

    Each finished product prints one line naming its outputs and time.
    Messages from ``occurrence`` are collected and printed together as
    warnings at the end, after a report of how variables.tex changed. The
    full return values go to ``results/paper_tables/post_fit_summary.json``.
    """
    names = _selected_product_names(product_names)
    resolved = {
        name: resolve_product(name, results_dir) for name in names
    }
    for name, (_, _, folders_read) in resolved.items():
        _check_folders_exist(name, folders_read)

    if dry_run:
        print("Results: {}".format(results_dir))
        for name, (function_name, arguments, folders_read) in resolved.items():
            print("{}: {} from {} result folders".format(
                name, function_name, len(folders_read)
            ))
        return {}

    results_dir = Path(results_dir)
    tables_dir = results_dir / pfa.PAPER_TABLES_DIRNAME
    variables_path = tables_dir / "variables.tex"
    previous_variables = (variables_path.read_text()
                          if variables_path.is_file() else None)
    variables = None
    outputs = {}
    warnings = []
    start = time.perf_counter()
    width = max(len(name) for name in resolved)
    count_width = len(str(len(resolved)))
    for index, (name, (function_name, arguments, _)) in enumerate(
            resolved.items(), 1):
        product_start = time.perf_counter()
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            outputs[name] = getattr(pfa, function_name)(**arguments)
        # Plot helpers announce every saved file; the product line names them
        warnings.extend(
            "{}: {}".format(name, re.sub(
                r"^post_fit_analysis\.[a-z_]+: ", "", line.strip()
            ))
            for line in captured.getvalue().splitlines()
            if line.strip() and "saved to" not in line
        )
        description = _describe_output(outputs[name], results_dir)
        if function_name == "make_variables":
            variables = pfa.variables_changes(
                previous_variables or "", variables_path.read_text()
            )
            description += " ({} commands)".format(variables["commands"])
        print("[{:>{}}/{}] {:<{}}  {:>8}  {}".format(
            index, count_width, len(resolved), name, width,
            format_duration(time.perf_counter() - product_start), description,
        ), flush=True)

    if variables is not None:
        print("\n".join([""] + _variables_report(
            variables, previous_variables is not None
        )))
    if warnings:
        print("\nWarnings:")
        print("\n".join("  " + warning for warning in warnings))
    summary_path = write_post_fit_summary(
        outputs, variables, warnings, tables_dir / POST_FIT_SUMMARY_NAME
    )
    print("\nMade {} products in {} ({} warning{}). Full results: {}".format(
        len(outputs), format_duration(time.perf_counter() - start),
        len(warnings), "" if len(warnings) == 1 else "s",
        summary_path.relative_to(results_dir),
    ))
    print("Next: python collect_paper_items.py")
    return outputs


if __name__ == "__main__":
    main()
