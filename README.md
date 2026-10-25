# DA3408 Assignment 4: Observability for a CPU Image-Captioning App

Video Link:- https://drive.google.com/drive/folders/1xG34JySMbmY-ZX08DMcJCcz_XmXFo1M0

A Streamlit app that captions images on CPU with `Salesforce/blip-image-captioning-base`, instrumented with `prometheus_client`. Prometheus scrapes the app and `node_exporter`, evaluates recording and alert rules, and sends alerts to Alertmanager. Grafana visualises application and system metrics side by side.

```
Browser ──► Streamlit :8501
                │
                ▼
        app /metrics :8000 ◄──┐
                              ├── Prometheus :9090 ──► Alertmanager :9093
  node_exporter /metrics :9100 ◄┘        │
                                         ▼
                                  Grafana :3000 (Docker)
```

## Repository layout

| Path | Purpose |
|---|---|
| `app/app.py` | Streamlit UI with Single image and Bulk ZIP modes |
| `app/model.py` | Cached BLIP load, image decode, preprocessing, inference |
| `app/metrics.py` | All metric definitions, the `/metrics` server on :8000, background RSS/CPU/session sampler |
| `app/bulk.py` | Safe ZIP handling: size caps, hidden/non-image filtering, per-file error isolation |
| `app/client.py` | Session ID and client IP extraction |
| `prometheus/prometheus.yml` | Scrape config (5 s) for the app, node_exporter, Prometheus and Alertmanager |
| `prometheus/recording_rules.yml` | Complex PromQL as recording rules, with the AI prompt used as a comment |
| `prometheus/alert_rules.yml` | App down, exporter down, high p95 latency, high error rate, high CPU, low memory |
| `grafana/dashboard.json` | Importable Grafana dashboard |
| `scripts/setup.sh` | Downloads Prometheus, Alertmanager, node_exporter into `~/monitoring` and creates the Grafana container |
| `scripts/start.sh` / `stop.sh` | Start or stop the whole stack |
| `scripts/make_zips.py` | Builds test ZIPs (10/50/100 images, a messy ZIP, an invalid ZIP) |
| `scripts/build_dashboard.py` | Regenerates `grafana/dashboard.json` |
| `scripts/calc.py` | Computes dashboard metrics by hand from raw `/metrics` values and compares with Prometheus |
| `scripts/show.sh` | Step-through of the terminal commands used in the demo video |

## Requirements

- Ubuntu 22.04+ (tested in a VirtualBox VM with 6 vCPUs and 12 GB RAM)
- Python 3.10+
- Docker (for Grafana)
- About 2 GB free disk (model weights ~1 GB)

Tested with Prometheus 3.15.0, Alertmanager 0.34.1, node_exporter 1.12.1 and Grafana Enterprise (Docker).

## Reproduce

### 1. Clone and install Python dependencies
```bash
git clone <repo-url> da3408-a4
cd da3408-a4
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Any existing venv works too; activate it before `start.sh`.

### 2. Install Prometheus, Alertmanager, node_exporter and Grafana
```bash
bash scripts/setup.sh
~/monitoring/prometheus-*/promtool check config prometheus/prometheus.yml
```
The check should report SUCCESS for the config, 11 recording rules and 6 alert rules.

### 3. Start the stack
```bash
bash scripts/start.sh
```
This starts node_exporter, Alertmanager and Prometheus in the background (logs in `logs/`), starts the Grafana container, then runs Streamlit in the foreground.

Open http://localhost:8501. The first load downloads the BLIP model (~1 GB, once only). The metrics server on :8000 starts with the first page load.

### 4. Check scraping
```bash
curl -s localhost:9090/api/v1/targets | grep -o '"job":"[^"]*"\|"health":"[^"]*"'
```
All four jobs (`caption_app`, `node`, `prometheus`, `alertmanager`) should be `up`. The same is visible at http://localhost:9090/targets.

### 5. Grafana
1. Open http://localhost:3000 and log in as `admin` / `admin`.
2. **Connections → Data sources → Add data source → Prometheus.** URL: `http://172.17.0.1:9090` (the VM as seen from inside the Docker bridge network; `localhost` would point at the container). **Save & test.**
   If the test times out: `sudo ufw allow from 172.17.0.0/16 to any port 9090`.
3. **Dashboards → New → Import**, upload `grafana/dashboard.json`, choose the Prometheus data source, **Import**.

The dashboard opens at the last 15 minutes with a 5 s refresh.

### 6. Generate traffic
```bash
python scripts/make_zips.py --images <folder-of-photos> --out test_zips
```
Without `--images`, synthetic images are generated. Then in Streamlit:
- **Single image** tab: upload a photo and click **Caption image**.
- **Bulk ZIP** tab: upload `test_zips/bulk_100.zip` and click **Caption all**.
- Upload `test_zips/dirty.zip` to exercise error handling (corrupt JPEG, text file, macOS metadata, hidden file, nested folders).

### 7. Stop
```bash
bash scripts/stop.sh
```
To wipe collected data: `rm -rf data/`.

### Accessing from a Windows host (VirtualBox NAT)
VM Settings → Network → Adapter 1 → Advanced → Port Forwarding. Forward host ports 8501, 9090, 9093 and 3000 to the same guest ports.

