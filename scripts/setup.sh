#!/usr/bin/env bash
set -euo pipefail
MON="$HOME/monitoring"
mkdir -p "$MON"
cd "$MON"
for app in prometheus alertmanager node_exporter; do
  if ! ls -d "$app"-*.linux-amd64 >/dev/null 2>&1; then
    ver=$(curl -s "https://api.github.com/repos/prometheus/$app/releases/latest" | grep -Po '"tag_name": "v\K[^"]+')
    wget -q --show-progress "https://github.com/prometheus/$app/releases/download/v$ver/$app-$ver.linux-amd64.tar.gz"
    tar xzf "$app-$ver.linux-amd64.tar.gz"
    rm "$app-$ver.linux-amd64.tar.gz"
  fi
done
if ! docker ps -a --format '{{.Names}}' | grep -qx grafana; then
  docker pull grafana/grafana-enterprise
  docker run -d -p 3000:3000 --name=grafana grafana/grafana-enterprise
fi
ls "$MON"
echo "Done."
