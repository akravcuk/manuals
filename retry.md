# Retry Pattern in Azure Functions (Python)

Cloud systems are built on the assumption that *transient failures are normal*.  
Services may return `503 Service Unavailable` or `429 Too Many Requests` due to temporary overload.  
Instead of failing fast, applications should **retry with delay**.

Official manual:
https://learn.microsoft.com/en-us/azure/architecture/patterns/retry


## Key principles (from Azure Architecture Center)
- **Retry only transient faults** (timeouts, 429, 503).
- **Limit the number of attempts** (avoid infinite loops).
- **Use delays (backoff)** between retries.
- **Ensure idempotency** — repeated calls must not create duplicates (safe for `GET`, risky for `POST`).

## Prepare
```sh
mkdir retry-pattern && cd retry-pattern

# activate python environment with Azure officialy supporter python 3.11
# func311 - is the name of the virtual environment
pyenv activate func311

# initialize functions
func init . --python
```

## Minimal Python Example (Azure Function - HTTP trigger)
```python
import time
import requests
import azure.functions as func

MAX_RETRIES = 3
DELAY = 2 # seconds

def main(req: func.HttpRequest) -> func.HttpResponse:
    url = req.params.get("url")
    if not url:
        return func.HttpResponse("Missing 'url' parameter", status_code=400)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code < 500:
                return func.HttpResponse(resp.text, status_code=resp.status_code)
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")

        if attempt < MAX_RETRIES:
            time.sleep(DELAY)

    return func.HttpResponse("Service unavailable after retries", status_code=500)
```

## Testing
```sh
# Start out service
func start
Found Python version 3.11.9 (python3).

Azure Functions Core Tools
# ...
[*] Worker process started and initialized.

Functions:

	HttpRetry:  http://localhost:7071/api/retry



# Make a request
curl http://localhost:7071/api/retry?url=https://tools-httpstatus.pickup-services.com/503

# After retries and delays
Service unavailable after retries

# The log of the service with Retry pattern implemented
[*] Executing 'Functions.HttpRetry' (Reason='This function was programmatically called via the host APIs.', Id=xxx)
[*] Host lock lease acquired by instance ID '000000000000000000000000882182DE'.
[*] Attempt 1 failed with exception: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
[*] Attempt 2 failed with exception: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
[*] Attempt 3 failed with exception: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
[*] Executed 'Functions.HttpRetry' (Succeeded, Id=xxx, Duration=6097ms)
```
