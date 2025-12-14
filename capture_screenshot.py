from playwright.sync_api import sync_playwright
import sys
import time

def run(output_file):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("http://localhost:8501", timeout=60000)
            # Wait for the main title to ensure app is loaded
            page.wait_for_selector("h1", timeout=60000)
            # Give it a couple of seconds for layout to settle (sidebar, etc)
            time.sleep(5)
            page.screenshot(path=output_file, full_page=True)
            print(f"Screenshot saved to {output_file}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "screenshot.png"
    run(output)
