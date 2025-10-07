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

async def capture_request(route, request):
    """Capture and log API requests"""
    if 'api' in request.url or 'search' in request.url:
        print(f"\n🔍 Captured Request:")
        print(f"   URL: {request.url}")
        print(f"   Method: {request.method}")
        print(f"   Headers: {json.dumps(dict(request.headers), indent=2)}")
        
        if request.post_data:
            print(f"   Body: {request.post_data}")
        
        # Save to file
        request_data = {
            'url': request.url,
            'method': request.method,
            'headers': dict(request.headers),
            'body': request.post_data
        }
        with open('captured_request.json', 'w') as f:
            json.dump(request_data, f, indent=2)
        print(f"   ✓ Saved to captured_request.json\n")
    
    # Continue the request
    await route.continue_()

async def main():
    """Main function to demonstrate cookie save/load"""
    
    async with async_playwright() as p:
        # Launch browser with anti-detection settings
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',  # Hide automation
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        # Create a new context with realistic browser fingerprint
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Upgrade-Insecure-Requests': '1'
            }
        )
        
        # Remove webdriver property to avoid detection
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        try:
            # Create a new page
            page = await context.new_page()
            
            # Enable request interception
            await page.route("**/*", capture_request)
            
            print("\n=== Playwright Cookie Manager & Request Capturer ===\n")
            
            # Try to load existing cookies
            cookies_loaded = await load_cookies(context)
            
            # Navigate to a website
            target_url = 'https://www.perplexity.ai/account/api/playground/search'
            print(f"\n→ Navigating to {target_url}")
            
            # Navigate with longer timeout for Cloudflare
            await page.goto(target_url, wait_until='domcontentloaded', timeout=60000)
            
            if cookies_loaded:
                print("✓ Page loaded with existing cookies")
                # Refresh to apply cookies
                await page.reload(wait_until='domcontentloaded', timeout=60000)
            else:
                print("✓ Page loaded (first visit - no cookies)")
            
            # Wait for Cloudflare challenge to complete
            print("⏳ Waiting for Cloudflare challenge (if any)...")
            try:
                # Wait for either the challenge to disappear or content to load
                await page.wait_for_load_state('networkidle', timeout=30000)
                print("✓ Cloudflare challenge passed!")
            except Exception as e:
                print(f"⚠ Timeout waiting for page to stabilize: {e}")
                print("  Continuing anyway...")
            
            # Wait for user to interact with the page
            print("\n⏳ Browser is open. Click the Generate button to capture the request.")
            print("   The request will be captured and saved automatically.")
            print("   Waiting for 60 seconds...")
            
            # Keep the browser open for manual interaction
            await asyncio.sleep(60)
            
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
