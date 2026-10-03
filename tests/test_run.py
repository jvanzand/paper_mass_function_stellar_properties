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


def test_load_local_paths_reads_both_directories(tmp_path):
    path = tmp_path / "local_paths.json"
    path.write_text(json.dumps({
        "recoveries_dir": str(tmp_path / "recoveries"),
        "posteriors_dir": str(tmp_path / "posteriors"),
    }))

    paths = run.load_local_paths(path)

    assert paths == {
        "recoveries_dir": (tmp_path / "recoveries").resolve(),
        "posteriors_dir": (tmp_path / "posteriors").resolve(),
    }


def test_load_local_paths_explains_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="local_paths.example.json"):
        run.load_local_paths(tmp_path / "local_paths.json")


def test_load_local_paths_rejects_missing_entries(tmp_path):
    path = tmp_path / "local_paths.json"
    path.write_text(json.dumps({"recoveries_dir": "/data/recoveries"}))

    with pytest.raises(ValueError, match="posteriors_dir"):
        run.load_local_paths(path)


def test_example_local_paths_lists_every_key():
    with run.LOCAL_PATHS_EXAMPLE.open() as stream:
        example = json.load(stream)
    assert set(example) == set(run.LOCAL_PATH_KEYS)
