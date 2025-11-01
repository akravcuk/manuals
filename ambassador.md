# Simple 10-minute Example of the **Ambassador** Cloud Pattern

## Microsoft Azure Reference

[https://learn.microsoft.com/en-us/azure/architecture/patterns/ambassador](https://learn.microsoft.com/en-us/azure/architecture/patterns/ambassador)

---

## Stack

* Python Flask
* Public API: [The Cat API](https://api.thecatapi.com)

---

## Purpose

[Ambassador pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/ambassador)

The **Ambassador** acts as a lightweight proxy between a microservice and internal / external APIs.
It offloads non-core responsibilities like **monitoring, retries, logging, security, or caching**,
keeping the main service clean and focused.

In this example we also expose **Prometheus metrics** for observability.

> *Note:* This is a conceptual demo — in production you’d add proper validation and error handling.

---

## Components

### 1. Main App — simple client

```python
import requests
from flask import Flask

url = "http://localhost:5001/images/latest"
port = 5000
app = Flask(__name__)

@app.route("/images/latest")
def get_images_latest():
    response = requests.get(url)
    return response.json()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port, debug=True)
```

---

### 2. Ambassador — proxy with retries & metrics

```python
import time, requests
from flask import Flask, Response
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY

url = "https://api.thecatapi.com/v1/images/search"
retry_timeout_seconds = 3
listen_port_number = 5001

app = Flask(__name__)

# Prometheus metrics
requests_total = Counter('ambassador_requests_total', 'Total requests', ['status'])
request_duration = Histogram('ambassador_request_duration_seconds', 'Request duration')
retries_total = Counter('ambassador_retries_total', 'Total retries')

@app.route("/images/latest")
def get_images_latest():
    with request_duration.time():
        for attempt in range(3):
            try:
                response = requests.get(url)
                response.raise_for_status()
                break
            except Exception as ex:
                retries_total.inc()
                if attempt == 2:
                    requests_total.labels(status='error').inc()
                    return {"error": str(ex)}, 503
                time.sleep(retry_timeout_seconds)

        data = response.json()[0]
        image_url, image_id = data["url"], data["id"]

        img_data = requests.get(image_url).content
        with open(f"images/{image_id}.jpg", "wb") as f:
            f.write(img_data)

        requests_total.labels(status='success').inc()
        return {"image_id": image_id}

@app.route("/metrics")
def metrics():
    return Response(generate_latest(REGISTRY), mimetype='text/plain')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=listen_port_number, debug=True)
```

---

## 3. Packaging — Dockerize both components

Place each app in its own folder:

```
ambassador-lab/
├── app/
│   ├── app.py
│   └── Dockerfile
└── ambassador/
    ├── ambassador.py
    └── Dockerfile
```

### `app/Dockerfile`

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY app.py .
RUN pip install flask requests
CMD ["python", "-u", "app.py"]
```

### `ambassador/Dockerfile`

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY ambassador.py .
RUN pip install flask requests prometheus_client
CMD ["python", "-u", "ambassador.py"]
```

### Build containers

```bash
docker build -t app:latest ./app
docker build -t ambassador:latest ./ambassador
```

---

## 4. Deployment — run both in one Pod (sidecar model)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ambassador-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ambassador-lab
  template:
    metadata:
      labels:
        app: ambassador-lab
    spec:
      containers:
        - name: main-app
          image: app:latest
          ports:
            - containerPort: 5000
        - name: ambassador
          image: ambassador:latest
          ports:
            - containerPort: 5001
```

---

## 6. Result

After deployment, you’ll get this flow inside one Pod:

```
+-------------------------------------------+
| POD: ambassador-lab                       |
|                                           |
|  [main-app]  :5000                        |
|       ↓                                   |
|  [ambassador] :5001 → thecatapi.com       |
|                                           |
|  + Prometheus metrics at /metrics         |
+-------------------------------------------+
```

Access:

* [http://localhost:5000/images/latest](http://localhost:5000/images/latest) Main app
* [http://localhost:5001/metrics](http://localhost:5001/metrics) Prometheus metrics
