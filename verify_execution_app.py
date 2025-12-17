from playwright.sync_api import sync_playwright
import time

def verify_execution():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Capture console logs
        page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

        print("Navigating to App...")
        page.goto("http://localhost:8501")

        try:
            print("Waiting for Landing Page...")
            page.wait_for_selector("input[type='text']", timeout=10000)

            page.locator("input[type='text']").first.fill("Retail Execution Test")
            page.get_by_role("button", name="Start Project").click()

            print("Waiting for Workspace...")
            page.wait_for_selector("h1:has-text('Workspace')", timeout=90000)
            print("Workspace Loaded!")

            time.sleep(10)

            # Locate Code Editor Iframe
            print("Looking for Code Editor iframe...")
            frame = None
            for f in page.frames:
                try:
                    if f.get_by_text("Run").count() > 0:
                        print("Found frame with Run button!")
                        frame = f
                        break
                except:
                    pass

            if not frame:
                print("No frame with Run button found.")
                page.screenshot(path="no_frame_run.png")
                return

            print("Clicking Run button inside frame...")
            frame.get_by_text("Run").first.click()

            print("Checking for 'Running...' or Result...")
            time.sleep(5)

            # Scroll down to see the result
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)

            content = page.content()
            if "Running..." in content:
                print("Status is 'Running...'")
                time.sleep(15)
                content = page.content()
                if "Running..." in content:
                    print("FAILURE: Still stuck on 'Running...' after 20s.")
                    page.screenshot(path="stuck_running.png")
                else:
                    print("SUCCESS: 'Running...' disappeared.")
            else:
                print("Did not catch 'Running...'. Assuming success.")
                page.screenshot(path="execution_result.png")

        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="execution_fail.png")

        browser.close()

if __name__ == "__main__":
    verify_execution()
