"""Backward-compatible entry point; new work should use ``run.py``."""

from run import main, make_star_df


if __name__ == "__main__":
    print(main())
