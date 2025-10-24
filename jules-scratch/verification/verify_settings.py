
from playwright.sync_api import sync_playwright
import time

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://127.0.0.1:5000")

    # Click the settings link
    page.click("a#view-settings-link")

    # Wait for the settings view to be visible
    page.wait_for_selector("#settings-view", state="visible")

    # Change the start URL
    page.fill("input#START_URL", "https://www.bing.com")

    # Click the save button
    page.click("button#save-settings-btn")

    time.sleep(1)

    # Take a screenshot
    page.screenshot(path="jules-scratch/verification/verification.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
