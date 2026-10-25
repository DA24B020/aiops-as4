# AI Usage

AI (Claude) was used to generate the PromQL queries and regular expressions in this project, as allowed by the assignment's Fair Use of AI rules. Each one is listed below with the prompt used, and each AI-generated metric was calculated manually to verify it.

## PromQL

These prompts are also written as comments above each rule in `prometheus/recording_rules.yml`.

| Rule | Prompt |
|---|---|
| `caption:inference_seconds:p50_1m` | "PromQL for p50 inference latency per mode over 1m from a Prometheus histogram named caption_inference_seconds" |
| `caption:inference_seconds:p95_1m` | "Same as above but p95" |
| `caption:inference_seconds:p99_1m` | "Same as above but p99" |
| `caption:inference_seconds:avg_1m` | "Average latency per mode from histogram _sum and _count over 1m" |
| `caption:decode_seconds:avg_1m` | "Average from a Summary's _sum and _count over 1m" |
| `caption:error_ratio:rate1m` | "Error ratio of images processed, errors over all, 1m window, 0 when idle" |
| `node:cpu_utilisation:percent` | "PromQL for overall CPU utilisation percent from node_exporter over 1m" |
| `node:memory_used:percent` | "PromQL for memory used percent from node_exporter MemAvailable and MemTotal" |
| `node:disk_used:percent` | "PromQL for root filesystem used percent, excluding tmpfs and overlay" |

## Regex

| Where | Regex | Request |
|---|---|---|
| `node:disk_used:percent` | `fstype!~"tmpfs\|overlay"` | Exclude tmpfs and overlay filesystems |
| Dashboard, Disk I/O | `device!~"loop.*"` | Exclude loop devices |
| Dashboard, CPU time by mode | `mode=~"user\|system\|iowait"` | Only user, system and iowait CPU modes |

## Manual calculation

Every AI-generated metric was recomputed by hand from the raw `/metrics` values. `python3 scripts/calc.py` shows each calculation live next to Prometheus's value. The worked examples are in `README.md` under "Manual metric calculations".

