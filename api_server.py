from flask import Flask, request, jsonify
import json
import threading
import queue
from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table
from rich import box
import time

app = Flask(__name__)
console = Console()

# Global browser instance
browser_instance = None
context_instance = None
page_instance = None
playwright_instance = None

# Queue for handling search requests from different threads
search_queue = queue.Queue()
result_queues = {}

def init_browser():
    """Initialize browser and navigate to Perplexity playground"""
    global browser_instance, context_instance, page_instance, playwright_instance
    
    if browser_instance is None:
        console.print("[cyan]🌐 Starting Chromium browser...[/cyan]")
        
        playwright_instance = sync_playwright().start()
        browser_instance = playwright_instance.chromium.launch(
            headless=False,
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )
        
        context_instance = browser_instance.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
            }
        )
        
        # Remove webdriver property
        context_instance.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # Load cookies if available
        try:
            with open('cookies.json', 'r') as f:
                cookies = json.load(f)
            context_instance.add_cookies(cookies)
            console.print("[green]✓ Loaded cookies from file[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ No cookies file found, will use fresh session[/yellow]")
        
        # Create page and navigate to Perplexity
        page_instance = context_instance.new_page()
        console.print("[cyan]📍 Navigating to Perplexity playground...[/cyan]")
        
        try:
            page_instance.goto(
                'https://www.perplexity.ai/account/api/playground/search',
                wait_until='domcontentloaded',
                timeout=60000
            )
            page_instance.wait_for_load_state('networkidle', timeout=30000)
            console.print("[green]✓ Browser ready! Session is active.[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ Page loaded with timeout: {e}[/yellow]")
            console.print("[yellow]  Continuing anyway - you may need to login manually[/yellow]")
    
    return context_instance, page_instance

def browser_worker():
    """Worker thread that handles all browser operations"""
    global page_instance, context_instance
    
    # Initialize browser in this thread
    init_browser()
    
    while True:
        try:
            # Get search request from queue
            request_id, query, max_results, max_tokens, country = search_queue.get(timeout=1)
            
            try:
                # Prepare payload
                payload = {
                    "safe_search": True,
                    "display_server_time": True,
                    "query": query,
                    "max_results": max_results,
                    "max_tokens": max_tokens,
                    "max_tokens_per_page": 2048,
                    "country": country
                }
                
                # Make API call from within the browser context using fetch
                result_data = page_instance.evaluate("""
                    async (payload) => {
                        try {
                            const response = await fetch('https://www.perplexity.ai/rest/pplx-api/playground/search?version=2.18&source=default', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'x-app-apiclient': 'default',
                                    'x-app-apiversion': '2.18',
                                    'x-perplexity-request-reason': 'playgroundSearch',
                                    'x-perplexity-request-try-number': '1'
                                },
                                body: JSON.stringify(payload)
                            });
                            
                            const data = await response.json();
                            return {
                                status: response.status,
                                data: data
                            };
                        } catch (error) {
                            return {
                                status: 500,
                                error: error.message
                            };
                        }
                    }
                """, payload)
                
                # Put result in the corresponding result queue
                if request_id in result_queues:
                    result_queues[request_id].put(result_data)
                    
            except Exception as e:
                if request_id in result_queues:
                    result_queues[request_id].put({'status': 500, 'error': str(e)})
            
            search_queue.task_done()
            
        except queue.Empty:
            continue

def perform_search(query, max_results=10, max_tokens=25000, country="US"):
    """Queue a search request and wait for result"""
    request_id = f"{threading.get_ident()}_{time.time()}"
    result_queues[request_id] = queue.Queue()
    
    # Add search request to queue
    search_queue.put((request_id, query, max_results, max_tokens, country))
    
    # Wait for result (with timeout)
    try:
        result = result_queues[request_id].get(timeout=60)
        del result_queues[request_id]
        return result
    except queue.Empty:
        del result_queues[request_id]
        return {'status': 500, 'error': 'Request timeout'}

