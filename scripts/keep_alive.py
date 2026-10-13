"""
Opens the deployed app, wakes it if Streamlit Cloud put it to sleep, and exits non-zero if it never loads.
Run by .github/workflows/keep-alive.yml.
"""

import os
import sys

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

APP_URL = os.environ.get("APP_URL", "https://bond-term-sheet-extractor-diwsf7fvsovutxsajuanis.streamlit.app/")
WAKE_BUTTON = "Yes, get this app back up!"
LOAD_TIMEOUT_MS = 180_000
WAKE_WAIT_MS = 15_000


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(APP_URL, wait_until="domcontentloaded", timeout=60_000)
        wake = page.get_by_role("button", name=WAKE_BUTTON)
        try:
            wake.wait_for(timeout=WAKE_WAIT_MS)
        except PlaywrightTimeout:
            pass
        else:
            print("App was asleep. Waking it.")
            wake.click()
        try:
            page.frame_locator("iframe").first.locator('[data-testid="stApp"]').wait_for(timeout=LOAD_TIMEOUT_MS)
        except PlaywrightTimeout:
            print("App did not load in time.")
            browser.close()
            return 1
        print("App is up.")
        browser.close()
        return 0


if __name__ == "__main__":
    sys.exit(main())
