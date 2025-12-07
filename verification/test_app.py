from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the app (frontend port 5173)
        page.goto("http://localhost:5173")

        # Check title
        print(page.title())

        # Input sector
        page.get_by_label("Sector").fill("Retail")

        # Click Start Project
        page.get_by_role("button", name="Start Project").click()

        # Wait for workspace to load (look for "Tasks" text)
        try:
            page.wait_for_selector("text=Tasks", timeout=15000)
            print("Workspace loaded")
        except:
            print("Workspace failed to load")
            page.screenshot(path="verification/failed_load.png")
            browser.close()
            return

        # Take screenshot of workspace
        page.screenshot(path="verification/workspace.png")

        browser.close()

if __name__ == "__main__":
    run()
