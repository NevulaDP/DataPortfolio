from playwright.sync_api import sync_playwright, expect
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Navigating to reproduction app...")
        page.goto("http://localhost:8505")

        page.wait_for_load_state("networkidle")
        time.sleep(2) # Wait for float to apply

        print("Taking screenshot...")
        page.screenshot(path="/home/jules/verification/reproduction.png")
        print("Screenshot saved.")

        browser.close()

if __name__ == "__main__":
    run()
