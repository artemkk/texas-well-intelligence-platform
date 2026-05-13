"""Fetch RRC Well Registry (Statewide API Data, dBase format) via Playwright.

The RRC serves 256 county-level .dbf files on the GoDrive MFT portal.
This fetcher downloads ALL of them and stores in the canonical source dir.
"""
from __future__ import annotations
import argparse, hashlib, json, logging, sys, time
from datetime import datetime, timezone
from pathlib import Path

MFT_URL = "https://mft.rrc.texas.gov/link/1eb94d66-461d-4114-93f7-b4bc04a70674"
DEFAULT_OUTPUT_DIR = Path("data/sources/rrc/well_registry")
LOG_PATH = Path("logs/fetch_well_registry.log")


def setup_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("fetch_well_registry")
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(str(log_path), mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s",
                                       datefmt="%Y-%m-%dT%H:%M:%S"))
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s",
                                       datefmt="%H:%M:%S"))
    logger.addHandler(sh)
    return logger


def fetch(output_dir: Path, headless: bool, log: logging.Logger) -> list[Path]:
    from playwright.sync_api import sync_playwright

    dbf_dir = output_dir / "dbf_files"
    dbf_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"Fetching well registry from {MFT_URL}")
    log.info(f"Output dir: {dbf_dir}")

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=headless)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        log.info("Navigating to MFT portal...")
        page.goto(MFT_URL, wait_until="networkidle", timeout=90000)
        log.info(f"Page loaded. Title: {page.title()}")

        # Get all .dbf file links
        links = page.query_selector_all("a")
        dbf_links = []
        for link in links:
            try:
                text = (link.inner_text() or "").strip()
                if text.endswith(".dbf"):
                    dbf_links.append(text)
            except Exception:
                continue

        log.info(f"Found {len(dbf_links)} .dbf files to download")

        downloaded = []
        failed = []
        start = time.time()

        for i, filename in enumerate(dbf_links):
            out_path = dbf_dir / filename
            if out_path.exists() and out_path.stat().st_size > 100:
                log.debug(f"  [{i+1}/{len(dbf_links)}] {filename} — already exists, skipping")
                downloaded.append(out_path)
                continue

            link = page.query_selector(f"a:has-text('{filename}')")
            if not link:
                log.warning(f"  [{i+1}/{len(dbf_links)}] {filename} — link not found")
                failed.append(filename)
                continue

            try:
                with page.expect_download(timeout=60000) as dl_info:
                    link.click()
                download = dl_info.value
                download.save_as(str(out_path))
                downloaded.append(out_path)

                if (i + 1) % 25 == 0:
                    elapsed = time.time() - start
                    log.info(f"  HEARTBEAT: {i+1}/{len(dbf_links)} files downloaded "
                             f"({elapsed:.0f}s elapsed)")
            except Exception as e:
                log.warning(f"  [{i+1}/{len(dbf_links)}] {filename} — download failed: {e}")
                failed.append(filename)
                try:
                    page.goto(MFT_URL, wait_until="networkidle", timeout=60000)
                except Exception:
                    pass

        browser.close()

    log.info(f"Downloaded: {len(downloaded)}, Failed: {len(failed)}")
    if failed:
        log.warning(f"Failed files: {failed}")

    total_size = sum(f.stat().st_size for f in downloaded)
    all_bytes = b"".join(sorted(f.name.encode() for f in downloaded))
    manifest_hash = hashlib.sha256(all_bytes).hexdigest()

    meta = {
        "source": "RRC Statewide API Data (dBase format)",
        "download_url": MFT_URL,
        "download_method": "playwright_firefox_headless" if headless else "playwright_firefox_headed",
        "download_timestamp": datetime.now(timezone.utc).isoformat(),
        "file_count": len(downloaded),
        "failed_count": len(failed),
        "total_size_bytes": total_size,
        "manifest_hash": manifest_hash,
        "failed_files": failed,
        "record_layout_url": "https://www.rrc.texas.gov/media/bkyl5qvx/well-api-manual.pdf",
    }
    meta_path = output_dir / "source_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    log.info(f"Total size: {total_size:,} bytes ({total_size/1024/1024:.1f} MB)")
    log.info(f"PIPELINE_COMPLETE: {len(downloaded)} county .dbf files downloaded")
    return downloaded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    ap.add_argument("--no-headless", action="store_true")
    args = ap.parse_args()

    log = setup_logging(LOG_PATH)
    try:
        fetch(args.output_dir, headless=not args.no_headless, log=log)
    except Exception as e:
        log.error(f"PIPELINE_FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
