from playwright.sync_api import sync_playwright, expect
import time

def verify_person_list():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate
        print("Waiting for app to start...")
        page.goto("http://localhost:8501", timeout=5000)
        page.wait_for_selector("text=人物一覧", timeout=10000)

        # Take debug screenshot of what we see
        page.screenshot(path="debug_page_load.png")

        # Check if table headers are visible
        # Note: Streamlit buttons inside columns might be rendered differently
        # Let's look for text "名前" regardless of role first
        if page.get_by_text("名前").count() > 0:
            print("Found '名前'")
        else:
            print("Did not find '名前'")

        # Try to find the button specifically
        # Streamlit buttons often have exact text match
        # If sort arrow is present (e.g., "名前 ▲"), strict "name" match might fail if we don't use regex or exact string
        # In my code: f"{label}{arrow}" -> "名前" or "名前 ▲"
        # So exact match "名前" might fail if arrow is there.
        # But initially arrow is empty string unless sorted. Default sort is "last_name", "asc".
        # So "名前" might have " ▲" appended if it matches `plist_sort_key`.
        # Code: `st.session_state["plist_sort_key"] = "last_name"`
        # So arrow will be " ▲" (asc).
        # Thus the button text is "名前 ▲".

        # Let's try matching partial text or regex
        expect(page.get_by_role("button", name="名前")).to_be_visible()

        page.screenshot(path="verification_table.png")

        browser.close()

if __name__ == "__main__":
    verify_person_list()
