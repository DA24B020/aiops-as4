#!/usr/bin/env bash
cd "$(dirname "$0")/.."
step() {
  read -r -p $'\n\e[2m[Enter] '"$1"$'\e[0m' _
  echo -e "\e[1m\$ $1\e[0m"
  bash -c "$1"
}
clear
step "ls app prometheus grafana scripts"
step "curl -s localhost:8000/metrics | grep '^caption_images_processed_total'"
step "curl -s localhost:8000/metrics | grep '^caption_requests_total'"
step "curl -s localhost:8000/metrics | grep '^caption_image_decode_seconds_[sc]'"
step "python scripts/calc.py"
step "pkill -f '[s]treamlit run' && echo 'app stopped'"
echo
