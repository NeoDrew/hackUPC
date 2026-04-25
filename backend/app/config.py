from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = REPO_ROOT / "resources" / "smadex" / "Smadex_Creative_Intelligence_Dataset_FULL"
ASSET_ROOT = DATASET_ROOT / "assets"

EXPECTED_ADVERTISERS = 36
EXPECTED_CAMPAIGNS = 180
EXPECTED_CREATIVES = 1080
EXPECTED_DAILY_ROWS = 192315

