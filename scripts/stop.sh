#!/usr/bin/env bash
pkill -f node_exporter || true
pkill -f "alertmanager --config.file" || true
pkill -f "prometheus --config.file" || true
pkill -f "streamlit run" || true
docker stop grafana >/dev/null || true
echo "Stopped."
