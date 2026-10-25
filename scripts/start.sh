#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MON="$HOME/monitoring"
mkdir -p "$ROOT/logs" "$ROOT/data"
NODE_DIR="$(ls -d "$MON"/node_exporter-*/ | head -1)"
PROM_DIR="$(ls -d "$MON"/prometheus-*/ | head -1)"
AM_DIR="$(ls -d "$MON"/alertmanager-*/ | head -1)"
pgrep -f "node_exporter" >/dev/null || nohup "${NODE_DIR}node_exporter" > "$ROOT/logs/node_exporter.log" 2>&1 &
pgrep -f "alertmanager --config.file" >/dev/null || (cd "$AM_DIR" && nohup ./alertmanager --config.file=alertmanager.yml --storage.path="$ROOT/data/alertmanager" > "$ROOT/logs/alertmanager.log" 2>&1 &)
pkill -f "prometheus --config.file" || true
sleep 1
nohup "${PROM_DIR}prometheus" \
  --config.file="$ROOT/prometheus/prometheus.yml" \
  --storage.tsdb.path="$ROOT/data/prometheus" \
  --web.enable-lifecycle > "$ROOT/logs/prometheus.log" 2>&1 &
docker start grafana >/dev/null
echo "node_exporter :9100 | alertmanager :9093 | prometheus :9090 | grafana :3000"
cd "$ROOT"
streamlit run app/app.py --server.port 8501 --server.address 0.0.0.0
