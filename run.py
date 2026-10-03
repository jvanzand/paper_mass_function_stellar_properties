"""Run all occurrence calculations used by this paper.

Edit ``RUN_CONFIGURATIONS`` for scientific choices and ``RUNS_TO_DO`` to
choose which of them run, or call :func:`main` from Python to select runs
and execution behavior. Paths are resolved from
this file, so launching it from another working directory is safe.
"""

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
OCCURRENCE_DIR = PROJECT_DIR.parent / "occurrence"
RESULTS_DIR = PROJECT_DIR / "results"
STAR_CATALOG = PROJECT_DIR / "data" / "derived" / "star_catalog.json"

# Machine-specific input locations live in an untracked JSON file, because the
# recoveries and posteriors are too large to keep in the repository.
LOCAL_PATHS_FILE = PROJECT_DIR / "local_paths.json"
LOCAL_PATHS_EXAMPLE = PROJECT_DIR / "local_paths.example.json"
LOCAL_PATH_KEYS = ("recoveries_dir", "posteriors_dir")

# occurrence is currently a sibling checkout rather than an installed package.
if str(OCCURRENCE_DIR.parent) not in sys.path:
    sys.path.insert(0, str(OCCURRENCE_DIR.parent))

from occurrence import post_fit_analysis as pfa  # noqa: E402
from occurrence import run as occurrence_run  # noqa: E402
from occurrence import sampling_utils as su  # noqa: E402

from config_dict import tier2_df_cuts_dict  # noqa: E402


# Each entry becomes one call to occurrence.run.run_multiple(). Keep separate
# experiments here instead of copying or commenting out call blocks.
RUN_CONFIGURATIONS = {

    "paper_bounds": {
        "tier1_list": ["mtrue", "qtrue"],
        "tier2_list": [
            "allstars", "highMstar", "lowMstar", "highFeH", "lowFeH",
            "highAct", "lowAct",
        ],
        "tier3_list": ["paper_bounds"],
        "a_edges": [0.1, 10.0],
        "m_edges": [0.4, 0.8, 1.6, 3.2, 6.4, 13.0, 26.0, 50.0],
        "model_fit_bounds": {
            "loglinear": {"a": (0.1, 10.0), "m": (2.26, 13.0)},
        },
        "run_models_list": ["piecewise", "sigmoid", "logG", "loglinear"],
        "plot_models_list": ["piecewise", "sigmoid", "logG"],

        "run_fits": True,
        "make_plots": True,
    },

    "stellar_3params": {
        "tier1_list": ["mtrue"],
        "tier2_list":['highMstarhighFeHhighAct', 'highMstarhighFeHlowAct',
                      'highMstarlowFeHhighAct', 'highMstarlowFeHlowAct',
                      'lowMstarhighFeHhighAct', 'lowMstarhighFeHlowAct',
                      'lowMstarlowFeHhighAct', 'lowMstarlowFeHlowAct'],
        "tier3_list": ["stellar_3params"],
        "a_edges": [0.1, 10.0],
        "m_edges": [0.4, 0.8, 1.6, 3.2, 6.4, 13.0, 26.0, 50.0],
        "run_models_list": ["piecewise"],
        "plot_models_list": ["piecewise"],

        "run_fits":True,
        "make_plots":True,
    },

}


# Names from RUN_CONFIGURATIONS to execute when main() is called without
# run_names (including ``python run.py``). Set to None to run every entry.
RUNS_TO_DO = ["stellar_3params"]


RUN_DEFAULTS = {
    "recoveries_mtype": "msini",
    "run_fits": True,
    "make_plots": True,
    "prepare_missing": True,
    "avg_map_only": False,
    "fill_single_nan_with_average": True,
    "run_models_list": ["piecewise"],
    "plot_models_list": ["piecewise"],
    "model_plot_style": "credible",
    "n_posterior_draws": 100,
    "plot_random_seed": 2222,
    "stack_dim": "a",
    "m_unit": "jupiter",
    "plot_occurrence": True,
    "plot_density": True,
    "plot_cumulative": True,
    "plot_corner": True,
    "plot_catalog_roi": True,
    "plot_roi_occurrence": True,
    "plot_uncorrected_occurrence_mle": True,
    "occurrence_legend_loc": "upper right",
    "completeness_type": "single",
    "plot_tier1_maps": False,
    "integration_resolution": (100, 100),
    "use_average_completeness": True,
    "piecewise_parameterization": "gp",
    "piecewise_gp_amplitude": 1.0,
    "piecewise_gp_length_scale_a": None,
    "piecewise_gp_length_scale_m": None,
    "piecewise_gp_jitter": 1e-8,
    "piecewise_gp_infer_hyperparameters": True,
    "piecewise_gp_amplitude_bounds": (0.05, 5.0),
    "piecewise_gp_length_scale_a_bounds": None,
    "piecewise_gp_length_scale_m_bounds": None,
    "max_integrated_occurrence": 1.0,
    "logg_amplitude_bounds": (1e-6, 10.0),
    "logg_sigma_bounds": None,
    "escarpment_amplitude_bounds": (1e-6, 10.0),
    "sigmoid_amplitude_bounds": (1e-6, 10.0),
    "sigmoid_width_bounds": None,
    "bpl_amplitude_bounds": (1e-6, 10.0),
    "bpl_slope_bounds": (-4.0, 4.0),
    "loglinear_amplitude_bounds": (1e-6, 10.0),
    "nwalkers": 50,
    "nsteps": 500,
    "burnin": 200,
    "random_seed": 1234,
    "parallel_fits": True,
    "parallel_mcmc": False,
}


