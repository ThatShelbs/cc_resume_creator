"""
Capture README screenshots of a running Resume Taylor (use the fictional demo
workspace, never real data) in light and dark, plus phone-width shots, and
report any page that scrolls sideways on a phone.

    python scripts/make_demo_workspace.py --force
    python launcher.py --data-root demo_workspace --no-browser     # in another terminal
    python scripts/capture_screenshots.py

Needs `pip install playwright` (requirements-dev.txt). It drives the Microsoft
Edge (or Chrome) already installed on the machine, so no browser download.
"""

import argparse
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PHONE_ROUTES = ["/", "/projects/new", "{workspace}", "/profile", "/resume", "/evidence", "/settings", "/welcome"]


def token(page: Page) -> str:
    return page.locator('meta[name="taylor-token"]').get_attribute("content")


def projects(page: Page) -> list:
    return page.evaluate(
        """async (t) => (await fetch('/api/projects', {headers: {'X-Taylor-Token': t}})).json()""", token(page)
    )


def settle(page: Page, pdf: bool = False) -> None:
    page.wait_for_load_state("networkidle")
    if pdf:
        page.wait_for_selector(".react-pdf__Page canvas", timeout=20_000)
    page.wait_for_timeout(700)  # let enter animations finish


def open_browser(p):
    for channel in ("msedge", "chrome"):
        try:
            return p.chromium.launch(channel=channel, headless=True)
        except Exception:
            continue
    return p.chromium.launch(headless=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture Resume Taylor screenshots.")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "screenshots")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    problems = []

    with sync_playwright() as p:
        browser = open_browser(p)
        for theme in ("light", "dark"):
            ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2, color_scheme=theme)
            ctx.add_init_script(f"localStorage.setItem('taylor-theme', '{theme}')")
            page = ctx.new_page()
            page.goto(args.url + "/")
            settle(page)
            items = projects(page)
            if not items:
                sys.exit("No projects found. Point this at the demo workspace (see the docstring).")
            seeded = next((x for x in items if x["has_pdf"] and x["template"] == "modern"), items[0])
            ws = f"/projects/{seeded['id']}"

            page.screenshot(path=args.out / f"dashboard-{theme}.png")
            page.goto(args.url + ws)
            settle(page, pdf=seeded["has_pdf"])
            page.screenshot(path=args.out / f"workspace-{theme}.png")

            if theme == "light":
                page.get_by_role("tab", name="Insights").click()
                settle(page)
                page.screenshot(path=args.out / "insights-light.png")
                page.get_by_role("tab", name="Template").click()
                settle(page)
                page.screenshot(path=args.out / "templates-light.png")
                page.goto(args.url + "/projects/new")
                settle(page)
                job = (ROOT / "examples" / "in_job_example.txt").read_text(encoding="utf-8")
                page.get_by_label("Job posting text").fill(job)
                page.wait_for_timeout(900)  # company/role suggestion
                page.screenshot(path=args.out / "new-project-light.png")
                for route, name in (("/evidence", "evidence"), ("/profile", "profile"), ("/welcome", "onboarding")):
                    page.goto(args.url + route)
                    settle(page)
                    page.screenshot(path=args.out / f"{name}-light.png")
            ctx.close()

        # Phone width: screenshots plus a sideways-scroll check on every page.
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3,
                                  is_mobile=True, has_touch=True, color_scheme="light")
        ctx.add_init_script("localStorage.setItem('taylor-theme', 'light')")
        page = ctx.new_page()
        page.goto(args.url + "/")
        settle(page)
        for route in PHONE_ROUTES:
            route = route.replace("{workspace}", ws)
            page.goto(args.url + route)
            settle(page)
            width = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
            if width[0] > width[1] + 1:
                problems.append(f"{route}: page is {width[0]}px wide on a {width[1]}px screen")
            if route in ("/", ws):
                page.screenshot(path=args.out / f"mobile-{'dashboard' if route == '/' else 'workspace'}.png")
        ctx.close()
        browser.close()

    print(f"Wrote screenshots to {args.out}")
    if problems:
        print("Phone layout problems:\n  " + "\n  ".join(problems))
        sys.exit(1)
    print("Phone layout: no page scrolls sideways.")


if __name__ == "__main__":
    main()
