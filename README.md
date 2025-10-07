# Perplexity API Server for n8n

A Flask-based API server that wraps Perplexity's search API for use with n8n workflows.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Capture cookies (first time only):
```bash
python script.py
```
This will open a browser, load Perplexity, and save your authenticated cookies.

3. Start the API server:
```bash
python api_server.py
```

The server will run on `http://localhost:5000`

## API Endpoints

### POST /search
Perform a Perplexity search query.

**Request Body:**
```json
{
  "query": "your search query",
  "max_results": 10,
  "max_tokens": 25000,
  "max_tokens_per_page": 2048,
  "country": "US"
}
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "results": [
      {
        "title": "...",
        "url": "...",
        "snippet": "...",
        "date": "...",
        "last_updated": "..."
      }
    ]
  }
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "message": "Perplexity API server is running"
}
```

## Usage with n8n

1. Use the **HTTP Request** node in n8n
2. Set method to **POST**
3. Set URL to `http://localhost:5000/search`
4. Set body to JSON:
```json
{
  "query": "{{ $json.query }}",
  "max_results": 10,
  "country": "US"
}
```

## Example cURL Request

```bash
curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "hot wheels collection", "max_results": 10}'
```

## Files

- `api_server.py` - Flask API server
- `script.py` - Cookie capture script (Playwright)
- `cookies.json` - Saved authentication cookies
- `requirements.txt` - Python dependencies

## Notes

- Cookies expire after some time. Re-run `script.py` to refresh them.
- The server uses cookies from `cookies.json` for authentication.
- Make sure Perplexity account is logged in when capturing cookies.
