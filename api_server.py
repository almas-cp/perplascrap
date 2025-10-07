from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# Load cookies from file
def load_cookies():
    try:
        with open('cookies.json', 'r') as f:
            cookies = json.load(f)
        # Convert to requests-compatible format
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        return cookie_dict
    except Exception as e:
        print(f"Error loading cookies: {e}")
        return {}

@app.route('/search', methods=['POST'])
def perplexity_search():
    """
    API endpoint for Perplexity search
    
    Expected JSON body:
    {
        "query": "your search query",
        "max_results": 10,
        "max_tokens": 25000,
        "max_tokens_per_page": 2048,
        "country": "US"
    }
    """
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        if not data or 'query' not in data:
            return jsonify({'error': 'Missing required field: query'}), 400
        
        # Set defaults
        payload = {
            "safe_search": True,
            "display_server_time": True,
            "query": data['query'],
            "max_results": data.get('max_results', 10),
            "max_tokens": data.get('max_tokens', 25000),
            "max_tokens_per_page": data.get('max_tokens_per_page', 2048),
            "country": data.get('country', 'US')
        }
        
        # Load cookies
        cookies = load_cookies()
        
        # Prepare headers
        headers = {
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'referer': 'https://www.perplexity.ai/account/api/playground/search',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'x-app-apiclient': 'default',
            'x-app-apiversion': '2.18',
            'x-perplexity-request-endpoint': 'https://www.perplexity.ai/rest/pplx-api/playground/search?version=2.18&source=default',
            'x-perplexity-request-reason': 'playgroundSearch',
            'x-perplexity-request-try-number': '1'
        }
        
        # Make request to Perplexity
        url = 'https://www.perplexity.ai/rest/pplx-api/playground/search?version=2.18&source=default'
        response = requests.post(url, json=payload, headers=headers, cookies=cookies)
        
        # Return response
        return jsonify({
            'status': response.status_code,
            'data': response.json() if response.status_code == 200 else response.text
        }), response.status_code
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Perplexity API server is running'}), 200

if __name__ == '__main__':
    print("\n🚀 Perplexity API Server Starting...")
    print("📍 Endpoints:")
    print("   POST /search - Perform Perplexity search")
    print("   GET  /health - Health check")
    print("\n💡 Example request:")
    print('   curl -X POST http://localhost:5000/search -H "Content-Type: application/json" -d \'{"query": "hot wheels collection"}\'')
    print("\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
