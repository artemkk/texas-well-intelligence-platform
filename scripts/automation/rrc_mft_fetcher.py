"""Generic RRC MFT fetcher — reusable across all MFT-served sources.

Each source-specific fetch_*.py script calls this with its URL and
target filename. Generalizes the P-TWIP-005 Playwright pattern.
"""
from __future__ import annotations
import hashlib, json, logging, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path


def fetch_from_mft(
    mft_url: str,
    target_filename: str,
    output_dir: Path,
    headless: bool,
    log: logging.Logger,
    preferred_file: str | None = None,
) -> Path:
    """Navigate RRC MFT GoDrive portal, download a file.

    Args:
        mft_url: The mft.rrc.texas.gov/link/... URL
        target_filename: Base filename for saved file (before extension fix)
        output_dir: Directory to save to
        headless: Run browser headless
        log: Logger instance
        preferred_file: If set, click this specific file link on the GoDrive page
                        (e.g., 'orf850.txt'). If None, clicks the first available file.
    Returns:
        Path to the downloaded file
    """
    from playwright.sync_api import sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / target_filename

    log.info(f"Fetching from {mft_url}")
    log.info(f"Headless: {headless}, target: {out_file}")

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=headless)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        log.info("Navigating to MFT portal...")
        page.goto(mft_url, wait_until="networkidle", timeout=90000)
        log.info(f"Page loaded. Title: {page.title()}")

        # List available files
        links = page.query_selector_all("a")
        file_links = []
        for link in links:
            try:
                text = (link.inner_text() or "").strip()
                if text and text not in ("/ (Home)", "") and not text.startswith("/"):
                    file_links.append(text)
                    log.debug(f"  File: '{text}'")
            except Exception:
                continue

        if not file_links:
            html_path = output_dir / "mft_page_debug.html"
            html_path.write_text(page.content(), encoding="utf-8")
            log.error(f"PIPELINE_FAILED: no file links found. Page saved to {html_path}")
            browser.close()
            sys.exit(1)

        # Determine which file to download
        if preferred_file:
            targets = [preferred_file]
        else:
            # Prefer .txt over .ebc, uncompressed over .gz
            txt_files = [f for f in file_links if f.endswith('.txt')]
            gz_files = [f for f in file_links if f.endswith('.txt.gz')]
            shp_files = [f for f in file_links if f.endswith('.zip') or f.endswith('.shp')]
            targets = txt_files + gz_files + shp_files + file_links

        download_triggered = False
        for target in targets:
            link = page.query_selector(f"a:has-text('{target}')")
            if not link:
                continue
            log.info(f"Clicking file link: '{target}'")
            try:
                with page.expect_download(timeout=120000) as dl_info:
                    link.click()
                download = dl_info.value
                download.save_as(str(out_file))
                download_triggered = True
                log.info(f"Download captured: '{target}'")
                break
            except Exception as e:
                log.warning(f"  Click didn't trigger download: {e}")
                # Try double-click
                try:
                    with page.expect_download(timeout=60000) as dl_info:
                        link.dblclick()
                    download = dl_info.value
                    download.save_as(str(out_file))
                    download_triggered = True
                    log.info(f"Download captured via double-click: '{target}'")
                    break
                except Exception as e2:
                    log.warning(f"  Double-click also failed: {e2}")

        if not download_triggered:
            html_path = output_dir / "mft_page_debug.html"
            html_path.write_text(page.content(), encoding="utf-8")
            log.error(f"PIPELINE_FAILED: could not trigger download. Files seen: {file_links}")
            browser.close()
            sys.exit(1)

        browser.close()

    # Validate
    if not out_file.exists() or out_file.stat().st_size < 100:
        log.error(f"PIPELINE_FAILED: downloaded file missing or tiny")
        sys.exit(1)

    sz = out_file.stat().st_size
    log.info(f"Downloaded: {sz:,} bytes ({sz/1024/1024:.1f} MB)")

    # Check for HTML error
    with open(out_file, "rb") as f:
        magic = f.read(10)
    if b"<html" in magic.lower() or b"<?xml" in magic:
        log.error(f"PIPELINE_FAILED: downloaded HTML not data")
        sys.exit(1)

    # Detect type and rename
    if magic[:4] == b"PK\x03\x04":
        file_type = "zip"
        final = out_file.with_suffix(".zip") if not str(out_file).endswith(".zip") else out_file
    elif magic[:2] == b"\x1f\x8b":
        file_type = "gzip"
        final = out_file.with_suffix(".gz") if not str(out_file).endswith(".gz") else out_file
    else:
        file_type = "fixed_width_text"
        final = out_file.with_suffix(".txt") if not str(out_file).endswith(".txt") else out_file

    if final != out_file:
        out_file.rename(final)
        out_file = final
        log.info(f"Renamed to {out_file.name} (type: {file_type})")

    # Hash + metadata
    sha = hashlib.sha256(out_file.read_bytes()).hexdigest()
    meta = {
        "filename": out_file.name,
        "size_bytes": sz,
        "sha256": sha,
        "download_url": mft_url,
        "download_method": f"playwright_firefox_{'headless' if headless else 'headed'}",
        "download_timestamp": datetime.now(timezone.utc).isoformat(),
        "file_type": file_type,
    }
    meta_path = output_dir / "source_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log.info(f"SHA-256: {sha[:16]}...")
    log.info(f"PIPELINE_COMPLETE: {out_file.name} ({sz:,} bytes)")
    return out_file
