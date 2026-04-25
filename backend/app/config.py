import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# DATASET_ROOT can be overridden via env var so the Render service can
# point at a Persistent Disk path or a sibling-checkout layout. Falls back
# to the in-repo bundled dataset.
_DEFAULT_DATASET = REPO_ROOT / "resources" / "smadex" / "Smadex_Creative_Intelligence_Dataset_FULL"
DATASET_ROOT = Path(os.environ.get("DATASET_ROOT", str(_DEFAULT_DATASET)))
ASSET_ROOT = DATASET_ROOT / "assets"

EXPECTED_ADVERTISERS = 36
EXPECTED_CAMPAIGNS = 180
EXPECTED_CREATIVES = 1080
EXPECTED_DAILY_ROWS = 192315