## Metrics

| Type | Name | Labels |
|---|---|---|
| Counter | `caption_images_processed_total` | mode, status, client_ip |
| Counter | `caption_requests_total` | mode, status, session |
| Counter | `caption_errors_total` | mode, error_type |
| Counter | `caption_zip_uploads_total` | status |
| Counter | `caption_files_skipped_total` | reason |
| Counter | `caption_upload_bytes_total` | mode |
| Counter | `caption_tokens_generated_total` | mode |
| Counter | `caption_model_loads_total` | model |
| Gauge | `caption_active_requests` | mode |
| Gauge | `caption_active_sessions` | |
| Gauge | `caption_model_loaded` | model |
| Gauge | `caption_process_rss_bytes` | |
| Gauge | `caption_process_cpu_percent` | |
| Gauge | `caption_bulk_queue_remaining` | |
| Gauge | `caption_last_batch_size` | |
| Gauge | `caption_last_success_timestamp_seconds` | mode |
| Info | `caption_app_info` | model, device, torch_threads, torch_version |
| Histogram | `caption_inference_seconds` | mode |
| Histogram | `caption_preprocess_seconds` | mode |
| Histogram | `caption_request_duration_seconds` | mode |
| Histogram | `caption_image_size_bytes` | mode |
| Histogram | `caption_length_words` | |
| Histogram | `caption_zip_image_count` | |
| Summary | `caption_image_decode_seconds` | mode |
| Summary | `caption_bulk_batch_seconds` | |
| Summary | `caption_bulk_per_image_seconds` | |

Notes:
- A Prometheus Summary exposes `_sum` and `_count`; the `_total` suffix belongs to Counters.
- `session` is an unbounded label, so it appears only on `caption_requests_total` and never on histograms, to limit cardinality.
- System metrics (CPU, memory, disk, network, load) come from node_exporter.

## Dashboard

Rows go from high-level health to low-level resources:

1. **Application health**: app and exporter UP/DOWN, model loaded, uptime, time since last success, active sessions
2. **Throughput**: images/s by mode, requests/s by outcome, in-flight requests and bulk queue, upload volume
3. **Latency**: p50/p95/p99 (log scale), latency heatmap, average time per stage, end-to-end duration
4. **Errors and data quality**: errors by type with error ratio, skipped files by reason, caption length
5. **Clients and inputs**: images per client IP, requests per session, image size and tokens/s
6. **System resources**: host CPU vs throughput, host memory vs app RSS, CPU by mode, disk I/O, load average, network, disk and swap

Every bulk ZIP upload draws an annotation marker across all panels.

Visual conventions:
- Okabe-Ito colour-blind-safe palette.
- Distinct dash patterns per series, so panels stay readable in grayscale.
- Named axes with scale and units.
- Table legends with mean, max and last.
- A description on every panel.
- UP/DOWN shown as text, not colour alone.

## Alerting

| Alert | Condition |
|---|---|
| CaptionAppDown | `up{job="caption_app"} == 0` for 30 s |
| NodeExporterDown | `up{job="node"} == 0` for 30 s |
| HighInferenceLatency | p95 inference > 5 s for 1 min |
| HighErrorRate | error ratio > 10 % for 1 min |
| HighCPU | host CPU > 90 % for 1 min |
| LowMemory | host memory used > 90 % for 1 min |

Firing alerts appear at http://localhost:9090/alerts and in Alertmanager at http://localhost:9093.

## Manual metric calculations

`python3 scripts/calc.py` reproduces these live. The values below come from a test run.

**Average decode time (Summary)**
```
average = _sum / _count = 2.915 / 105 = 0.028 s per image
```

**p95 inference latency (Histogram)**
```
cumulative bulk buckets: le=3 → 0, le=5 → 77, le=8 → 98, le=13 → 100, le=20 → 103, +Inf → 106
rank = 0.95 × 106 = 100.7  → between le=13 (100) and le=20 (103)
p95  = 13 + (100.7 − 100) / (103 − 100) × (20 − 13) = 14.6 s
```
`histogram_quantile` applies the same linear interpolation to bucket rates over the query window.

**p50 inference latency**
```
rank = 0.5 × 106 = 53  → between le=3 (0) and le=5 (77)
p50  = 3 + (53 − 0) / (77 − 0) × (5 − 3) = 4.4 s
```

**Error ratio**
```
errors / all images = 2 / (101 + 2 + 4) = 1.9 %
```

**rate()**
```
two readings 21.1 s apart: 243 → 251 bulk successes
rate = (251 − 243) / 21.1 = 0.38 images/s     (Prometheus over 20 s: 0.33)
```
Prometheus only has samples every 5 s and extrapolates from the first and last sample in the window. The counter also moves in whole images, so short windows differ slightly.

**Host CPU %**
```
per core: busy % = 100 × (1 − increase in idle seconds / elapsed seconds)
core 0: idle 1334.42 → 1336.46 over 21.1 s → 0.097 idle → 90.3 % busy
average over 6 cores = 84.81 %                (Prometheus: 84.46 %)
```

**Memory used %**
```
100 × (1 − node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)
```

