"""Checks that post-fit products read the runs they name."""

import pytest

import run_post_fit_analysis as post_fit


def _use_products(monkeypatch, **products):
    monkeypatch.setattr(post_fit, "POST_FIT_PRODUCTS", products)


def test_variables_take_tier3_folders_from_runs(tmp_path, monkeypatch):
    _use_products(monkeypatch, variables={
        "function": "make_variables",
        "runs": ["paper_bounds"],
        "three_parameter_runs": ["stellar3params", "stellar_3params_Miyazaki"],
        "tier1_dirs": ["mtrue"],
        "tier2_types": ["allstars", "Mstar"],
    })

    function_name, arguments, folders = post_fit.resolve_product(
        "variables", tmp_path
    )

    assert function_name == "make_variables"
    assert arguments["tier3_dirs"] == ["paper_bounds"]
    assert arguments["three_parameter_t3"] == [
        "stellar3params", "stellar_3params_Miyazaki",
    ]
    assert arguments["results_dir"] == tmp_path
    assert tmp_path / "mtrue" / "highMstar" / "paper_bounds" in folders
    assert (tmp_path / "mtrue" / "lowMstarlowFeHhighAct" /
            "stellar3params") in folders
    assert (tmp_path / "mtrue" / "lowMstarlowFeHhighAct" /
            "stellar_3params_Miyazaki") in folders


def test_variables_without_three_parameter_run_skip_it(tmp_path, monkeypatch):
    _use_products(monkeypatch, variables={
        "function": "make_variables", "runs": ["paper_bounds"],
        "tier1_dirs": ["mtrue"], "tier2_types": ["allstars"],
    })
    _, arguments, _ = post_fit.resolve_product("variables", tmp_path)
    assert arguments["three_parameter_t3"] == []


def test_subset_tables_read_the_run_tier2_folders(tmp_path, monkeypatch):
    _use_products(monkeypatch, tables={
        "function": "make_two_parameter_tables",
        "run": "stellar2params",
        "t1": "mtrue",
    })

    _, arguments, folders = post_fit.resolve_product("tables", tmp_path)

    assert arguments["t3"] == "stellar2params"
    assert arguments["tier2_dirs"] == [
        "highMstarhighFeH", "highMstarlowFeH",
        "lowMstarhighFeH", "lowMstarlowFeH",
    ]
    assert len(folders) == 4


def test_products_reject_tiers_their_run_lacks(tmp_path, monkeypatch):
    _use_products(monkeypatch, table={
        "function": "make_parameter_table", "run": "stellar3params",
        "t1": "mtrue", "t2": "allstars", "models": ["logG"],
    })
    with pytest.raises(ValueError, match="allstars"):
        post_fit.resolve_product("table", tmp_path)


def test_products_cannot_set_tier3_directly(tmp_path, monkeypatch):
    _use_products(monkeypatch, table={
        "function": "make_two_parameter_tables", "run": "stellar2params",
        "t3": "stellar2params",
    })
    with pytest.raises(ValueError, match="run configuration"):
        post_fit.resolve_product("table", tmp_path)


def test_products_reject_unknown_runs(tmp_path, monkeypatch):
    _use_products(monkeypatch, table={
        "function": "make_two_parameter_tables", "run": "stellar_2params",
    })
    with pytest.raises(ValueError, match="unknown run"):
        post_fit.resolve_product("table", tmp_path)


def test_main_requires_results_before_making_anything(tmp_path, monkeypatch):
    _use_products(monkeypatch, tables={
        "function": "make_two_parameter_tables",
        "run": "stellar2params", "t1": "mtrue",
    })
    monkeypatch.setattr(
        post_fit.pfa, "make_two_parameter_tables",
        lambda **kwargs: pytest.fail("made a product without its results"),
    )
    with pytest.raises(FileNotFoundError, match="run_occurrence.py first"):
        post_fit.main(["tables"], results_dir=tmp_path)


def test_main_passes_resolved_arguments(tmp_path, monkeypatch):
    _use_products(monkeypatch, tables={
        "function": "make_two_parameter_tables",
        "run": "stellar2params", "t1": "mtrue",
        "use_latex_variables": False,
    })
    for tier2 in ("highMstarhighFeH", "highMstarlowFeH",
                  "lowMstarhighFeH", "lowMstarlowFeH"):
        (tmp_path / "mtrue" / tier2 / "stellar2params").mkdir(parents=True)
    calls = []
    monkeypatch.setattr(
        post_fit.pfa, "make_two_parameter_tables",
        lambda **kwargs: calls.append(kwargs) or "made",
    )

    outputs = post_fit.main(["tables"], results_dir=tmp_path)

    assert outputs == {"tables": "made"}
    assert calls[0]["t3"] == "stellar2params"
    assert calls[0]["use_latex_variables"] is False


def test_configured_products_resolve(tmp_path):
    for name in post_fit.POST_FIT_PRODUCTS:
        post_fit.resolve_product(name, tmp_path)
    post_fit._selected_product_names(None)


def test_variables_include_each_runs_own_samples(tmp_path, monkeypatch):
    _use_products(monkeypatch, variables={
        "function": "make_variables",
        "runs": ["paper_bounds", "paper_bounds_noGP"],
        "tier1_dirs": ["mtrue", "qtrue"],
        "tier2_types": ["allstars", "Mstar"],
    })

    _, arguments, folders = post_fit.resolve_product("variables", tmp_path)

    assert arguments["tier3_dirs"] == ["paper_bounds", "paper_bounds_noGP"]
    no_gp = sorted(folder.relative_to(tmp_path) for folder in folders
                   if folder.name == "paper_bounds_noGP")
    assert no_gp == [
        post_fit.Path("mtrue/allstars/paper_bounds_noGP"),
        post_fit.Path("qtrue/allstars/paper_bounds_noGP"),
    ]
    assert len(folders) == 2*3 + 2


def test_variables_need_every_run_to_contribute(tmp_path, monkeypatch):
    _use_products(monkeypatch, variables={
        "function": "make_variables",
        "runs": ["paper_bounds", "paper_bounds_noGP"],
        "tier1_dirs": ["mtrue"], "tier2_types": ["FeH"],
    })
    with pytest.raises(ValueError, match="none of run 'paper_bounds_noGP'"):
        post_fit.resolve_product("variables", tmp_path)


def test_variables_reject_samples_no_run_has(tmp_path, monkeypatch):
    _use_products(monkeypatch, variables={
        "function": "make_variables",
        "runs": ["paper_bounds", "paper_bounds_noGP"],
        "tier1_dirs": ["msini"], "tier2_types": ["allstars"],
    })
    with pytest.raises(ValueError, match="msini"):
        post_fit.resolve_product("variables", tmp_path)


def test_variables_use_runs_and_tables_use_run(tmp_path, monkeypatch):
    _use_products(monkeypatch,
                  variables={"function": "make_variables",
                             "run": "paper_bounds"},
                  table={"function": "make_two_parameter_tables",
                         "runs": ["stellar2params"]})
    for name in ("variables", "table"):
        with pytest.raises(ValueError, match="must name what it reads"):
            post_fit.resolve_product(name, tmp_path)
