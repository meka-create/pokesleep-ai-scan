#!/usr/bin/env python3
"""Read-only real Chromium regression for the warning-only status icon UI."""
import json
import threading
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base = f"http://127.0.0.1:{server.server_port}/index.html"
results = []
try:
    with sync_playwright() as play:
        browser = play.chromium.launch(headless=True)
        for width, height in ((375, 812), (1280, 900)):
            context = browser.new_context(viewport={"width": width, "height": height})
            status = {"state": "attention"}
            def serve_status(route):
                payload = {
                    "schemaVersion": "pokesleep-upstream-status-v1",
                    "state": status["state"],
                    "checkedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "productionCsvAllowed": False,
                    "reasonCode": "UPSTREAM_PREFLIGHT_FAILED",
                    "message": "Check upstream",
                    "details": "Check upstream"
                }
                route.fulfill(status=200, content_type="application/json; charset=utf-8",
                              body=json.dumps(payload))
            context.route("**/update-status.json*", serve_status)
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            response = page.goto(base, wait_until="networkidle", timeout=30000)
            assert response.status == 200, response.status
            page.wait_for_function("() => { const b=document.querySelector('#update-watch-button'); return b && !b.hidden && b.textContent.includes('⚠'); }")
            if page.locator("#tipsDialog").evaluate("(e) => e.open"):
                page.locator("#tipsClose").click()
            warning = page.locator("#update-watch-button")
            warning.wait_for(state="visible")
            css = warning.evaluate("""(node) => {
              const s = getComputedStyle(node);
              return {border: s.borderTopWidth, background: s.backgroundColor,
                      shadow: s.boxShadow, radius: s.borderTopLeftRadius,
                      padding: s.paddingTop, width: node.getBoundingClientRect().width};
            }""")
            assert css["border"] == "0px", css
            assert css["background"] in ("rgba(0, 0, 0, 0)", "transparent"), css
            assert css["shadow"] == "none", css
            assert css["radius"] == "0px", css
            assert css["padding"] == "0px", css
            assert css["width"] >= 30, css
            assert page.locator("#update-watch-close-bottom").count() == 0
            warning.click()
            assert page.locator("#update-watch-dialog").evaluate("(e) => e.open")
            assert page.locator("#update-watch-close").is_visible()
            page.locator("#update-watch-close").click()
            assert not page.locator("#update-watch-dialog").evaluate("(e) => e.open")
            warning.click()
            page.keyboard.press("Escape")
            assert not page.locator("#update-watch-dialog").evaluate("(e) => e.open")
            warning.click()
            status["state"] = "healthy"
            page.evaluate("window.dispatchEvent(new Event('focus'))")
            page.wait_for_function("() => document.querySelector('#update-watch-button').hidden")
            assert not page.locator("#update-watch-dialog").evaluate("(e) => e.open")
            assert not errors, errors
            results.append({"viewport": width, "visibleIconWithoutFrame": True,
                            "iconClickable": True, "topXCloses": True, "escCloses": True,
                            "healthyHidesAndCloses": True, "secondaryCloseRemoved": True,
                            "jsErrors": 0})
            print("PASS", results[-1])
            context.close()
        browser.close()
finally:
    server.shutdown()
    thread.join(timeout=5)
report = ROOT / "qa" / "warning_ui_browser_evidence.json"
report.write_text(json.dumps({"status": "PASS", "results": results}, indent=2) + "\n")
print("REAL_HTTP_CHROMIUM_WARNING_UI_PASS", len(results), "viewports")
