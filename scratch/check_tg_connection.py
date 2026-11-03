import urllib.request
import urllib.error

urls = [
    "http://localhost:14240",
    "http://localhost:9000/echo",
    "127.0.0.1:14240"
]

print("=== PINGING LOCAL TIGERGRAPH ENDPOINTS ===")
for url in ["http://localhost:14240", "http://localhost:9000"]:
    try:
        req = urllib.request.urlopen(url, timeout=2)
        print(f"Endpoint {url}: SUCCESS (Status {req.getcode()})")
    except urllib.error.URLError as e:
        print(f"Endpoint {url}: UNREACHABLE ({e.reason})")
    except Exception as e:
        print(f"Endpoint {url}: FAILED ({e})")
