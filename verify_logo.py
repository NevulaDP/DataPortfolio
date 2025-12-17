from playwright.sync_api import sync_playwright

def verify_logo():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Navigating to App...")
        page.goto("http://localhost:8501")
        page.wait_for_load_state("networkidle")

        # Check Sidebar
        sidebar = page.locator('section[data-testid="stSidebar"]')
        if not sidebar.is_visible():
            print("Sidebar not found!")
            return

        # Check for Image in Sidebar
        # Streamlit images usually have class stImage or similar, but structure varies.
        # We look for an img tag.
        images = sidebar.locator("img")
        count = images.count()
        print(f"Found {count} images in sidebar.")

        if count > 0:
            # Check src of first image
            src = images.first.get_attribute("src")
            print(f"Image src: {src}")
            print("SUCCESS: Logo appears to be present in sidebar.")
        else:
            print("FAILURE: No image found in sidebar.")
            page.screenshot(path="logo_fail.png")

        browser.close()

if __name__ == "__main__":
    verify_logo()
