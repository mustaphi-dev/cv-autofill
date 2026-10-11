import sys


def test_runs_on_pinned_python() -> None:
    assert sys.version_info >= (3, 14)
