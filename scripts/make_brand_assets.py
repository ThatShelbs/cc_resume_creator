"""
Render Resume Taylor's brand images from their sources, so the art only ever
lives in two files: frontend/public/favicon.svg (the mark) and
docs/brand/banner.html (the banner).

    python scripts/make_brand_assets.py

Writes:
  docs/brand/resume-taylor.ico       desktop shortcut icon, 16 to 256 px
  docs/brand/banner.png              README hero (1280x400 at 2x)
  docs/brand/social-preview.png      GitHub social preview (1280x640); upload it
                                     under the repo's Settings > Social preview

Needs Playwright and Pillow (the backend[dev] extra) and drives the Microsoft
Edge or Chrome already installed, so no browser download. Run `npm install` in
frontend/ first so the banner gets its real fonts.
"""

import base64
import io
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
MARK = ROOT / "frontend" / "public" / "favicon.svg"
BANNER = ROOT / "docs" / "brand" / "banner.html"
ICO = ROOT / "docs" / "brand" / "resume-taylor.ico"
OUT = ROOT / "docs" / "brand"


def open_browser(p):
    for channel in ("msedge", "chrome"):
        try:
            return p.chromium.launch(channel=channel, headless=True)
        except Exception:
            continue
    return p.chromium.launch(headless=True)


def render_icon(browser) -> None:
    page = browser.new_page(viewport={"width": 256, "height": 256})
    uri = "data:image/svg+xml;base64," + base64.b64encode(MARK.read_bytes()).decode()
    page.set_content(f"<style>html,body{{margin:0;background:transparent}}</style><img src='{uri}' width=256 height=256>")
    page.wait_for_load_state("networkidle")
    png = page.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": 256, "height": 256})
    page.close()
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    ICO.parent.mkdir(parents=True, exist_ok=True)
    img.save(ICO, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Wrote {ICO.relative_to(ROOT)}")


def render_banner(browser, variant: str, size: tuple[int, int], scale: int, out: Path) -> None:
    page = browser.new_page(viewport={"width": size[0], "height": size[1]}, device_scale_factor=scale)
    page.goto(f"{BANNER.as_uri()}?v={variant}")
    page.wait_for_selector("body[data-ready='1']")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(300)
    page.screenshot(path=str(out))
    page.close()
    print(f"Wrote {out.relative_to(ROOT)}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = open_browser(p)
        render_icon(browser)
        render_banner(browser, "readme", (1280, 400), 2, OUT / "banner.png")
        render_banner(browser, "social", (1280, 640), 1, OUT / "social-preview.png")
        browser.close()


if __name__ == "__main__":
    main()
