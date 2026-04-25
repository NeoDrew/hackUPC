"""Offline trainer for the fatigue classifier.

Run this when the dataset changes or the feature schema in
``app/services/fatigue.py`` is updated. Persists the fitted pipeline
+ F1-maximizing threshold to ``backend/models/fatigue_classifier_<ver>.joblib``;
the file is committed to the repo so the deployed backend boots without
training.

Usage (from the backend dir):

    uv run python scripts/train_fatigue.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Make ``app`` importable when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.datastore import init_store  # noqa: E402
from app.services import fatigue as fatigue_module  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("train_fatigue")


def main() -> int:
    log.info("loading dataset…")
    # Avoid recursive training: if the artifact already exists we rename
    # it briefly so init_store falls through to inline training, which
    # also writes a fresh file. Simpler: just call into the same code
    # path init_store does, on a fresh Datastore.
    artifact = fatigue_module.MODEL_PATH
    if artifact.exists():
        log.info("existing artifact at %s — overwriting", artifact)
        artifact.unlink()

    store = init_store()
    if store.fatigue_classifier is None:
        log.error("training failed — no classifier produced")
        return 1
    log.info(
        "saved fatigue classifier to %s (threshold=%.2f)",
        fatigue_module.MODEL_PATH,
        store.fatigue_threshold,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
