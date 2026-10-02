"""Small regression suite for the paper orchestration layer."""

import json

import run


def test_catalog_and_active_samples_are_valid():
    star_df = run.make_star_df()

    run.validate_star_df(
        star_df,
        run.RUN_CONFIGURATIONS["stellar2params"]["tier2_list"],
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
