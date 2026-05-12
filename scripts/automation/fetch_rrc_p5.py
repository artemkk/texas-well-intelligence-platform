"""Fetch RRC P-5 Organization data ZIP via Playwright (Firefox headless).

Navigates the RRC MFT portal, captures the download event, saves the
ZIP with provenance metadata. Generalizable pattern for all MFT-served
RRC sources.

Usage:
    python scripts/automation/fetch_rrc_p5.py
    python scripts/automation/fetch_rrc_p5.py --no-headless   # debug mode
"""
from __future__ import annotations
import argparse, hashlib, json, logging, os, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path

MFT_URL = "https://mft.rrc.texas.gov/link/04652169-eed6-4396-9019-2e270e790f6c"
DEFAULT_OUTPUT_DIR = Path("data/sources/rrc/og_operator_data")
LOG_PATH = Path("logs/fetch_rrc_p5.log")


def setup_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("fetch_rrc_p5")
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


def fetch(output_dir: Path, headless: bool, log: logging.Logger) -> Path:
    from playwright.sync_api import sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_file = output_dir / f"p5_organization_{today}.zip"

    log.info(f"Starting P-5 fetch from {MFT_URL}")
    log.info(f"Headless: {headless}")
    log.info(f"Target: {out_file}")

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=headless)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        log.info("Navigating to MFT portal...")
        page.goto(MFT_URL, wait_until="networkidle", timeout=60000)
        log.info(f"Page loaded. Title: {page.title()}")

        # The MFT GoDrive page lists files as <a href="#"> links.
        # Target: orf850.txt (ASCII format, uncompressed) or orf850.txt.gz
        # Click the file name link to trigger download.
        target_files = ["orf850.txt", "orf850.txt.gz", "orf850.ebc", "orf850.ebc.gz"]
        download_triggered = False

        links = page.query_selector_all("a")
        for link in links:
            try:
                text = (link.inner_text() or "").strip()
            except Exception:
                continue
            log.debug(f"  Link found: '{text}'")

        # Strategy: click the orf850.txt link (ASCII, uncompressed preferred)
        for target in target_files:
            log.info(f"Looking for file link: '{target}'")
            link = page.query_selector(f"a:has-text('{target}')")
            if not link:
                log.info(f"  Not found, trying next")
                continue
            log.info(f"  Found. Clicking to trigger download...")
            try:
                with page.expect_download(timeout=60000) as dl_info:
                    link.click()
                download = dl_info.value
                download.save_as(str(out_file))
                download_triggered = True
                log.info(f"Download captured: '{target}' -> {out_file}")
                break
            except Exception as e:
                log.warning(f"  Click on '{target}' didn't trigger download: {e}")

        # Fallback: double-click (some GoDrive UIs require it)
        if not download_triggered:
            for target in target_files:
                link = page.query_selector(f"a:has-text('{target}')")
                if not link:
                    continue
                log.info(f"Trying double-click on '{target}'...")
                try:
                    with page.expect_download(timeout=60000) as dl_info:
                        link.dblclick()
                    download = dl_info.value
                    download.save_as(str(out_file))
                    download_triggered = True
                    log.info(f"Download captured via double-click: '{target}'")
                    break
                except Exception as e:
                    log.warning(f"  Double-click didn't trigger download: {e}")

        if not download_triggered:
            # Save page HTML for diagnosis
            html_path = output_dir / "mft_page_debug.html"
            html_path.write_text(page.content(), encoding="utf-8")
            log.error(f"PIPELINE_FAILED: could not trigger download. Page HTML saved to {html_path}")
            browser.close()
            sys.exit(1)

        browser.close()

    # Verify the download
    if not out_file.exists():
        log.error(f"PIPELINE_FAILED: download file does not exist at {out_file}")
        sys.exit(1)

    sz = out_file.stat().st_size
    log.info(f"Downloaded file size: {sz:,} bytes ({sz/1024/1024:.1f} MB)")

    if sz < 10000:
        content = out_file.read_bytes()[:200]
        if b"<html" in content.lower() or b"<?xml" in content:
            log.error(f"PIPELINE_FAILED: downloaded file is HTML, not data. First bytes: {content[:100]}")
            sys.exit(1)

    # Detect file type: ZIP or raw fixed-width text
    with open(out_file, "rb") as f:
        magic = f.read(4)

    if magic == b"PK\x03\x04":
        file_type = "zip"
        try:
            with zipfile.ZipFile(str(out_file)) as zf:
                names = zf.namelist()
                log.info(f"ZIP contains {len(names)} files: {names}")
        except zipfile.BadZipFile:
            log.error(f"PIPELINE_FAILED: file is corrupt ZIP")
            sys.exit(1)
    elif magic[:2] in (b"1T", b"A "):
        # RRC fixed-width text file (starts with record type identifier)
        file_type = "fixed_width_text"
        # Rename to .txt extension
        txt_path = out_file.with_suffix(".txt")
        out_file.rename(txt_path)
        out_file = txt_path
        log.info(f"File is raw fixed-width text (RRC format). Renamed to {out_file.name}")
        names = [out_file.name]
    else:
        # Check for gzip
        if magic[:2] == b"\x1f\x8b":
            file_type = "gzip"
            gz_path = out_file.with_suffix(".txt.gz")
            out_file.rename(gz_path)
            out_file = gz_path
            log.info(f"File is gzip-compressed. Renamed to {out_file.name}")
            names = [out_file.name]
        else:
            log.error(f"PIPELINE_FAILED: unknown file type. Magic bytes: {magic}")
            sys.exit(1)

    # Compute hash and write metadata
    sha = hashlib.sha256(out_file.read_bytes()).hexdigest()
    meta = {
        "filename": out_file.name,
        "size_bytes": sz,
        "sha256": sha,
        "download_url": MFT_URL,
        "download_method": "playwright_firefox_headless" if headless else "playwright_firefox_headed",
        "download_timestamp": datetime.now(timezone.utc).isoformat(),
        "record_layout_url": "https://www.rrc.texas.gov/media/jtqfynn3/ora001_p5_manual_october-2014.pdf",
        "file_type": file_type,
        "record_length": 350,
        "contents": names,
    }
    meta_path = output_dir / "source_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log.info(f"Source metadata written to {meta_path}")
    log.info(f"SHA-256: {sha}")
    log.info(f"PIPELINE_COMPLETE: {out_file.name} ({sz:,} bytes)")
    return out_file


def main():
    ap = argparse.ArgumentParser(description="Fetch RRC P-5 Organization data via Playwright")
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    ap.add_argument("--no-headless", action="store_true", help="Run browser visibly for debugging")
    args = ap.parse_args()

    log = setup_logging(LOG_PATH)
    try:
        fetch(args.output_dir, headless=not args.no_headless, log=log)
    except Exception as e:
        log.error(f"PIPELINE_FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
