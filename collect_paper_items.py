"""Gather every figure, table, and variables file the paper uses.

Running this module rebuilds ``paper_items/`` with the same layout as the
LaTeX project: tables and ``variables.tex`` at the top level and figures in
``Figures/``. Copy the folder's contents over the LaTeX project to update the
paper, for example::

    rsync -a paper_items/ /path/to/latex_project/

Figures come from experiment ``plots`` folders written by
``run_occurrence.py``; tables and variables come from ``results/paper_tables/``
written by ``run_post_fit_analysis.py``. Every source is checked before
anything is copied, so a collection is never left half-updated.
"""

import shutil
from pathlib import Path

from run_occurrence import PROJECT_DIR, RESULTS_DIR, resolve_run_configuration

from occurrence.post_fit_analysis import PAPER_TABLES_DIRNAME


PAPER_ITEMS_DIR = PROJECT_DIR / "paper_items"
FIGURES_DIRNAME = "Figures"

# Short labels used in figure names, keyed by the file each experiment's
# ``plots`` folder holds. A figure is named "<label>_<tier1>_<tier2>_<run>.png".
PLOT_LABELS = {
    "occurrence_ORD.png": "ORD",
    "companions_by_mstar.png": "companions_Mstar",
    "companions_by_feh.png": "companions_FeH",
    "companions_by_age.png": "companions_Age",
}


def _figures(plot, run, tier1, tier2_list):
    return [
        {"plot": plot, "run": run, "tier1": tier1, "tier2": tier2}
        for tier2 in tier2_list
    ]


# Figures the paper includes, each from one experiment's plots folder.
PAPER_FIGURES = [
    # Results: mass functions for the full sample and each stellar subset
    *_figures("occurrence_ORD.png", "paper_bounds", "mtrue", [
        "allstars", "highMstar", "lowMstar", "highFeH", "lowFeH",
        "highAct", "lowAct",
    ]),
    # Sample: companions colored by host properties
    *_figures("companions_by_mstar.png", "paper_bounds", "mtrue", ["allstars"]),
    *_figures("companions_by_feh.png", "paper_bounds", "mtrue", ["allstars"]),
    *_figures("companions_by_age.png", "paper_bounds", "mtrue", ["allstars"]),
    # Discussion: loglinear fit and mass-ratio functions
    *_figures("occurrence_ORD.png", "paper_bounds_loglinear", "mtrue",
              ["allstars"]),
    *_figures("occurrence_ORD.png", "paper_bounds", "qtrue", [
        "allstars", "highMstar", "lowMstar",
    ]),
]

# Tables and variables the paper inputs: file in results/paper_tables/ mapped
# to the name the LaTeX project uses.
PAPER_TABLES = {
    "variables.tex": "variables.tex",
    "model_params_mtrue_allstars_paper_bounds.tex": "model_params_table.tex",
    "model_params_appendix_paper_bounds.tex": "model_params_table_appendix.tex",
    "three_parameter_OR_mtrue_stellar3params.tex": "three_param_OR_table.tex",
    "three_parameter_OR_reordered_mtrue_stellar3params.tex":
        "three_param_OR_table_reordered.tex",
}


def figure_name(figure):
    """Return the uniform paper filename for a figure entry."""
    return "{}_{}_{}_{}.png".format(
        PLOT_LABELS[figure["plot"]], figure["tier1"], figure["tier2"],
        figure["run"],
    )


def _figure_source(figure, results_dir):
    """Return the plot file for a figure, checking it against its run."""
    if figure["plot"] not in PLOT_LABELS:
        raise ValueError("no label for plot {!r}; add it to PLOT_LABELS"
                         .format(figure["plot"]))
    try:
        configuration = resolve_run_configuration(figure["run"])
    except KeyError:
        raise ValueError("figure reads unknown run {!r}".format(
            figure["run"]
        )) from None
    for tier_key, tier in (("tier1_list", figure["tier1"]),
                           ("tier2_list", figure["tier2"])):
        if tier not in configuration[tier_key]:
            raise ValueError("run {!r} has no {} {!r}".format(
                figure["run"], tier_key[:-5], tier
            ))
    tier3 = configuration["tier3_list"][0]
    return (Path(results_dir) / figure["tier1"] / figure["tier2"] / tier3 /
            "plots" / figure["plot"])


def collection_plan(results_dir=RESULTS_DIR):
    """Map each destination path (relative to paper_items/) to its source."""
    plan = {}
    for figure in PAPER_FIGURES:
        destination = Path(FIGURES_DIRNAME) / figure_name(figure)
        if destination in plan:
            raise ValueError("two figures are named {}".format(destination))
        plan[destination] = _figure_source(figure, results_dir)
    tables_dir = Path(results_dir) / PAPER_TABLES_DIRNAME
    for source_name, destination_name in PAPER_TABLES.items():
        destination = Path(destination_name)
        if destination in plan:
            raise ValueError("two items are named {}".format(destination))
        plan[destination] = tables_dir / source_name
    return plan


def main(results_dir=RESULTS_DIR, paper_items_dir=PAPER_ITEMS_DIR,
         dry_run=False):
    """Rebuild ``paper_items/`` from the current results.

    The folder is emptied first so it holds exactly the current paper items.
    Nothing is removed or copied unless every source exists. ``dry_run``
    stops after that check.
    """
    plan = collection_plan(results_dir)
    missing = sorted(str(source) for source in plan.values()
                     if not source.is_file())
    if missing:
        raise FileNotFoundError(
            "{} paper item sources are missing; run run_occurrence.py and "
            "run_post_fit_analysis.py for them first:\n  {}".format(
                len(missing), "\n  ".join(missing)
            )
        )
    print("Collecting {} items into {}".format(len(plan), paper_items_dir))
    if dry_run:
        return plan

    paper_items_dir = Path(paper_items_dir)
    if paper_items_dir.name != PAPER_ITEMS_DIR.name:
        raise ValueError("refusing to empty {}; the collection folder must be "
                         "named {}".format(paper_items_dir, PAPER_ITEMS_DIR.name))
    if paper_items_dir.exists():
        shutil.rmtree(paper_items_dir)
    for destination, source in sorted(plan.items()):
        target = paper_items_dir / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        print("  {} <- {}".format(destination, source.relative_to(
            Path(results_dir)
        )))
    return {paper_items_dir / destination: source
            for destination, source in plan.items()}


if __name__ == "__main__":
    main()
