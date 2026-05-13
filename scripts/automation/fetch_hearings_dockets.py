"""Fetch RRC hearings_dockets data via Playwright. Auto-generated from P-TWIP-007 template."""
from __future__ import annotations
import argparse, logging, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rrc_mft_fetcher import fetch_from_mft

MFT_URL = "https://mft.rrc.texas.gov/link/e9af053b-28c8-49b2-ad40-bf2f10f4f21a"
DEFAULT_OUTPUT_DIR = Path("data/sources/rrc/hearings_dockets")
LOG_PATH = Path("logs/fetch_hearings_dockets.log")

def setup_logging(log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("fetch_hearings_dockets")
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
        fetch_from_mft(MFT_URL, f"hearings_{today}.dat", args.output_dir,
                       headless=not args.no_headless, log=log)
    except Exception as e:
        log.error(f"PIPELINE_FAILED: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
