# Observability: Exemplars with OTEL + Tempo + Prometheus + Grafana

This document demonstrates how to implement an observability pipeline that connects **traces, metrics, and exemplars** across a simple Python microservice.

> **Note:** This is not a CI/CD or DevOps guide. It focuses purely on *observability architecture and data flow.*

**Main article:** https://grafana.com/docs/grafana/latest/fundamentals/exemplars/

---

## System Overview

* **Python Flask** microservice instrumented with OpenTelemetry SDK
* **OTel Collector** to receive traces and metrics
* **Grafana Tempo** for distributed tracing storage
* **Prometheus** for metric collection
* **Grafana** for visualization and correlation via exemplars

---

## 1. Flask Microservice (`app.py`)

```python
from flask import Flask
import time
import logging

# --- OpenTelemetry setup ---
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

logging.basicConfig(level=logging.INFO)

# Define service identity
resource = Resource.create({"service.name": "demo-service"})
provider = TracerProvider(resource=resource)

# Console exporter for debugging
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

# gRPC exporter to OTel Collector
otlp_exporter = OTLPSpanExporter(endpoint="localhost:4319", insecure=True)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

trace.set_tracer_provider(provider)

# --- Flask ---
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
tracer = trace.get_tracer(__name__)

@app.route("/")
def index():
    with tracer.start_as_current_span("index-span"):
        return "Hello, OTLP via Collector!"

@app.route("/slow")
def slow():
    with tracer.start_as_current_span("slow-span"):
        time.sleep(0.5)
        return "Slept 0.5s"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

---

## 2. OpenTelemetry Collector (`otelcol-config.yaml`)

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4320
      grpc:
        endpoint: 0.0.0.0:4319

connectors:
  spanmetrics:
    exemplars:
      enabled: true
    dimensions:
      - name: http.method
      - name: http.status_code
    histogram:
      explicit:
        buckets: [2ms, 4ms, 6ms, 10ms, 50ms, 100ms, 200ms, 500ms, 1s, 2s]

exporters:
  prometheus:
    endpoint: "0.0.0.0:9464"
    send_timestamps: true
    enable_open_metrics: true
  otlphttp/tempo:
    endpoint: "http://localhost:4318"
    tls:
      insecure: true
  debug:
    verbosity: detailed

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [spanmetrics, otlphttp/tempo, debug]
    metrics:
      receivers: [spanmetrics]
      exporters: [prometheus]
```

---

## 3. Grafana Tempo (`tempo.yaml`)

```yaml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        http:  # or grpc if using OTLP gRPC input

ingester:
  trace_idle_period: 10s
  max_block_bytes: 1_000_000
  max_block_duration: 5m

compactor:
  compaction:
    compaction_window: 1h

storage:
  trace:
    backend: local
    wal:
      path: ./wal
    local:
      path: ./blocks
```

---

## 4. Prometheus Configuration (`prometheus.yaml`)

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "otelcol"
    honor_labels: true
    static_configs:
      - targets: ["localhost:9464"]
    metrics_path: /metrics
```

---

## 5. Grafana Configuration

### Data Sources

**Prometheus**

* URL: `http://localhost:9090`
* Enable **Exemplars**
* Set exemplar label: `traceID`

**Tempo**

* URL: `http://localhost:3200`
* Tag mappings:

  * `service_name: {{service.name}}`
  * `span_name: {{span.name}}`

---

### Example Dashboard Query

Create a time-series panel and enable “Exemplars” display mode.
Use Prometheus as the data source with the query:

```promql
sum by (http_method, job) (
  traces_span_metrics_calls_total{span_name="GET /slow"}
)
```

Hovering over a point on the chart will reveal a trace link to Tempo.

---

## 6. Testing

Generate traffic:

```bash
# Windows PowerShell
Invoke-WebRequest http://localhost:5000/slow

# Linux/macOS
curl http://localhost:5000/slow
```

Check that exemplars are visible in Prometheus metrics output:

```bash
curl http://localhost:9464/metrics
```

Look for metrics like:

```
traces_span_metrics_duration_milliseconds_bucket{...} 0 1760611741586
# Exemplar traceID=abcd1234 spanID=ef567890
```

---

## 7. Key Concept

**Standard:**
Prometheus uses the **OpenMetrics 1.0 text format** (IETF/CNCF).
It extends the classic Prometheus exposition format to include exemplars and `_created` timestamps.

**Difference:**
Traditional Prometheus metrics provide numeric observations only.
OTEL-compatible metrics include **trace-linked exemplars**, enabling Grafana to connect metric samples with distributed traces stored in Tempo.
