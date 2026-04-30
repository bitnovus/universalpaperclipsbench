from pathlib import Path


def prestige():
    """Return an Inspect task for the local Harbor Universal Paperclips dataset."""
    try:
        from inspect_harbor import harbor
    except ImportError as exc:
        raise RuntimeError(
            "inspect_harbor is required for the Inspect compatibility wrapper. "
            "Install it with `pip install inspect-harbor`."
        ) from exc

    dataset = Path(__file__).resolve().parents[2] / "datasets" / "universal-paperclips"
    return harbor(path=str(dataset))

