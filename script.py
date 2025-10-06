import asyncio
import json
import os
from playwright.async_api import async_playwright

# Cookie file path in the same directory
COOKIE_FILE = 'cookies.json'

async def save_cookies(context):
    """Save cookies to a JSON file"""
    cookies = await context.cookies()
    with open(COOKIE_FILE, 'w') as f:
        json.dump(cookies, f, indent=2)
    print(f"✓ Cookies saved to {COOKIE_FILE}")
    print(f"  Total cookies saved: {len(cookies)}")

async def load_cookies(context):
    """Load cookies from JSON file if it exists"""
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, 'r') as f:
            cookies = json.load(f)
        
        if cookies:
            await context.add_cookies(cookies)
            print(f"✓ Loaded {len(cookies)} cookies from {COOKIE_FILE}")
            return True
        else:
            print("⚠ Cookie file is empty")
            return False
    else:
        print(f"⚠ No cookie file found at {COOKIE_FILE}")
        return False

async def main():
    """Main function to demonstrate cookie save/load"""
    
    async with async_playwright() as p:
        # Launch browser in non-headless mode (graphical display)
        browser = await p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        
        # Create a new context
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        try:
            # Create a new page
            page = await context.new_page()
            
            print("\n=== Playwright Cookie Manager ===\n")
            
            # Try to load existing cookies
            cookies_loaded = await load_cookies(context)
            
            # Navigate to a website
            target_url = 'https://www.perplexity.ai/account/api/playground/search'
            print(f"\n→ Navigating to {target_url}")
            await page.goto(target_url, wait_until='networkidle')
            
            if cookies_loaded:
                print("✓ Page loaded with existing cookies")
                # Refresh to apply cookies
                await page.reload(wait_until='networkidle')
            else:
                print("✓ Page loaded (first visit - no cookies)")
            
            # Wait for user to interact with the page
            print("\n⏳ Browser is open. Interact with the page if needed.")
            print("   Press Enter in this terminal when done to save cookies...")
            
            # Keep the browser open for manual interaction
            # In a real scenario, you might do automated actions here
            await asyncio.sleep(5)  # Wait 5 seconds for demonstration
            
            # Save cookies before closing
            print("\n→ Saving cookies...")
            await save_cookies(context)
            
            print("\n✓ Done! Cookies are saved for next run.")
            print("  Run this script again to see cookies loaded automatically.\n")
            
            # Keep browser open for a few more seconds to see the result
            await asyncio.sleep(3)
            
        finally:
            # Close the browser
            await browser.close()
            print("✓ Browser closed")

if __name__ == '__main__':
    asyncio.run(main())
