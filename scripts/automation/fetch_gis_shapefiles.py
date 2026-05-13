"""Fetch RRC gis_shapefiles data via Playwright. Auto-generated from P-TWIP-007 template."""
from __future__ import annotations
import argparse, logging, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rrc_mft_fetcher import fetch_from_mft

MFT_URL = "https://mft.rrc.texas.gov/link/d551fb20-442e-4b67-84fa-ac3f23ecabb4"
DEFAULT_OUTPUT_DIR = Path("data/sources/rrc/gis_shapefiles")
LOG_PATH = Path("logs/fetch_gis_shapefiles.log")

def setup_logging(log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("fetch_gis_shapefiles")
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(str(log_path), mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"))
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(sh)
    return logger

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    ap.add_argument("--no-headless", action="store_true")
    args = ap.parse_args()
    log = setup_logging(LOG_PATH)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    try:
        fetch_from_mft(MFT_URL, f"well_locations_{today}.dat", args.output_dir,
                       headless=not args.no_headless, log=log)
    except Exception as e:
        log.error(f"PIPELINE_FAILED: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