def _catalog_sources(occurrence_dir=OCCURRENCE_DIR):
    cls_dir = Path(occurrence_dir) / "cls_files"
    return {
        "stars": cls_dir / "clsI_tab2.csv",
        "activity": cls_dir / "clsV_tab2.csv",
        "companions": cls_dir / "cls_substellar_comps.csv",
    }


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _catalog_metadata(occurrence_dir=OCCURRENCE_DIR):
    return {
        "schema_version": 1,
        "source_sha256": {
            name: _file_sha256(path)
            for name, path in _catalog_sources(occurrence_dir).items()
        },
    }


def make_star_df(occurrence_dir=OCCURRENCE_DIR):
    """Build the complete CLS stellar catalog used by the paper."""
    sources = _catalog_sources(occurrence_dir)
    cls_i = pd.read_csv(sources["stars"])
    cls_v = pd.read_csv(sources["activity"])
    combined = cls_i.merge(cls_v, on="cps_identifier", how="left")

    columns = [
        "cps_identifier", "Mstar", "Mstar_err", "feh", "feh_err",
        "logrhk", "age",
    ]
    star_df = combined[columns].copy().rename(
        columns={"cps_identifier": "star_name"}
    )
    companions = pd.read_csv(sources["companions"])

    companion_lists = []
    for star_name in star_df["star_name"]:
        rows = companions.loc[companions["cps_identifier"] == star_name]
        companion_names = (
            rows["cps_identifier"] + "_" +
            rows.groupby("cps_identifier").cumcount().astype(str)
        ).tolist()
        # The published sample intentionally excludes the spurious outer
        # companion assigned to HD 167215.
        if "167215" in star_name and companion_names:
            companion_names = companion_names[:1]
        companion_lists.append(companion_names)

    star_df["comp_list"] = companion_lists
    star_df["comp_num"] = star_df["comp_list"].map(len)
    validate_star_df(star_df)
    return star_df


def validate_star_df(star_df, sample_names=None):
    """Validate the catalog and the sample queries selected for a run."""
    required = {"star_name", "Mstar", "feh", "logrhk", "comp_list"}
    missing = required - set(star_df.columns)
    if missing:
        raise ValueError("star catalog is missing columns: {}".format(
            sorted(missing)
        ))
    if star_df.empty:
        raise ValueError("star catalog is empty")
    if star_df["star_name"].isna().any() or star_df["star_name"].duplicated().any():
        raise ValueError("star_name values must be non-null and unique")
    if star_df["Mstar"].isna().any() or (star_df["Mstar"] <= 0).any():
        raise ValueError("Mstar values must be non-null and positive")
    if not star_df["comp_list"].map(lambda value: isinstance(value, list)).all():
        raise ValueError("every comp_list value must be a list")

    sample_names = list(sample_names or [])
    unknown = sorted(set(sample_names) - set(tier2_df_cuts_dict))
    if unknown:
        raise ValueError("unknown stellar samples: {}".format(unknown))
    for name in sample_names:
        query = tier2_df_cuts_dict[name][0]["star_df_query"]
        try:
            selected = star_df.query(query) if query else star_df
        except Exception as error:
            raise ValueError(
                "invalid query for sample {!r}: {!r}".format(name, query)
            ) from error
        if selected.empty:
            raise ValueError("sample {!r} selects no stars".format(name))


