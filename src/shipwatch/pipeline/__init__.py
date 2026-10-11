"""Fetch → extract → characterize → dedup → cluster → score → brief → verify."""

__all__ = ["run_brief", "run_fetch", "run_pipeline"]


def __getattr__(name: str):
    if name in __all__:
        from shipwatch.pipeline import run as _run

        return getattr(_run, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
