
from playwright.sync_api import sync_playwright

def verify_dashboard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('http://localhost:3000')

        # Verify Title
        print(f'Title: {page.title()}')

        # Take Screenshot
        page.screenshot(path='/home/jules/verification/dashboard.png')

        browser.close()

if __name__ == '__main__':
    verify_dashboard()