def load_or_make_star_df(cache_path=STAR_CATALOG, rebuild=False):
    """Load the frozen catalog, or rebuild and cache it from the CLS tables."""
    cache_path = Path(cache_path)
    if cache_path.is_file() and not rebuild:
        with cache_path.open() as stream:
            cached = json.load(stream)
        if not isinstance(cached, dict) or "records" not in cached:
            raise ValueError(
                "star catalog cache uses an obsolete format; rebuild it with "
                "rebuild_star_catalog=True"
            )
        star_df = pd.DataFrame(
            cached["records"], columns=cached.get("columns")
        )
        validate_star_df(star_df)
        return star_df

    star_df = make_star_df()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    records = json.loads(
        star_df.to_json(orient="records", double_precision=15)
    )
    cached = _catalog_metadata()
    cached["columns"] = list(star_df.columns)
    cached["records"] = records
    with cache_path.open("w") as stream:
        json.dump(cached, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return star_df


def load_local_paths(path=LOCAL_PATHS_FILE):
    """Read this machine's input directories from ``local_paths.json``."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(
            "{} not found; copy {} to {} and set this machine's "
            "paths".format(path, LOCAL_PATHS_EXAMPLE.name, path.name)
        )
    with path.open() as stream:
        configured = json.load(stream)
    missing = [key for key in LOCAL_PATH_KEYS if not configured.get(key)]
    if missing:
        raise ValueError("{} is missing entries: {}".format(path, missing))
    return {
        key: (PROJECT_DIR / Path(configured[key]).expanduser()).resolve()
        for key in LOCAL_PATH_KEYS
    }


def _selected_run_names(run_names):
    if run_names is None:
        run_names = RUNS_TO_DO
    names = list(RUN_CONFIGURATIONS) if run_names is None else list(run_names)
    unknown = sorted(set(names) - set(RUN_CONFIGURATIONS))
    if unknown:
        raise ValueError("unknown runs: {}".format(unknown))
    if not names:
        raise ValueError("run_names must select at least one run")
    return names


def _validate_run_configuration(name, configuration):
    for edge_name in ("a_edges", "m_edges"):
        edges = configuration[edge_name]
        if len(edges) < 2 or any(
                right <= left for left, right in zip(edges, edges[1:])):
            raise ValueError(
                "{} {} must be strictly increasing".format(name, edge_name)
            )
    if RUN_DEFAULTS["burnin"] >= RUN_DEFAULTS["nsteps"]:
        raise ValueError("burnin must be smaller than nsteps")


def _print_plan(names, star_df, output_dir):
    print("Catalog: {} stars".format(len(star_df)))
    print("Results: {}".format(output_dir))
    for name in names:
        config = RUN_CONFIGURATIONS[name]
        print("{}:".format(name))
        for sample_name in config["tier2_list"]:
            query = tier2_df_cuts_dict[sample_name][0]["star_df_query"]
            count = len(star_df.query(query)) if query else len(star_df)
            print("  {}: {} stars".format(sample_name, count))


def make_post_fit_products(results_dir=RESULTS_DIR):
    """Create the currently used two-stellar-parameter summary tables."""
    return pfa.make_two_parameter_tables(
        Path(results_dir), t1="mtrue", t3="stellar2params",
        use_latex_variables=False,
    )


def main(
        run_names=None,
        validate_only=False,
        dry_run=False,
        plots_only=False,
        run_fits=None,
        make_plots=None,
        rebuild_star_catalog=False,
        make_post_fit_tables=False,
        output_dir=RESULTS_DIR,
        recoveries_dir=None,
        comp_post_dir=None):
    """Validate and execute the selected paper calculations.

    ``run_names`` selects keys from ``RUN_CONFIGURATIONS``; when omitted,
    ``RUNS_TO_DO`` is used, and ``None`` there means every run. ``plots_only``
    reuses saved chains instead of fitting. ``run_fits=True`` always reruns
    the Tier 3 fits and overwrites their saved products. Set
    ``make_plots=False`` to skip plots.
    ``dry_run`` reports expanded sample sizes and paths without creating
    results. ``validate_only`` also verifies required input directories, then
    stops. ``recoveries_dir`` and ``comp_post_dir`` default to the
    ``recoveries_dir`` and ``posteriors_dir`` entries in ``local_paths.json``.
    """
    names = _selected_run_names(run_names)
    for name in names:
        _validate_run_configuration(name, RUN_CONFIGURATIONS[name])
    selected_samples = [
        sample
        for name in names
        for sample in RUN_CONFIGURATIONS[name]["tier2_list"]
    ]
    star_df = load_or_make_star_df(rebuild=rebuild_star_catalog)
    validate_star_df(star_df, selected_samples)

    if recoveries_dir is None or comp_post_dir is None:
        local_paths = load_local_paths()
        if recoveries_dir is None:
            recoveries_dir = local_paths["recoveries_dir"]
        if comp_post_dir is None:
            comp_post_dir = local_paths["posteriors_dir"]
    recoveries_dir = Path(recoveries_dir)
    comp_post_dir = Path(comp_post_dir)
    output_dir = Path(output_dir)
    missing_inputs = [
        path for path in (recoveries_dir, comp_post_dir) if not path.is_dir()
    ]
    if missing_inputs:
        raise FileNotFoundError(
            "required input directories do not exist: {}".format(
                [str(path) for path in missing_inputs]
            )
        )

    _print_plan(names, star_df, output_dir)
    if validate_only or dry_run:
        return []

    if plots_only and run_fits is True:
        raise ValueError("plots_only=True conflicts with run_fits=True")

    results = []
    for name in names:
        arguments = dict(RUN_DEFAULTS)
        arguments.update(RUN_CONFIGURATIONS[name])
        arguments.update({
            "star_df": star_df,
            "tier2_df_cuts_dict": tier2_df_cuts_dict,
            "output_dir": output_dir,
            "recoveries_dir": recoveries_dir,
            "comp_post_dir": comp_post_dir,
            "sampling_func": su.post_sampler2,
        })
        if plots_only:
            arguments["run_fits"] = False
            arguments["make_plots"] = True
        if run_fits is not None:
            arguments["run_fits"] = run_fits
        if make_plots is not None:
            arguments["make_plots"] = make_plots
        results.extend(occurrence_run.run_multiple(**arguments))

    if make_post_fit_tables:
        make_post_fit_products(output_dir)
    return results


if __name__ == "__main__":
    print(main())
