from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime

from measure.config import load_app_config

# requires: playwright install
from playwright.sync_api import sync_playwright


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="", help="Screenshot name (e.g., day1). Default uses timestamp.")
    args = ap.parse_args()

    app = load_app_config()
    app.screenshots_dir.mkdir(parents=True, exist_ok=True)

    name = args.name.strip() or datetime.now().strftime("%Y-%m-%d")
    out = app.screenshots_dir / f"dashboard_{name}.png"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(app.dashboard_url, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(out), full_page=True)
        browser.close()

    print(f"Saved screenshot: {out}")


if __name__ == "__main__":
    main()
