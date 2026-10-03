"""Small regression suite for the paper orchestration layer."""

import json

import pytest

import run


def test_catalog_and_active_samples_are_valid():
    star_df = run.make_star_df()
    active_run = next(iter(run.RUN_CONFIGURATIONS.values()))

    run.validate_star_df(
        star_df,
        active_run["tier2_list"],
    )
    assert len(star_df) == 719


def test_catalog_cache_preserves_lists_and_source_checksums(tmp_path):
    cache_path = tmp_path / "catalog.json"
    built = run.load_or_make_star_df(cache_path=cache_path, rebuild=True)
    loaded = run.load_or_make_star_df(cache_path=cache_path)

    assert built.equals(loaded)
    assert isinstance(loaded.iloc[0]["comp_list"], list)
    with cache_path.open() as stream:
        cached = json.load(stream)
    assert set(cached["source_sha256"]) == {"stars", "activity", "companions"}


def test_validate_only_does_not_call_occurrence_runner(monkeypatch):
    monkeypatch.setattr(
        run.occurrence_run,
        "run_multiple",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("runner called")),
    )

    assert run.main(validate_only=True) == []


def test_mcmc_configuration_keeps_samples_after_burnin():
    assert run.RUN_DEFAULTS["nsteps"] > run.RUN_DEFAULTS["burnin"]


def test_runs_to_do_selects_default_runs(monkeypatch):
    monkeypatch.setattr(run, "RUNS_TO_DO", ["stellar_3params"])
    assert run._selected_run_names(None) == ["stellar_3params"]


def test_runs_to_do_none_selects_every_run(monkeypatch):
    monkeypatch.setattr(run, "RUNS_TO_DO", None)
    assert run._selected_run_names(None) == list(run.RUN_CONFIGURATIONS)


def test_explicit_run_names_override_runs_to_do(monkeypatch):
    monkeypatch.setattr(run, "RUNS_TO_DO", ["stellar_3params"])
    assert run._selected_run_names(["paper_bounds"]) == ["paper_bounds"]


def test_runs_to_do_rejects_unknown_names(monkeypatch):
    monkeypatch.setattr(run, "RUNS_TO_DO", ["not_a_run"])
    with pytest.raises(ValueError, match="unknown runs"):
        run._selected_run_names(None)