@app.route('/search', methods=['POST'])
def perplexity_search():
    """
    API endpoint for Perplexity search
    
    Expected JSON body:
    {
        "query": "your search query",
        "max_results": 10,
        "max_tokens": 25000,
        "country": "US"
    }
    """
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        if not data or 'query' not in data:
            return jsonify({'error': 'Missing required field: query'}), 400
        
        # Perform search using Playwright
        result = perform_search(
            query=data['query'],
            max_results=data.get('max_results', 10),
            max_tokens=data.get('max_tokens', 25000),
            country=data.get('country', 'US')
        )
        
        return jsonify(result), result.get('status', 500)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Perplexity API server is running'}), 200

def manual_search():
    """Interactive CLI for manual searches"""
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]Perplexity Manual Search[/bold cyan]\n"
        "Type your queries and get instant results!",
        border_style="cyan"
    ))
    
    while True:
        console.print("\n")
        query = Prompt.ask("[bold green]Enter search query[/bold green] (or 'quit' to exit)")
        
        if query.lower() in ['quit', 'exit', 'q']:
            console.print("[yellow]Exiting manual search mode...[/yellow]")
            break
        
        if not query.strip():
            console.print("[red]Please enter a valid query![/red]")
            continue
        
        # Show loading
        with console.status("[bold cyan]Searching...", spinner="dots"):
            try:
                # Perform search using Playwright
                result = perform_search(query)
                
                if result.get('status') == 200:
                    data = result.get('data', {})
                    results = data.get('results', [])
                    
                    console.print(f"\n[bold green]✓ Found {len(results)} results[/bold green]\n")
                    
                    # Display results in a table
                    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
                    table.add_column("#", style="dim", width=3)
                    table.add_column("Title", style="cyan", width=40)
                    table.add_column("URL", style="blue", width=50)
                    
                    for idx, result in enumerate(results[:10], 1):
                        title = result.get('title', 'N/A')[:40]
                        url = result.get('url', 'N/A')[:50]
                        table.add_row(str(idx), title, url)
                    
                    console.print(table)
                    console.print("\n[dim]Results displayed. Enter another query to search again.[/dim]")
                else:
                    console.print(f"[red]✗ Error: {result.get('status', 'Unknown')}[/red]")
                    console.print(f"[dim]{result.get('error', 'Unknown error')}[/dim]")
                    
            except Exception as e:
                console.print(f"[red]✗ Error: {str(e)}[/red]")

def start_browser_worker():
    """Start browser worker thread"""
    thread = threading.Thread(target=browser_worker, daemon=True)
    thread.start()

def start_manual_search_thread():
    """Start manual search in a separate thread"""
    thread = threading.Thread(target=manual_search, daemon=True)
    thread.start()

if __name__ == '__main__':
    console.print(Panel.fit(
        "[bold cyan]🚀 Perplexity API Server[/bold cyan]\n\n"
        "[green]📍 Endpoints:[/green]\n"
        "   POST /search - Perform Perplexity search\n"
        "   GET  /health - Health check\n\n"
        "[yellow]💡 Example request:[/yellow]\n"
        "   curl -X POST http://localhost:5000/search \\\n"
        "     -H 'Content-Type: application/json' \\\n"
        "     -d '{\"query\": \"hot wheels collection\"}'",
        border_style="cyan"
    ))
    
    # Start browser worker thread (handles all browser operations)
    console.print("\n[bold yellow]⏳ Starting browser worker thread...[/bold yellow]")
    start_browser_worker()
    
    # Wait a bit for browser to initialize
    time.sleep(3)
    console.print("\n[bold green]✓ Browser is ready! You can now make searches.[/bold green]")
    console.print("[dim]The browser window will stay open and be used for all requests.[/dim]\n")
    
    # Start manual search interface in separate thread
    start_manual_search_thread()
    
    # Start Flask server (disable Flask's default output)
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    console.print("[bold cyan]🚀 API Server running on http://localhost:5000[/bold cyan]\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
