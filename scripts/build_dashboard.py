import json
from pathlib import Path

BLUE = "#0072B2"
ORANGE = "#E69F00"
GREEN = "#009E73"
VERMILION = "#D55E00"
PURPLE = "#CC79A7"
SKY = "#56B4E9"
YELLOW = "#F0E442"
DS = {"type": "prometheus", "uid": "${DS_PROMETHEUS}"}

state = {"id": 0, "y": 0}


def next_id():
    state["id"] += 1
    return state["id"]


def target(expr, legend, ref="A", fmt="time_series", instant=False):
    return {
        "datasource": DS,
        "expr": expr,
        "legendFormat": legend,
        "refId": ref,
        "format": fmt,
        "instant": instant,
        "range": not instant,
    }


def style(name, colour, dash=None, axis=None):
    props = [
        {"id": "color", "value": {"mode": "fixed", "fixedColor": colour}},
    ]
    if dash:
        props.append({"id": "custom.lineStyle", "value": {"fill": "dash", "dash": dash}})
    if axis:
        props += axis
    return {"matcher": {"id": "byName", "options": name}, "properties": props}


def right_axis(label, unit):
    return [
        {"id": "custom.axisPlacement", "value": "right"},
        {"id": "custom.axisLabel", "value": label},
        {"id": "unit", "value": unit},
    ]


def row(title):
    panel = {
        "type": "row",
        "id": next_id(),
        "title": title,
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": state["y"]},
        "panels": [],
    }
    state["y"] += 1
    return panel


def note(text):
    panel = {
        "type": "text",
        "id": next_id(),
        "title": "",
        "transparent": True,
        "gridPos": {"h": 2, "w": 24, "x": 0, "y": state["y"]},
        "options": {"mode": "markdown", "content": text},
    }
    state["y"] += 2
    return panel


def stat(title, desc, targets, x, w, unit="none", mappings=None, thresholds=None, h=4):
    return {
        "type": "stat",
        "id": next_id(),
        "title": title,
        "description": desc,
        "datasource": DS,
        "gridPos": {"h": h, "w": w, "x": x, "y": state["y"]},
        "targets": targets,
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "mappings": mappings or [],
                "color": {"mode": "thresholds"},
                "thresholds": thresholds or {
                    "mode": "absolute",
                    "steps": [{"color": BLUE, "value": None}],
                },
            },
            "overrides": [],
        },
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "colorMode": "background",
            "graphMode": "none",
            "textMode": "value_and_name",
            "justifyMode": "center",
        },
    }


def series(title, desc, targets, x, w, unit, axis_label, overrides,
           scale="linear", h=8, stack=False, bars=False, minimum=None):
    custom = {
        "drawStyle": "bars" if bars else "line",
        "lineWidth": 2,
        "fillOpacity": 25 if (stack or bars) else 0,
        "showPoints": "always",
        "pointSize": 4,
        "axisLabel": axis_label,
        "axisPlacement": "left",
        "scaleDistribution": {"type": "log", "log": 10} if scale == "log" else {"type": "linear"},
        "spanNulls": True,
        "stacking": {"mode": "normal" if stack else "none", "group": "A"},
    }
    defaults = {"unit": unit, "custom": custom, "color": {"mode": "fixed", "fixedColor": BLUE}}
    if minimum is not None:
        defaults["min"] = minimum
    return {
        "type": "timeseries",
        "id": next_id(),
        "title": title,
        "description": desc,
        "datasource": DS,
        "gridPos": {"h": h, "w": w, "x": x, "y": state["y"]},
        "targets": targets,
        "fieldConfig": {"defaults": defaults, "overrides": overrides},
        "options": {
            "legend": {"displayMode": "table", "placement": "bottom", "showLegend": True,
                       "calcs": ["mean", "max", "lastNotNull"]},
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
    }


def heatmap(title, desc, expr, x, w, h=8):
    return {
        "type": "heatmap",
        "id": next_id(),
        "title": title,
        "description": desc,
        "datasource": DS,
        "gridPos": {"h": h, "w": w, "x": x, "y": state["y"]},
        "targets": [target(expr, "{{le}}", fmt="heatmap")],
        "options": {
            "calculate": False,
            "cellGap": 1,
            "color": {"mode": "scheme", "scheme": "Cividis", "steps": 64, "exponent": 0.5},
            "yAxis": {"axisLabel": "Inference time bucket (s, bucket upper bound)", "unit": "s"},
            "legend": {"show": True},
            "tooltip": {"show": True, "yHistogram": True},
            "rowsFrame": {"layout": "auto"},
        },
    }


def bar_gauge(title, desc, expr, legend, x, w, unit, h=8):
    return {
        "type": "bargauge",
        "id": next_id(),
        "title": title,
        "description": desc,
        "datasource": DS,
        "gridPos": {"h": h, "w": w, "x": x, "y": state["y"]},
        "targets": [target(expr, legend, instant=True)],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "color": {"mode": "fixed", "fixedColor": BLUE},
                "min": 0,
            },
            "overrides": [],
        },
        "options": {
            "orientation": "horizontal",
            "displayMode": "basic",
            "showUnfilled": True,
            "valueMode": "text",
            "namePlacement": "left",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
        },
    }


def table(title, desc, expr, x, w, h=8):
    return {
        "type": "table",
        "id": next_id(),
        "title": title,
        "description": desc,
        "datasource": DS,
        "gridPos": {"h": h, "w": w, "x": x, "y": state["y"]},
        "targets": [target(expr, "", fmt="table", instant=True)],
        "transformations": [
            {"id": "organize", "options": {
                "excludeByName": {"Time": True},
                "renameByName": {"client_ip": "Client IP", "mode": "Mode", "Value": "Images (last 15 min)"},
            }},
        ],
        "fieldConfig": {"defaults": {"unit": "short"}, "overrides": []},
        "options": {"showHeader": True, "sortBy": [{"displayName": "Images (last 15 min)", "desc": True}]},
    }


UPDOWN = [{"type": "value", "options": {
    "0": {"text": "DOWN", "color": VERMILION, "index": 0},
    "1": {"text": "UP", "color": BLUE, "index": 1},
}}]
LOADED = [{"type": "value", "options": {
    "0": {"text": "NOT LOADED", "color": VERMILION, "index": 0},
    "1": {"text": "LOADED", "color": BLUE, "index": 1},
}}, {"type": "special", "options": {"match": "null", "result": {"text": "NOT LOADED", "color": VERMILION}}}]


def build():
    panels = []

    panels.append(row("1 · Application health"))
    panels.append(note("**Is the service alive?** Up/down of the app and node exporter, model state and freshness. "
                       "Text labels (UP/DOWN) carry the meaning, so colour is never the only signal."))
    panels += [
        stat("App status", "1 = Prometheus can scrape the app's /metrics endpoint on :8000. 0 = app crashed or stopped.",
             [target('up{job="caption_app"}', "App")], 0, 4, mappings=UPDOWN),
        stat("Node exporter status", "1 = node_exporter on :9100 is reachable, so host metrics below are valid.",
             [target('up{job="node"}', "Node exporter")], 4, 4, mappings=UPDOWN),
        stat("Model", "1 once the BLIP model is in memory. Set at first page load.",
             [target("max(caption_model_loaded)", "Model")], 8, 4, mappings=LOADED),
        stat("App uptime", "Seconds since the app process started (process_start_time_seconds).",
             [target('time() - process_start_time_seconds{job="caption_app"}', "Uptime")], 12, 4, unit="s"),
        stat("Since last success", "Seconds since any request last completed successfully. Large values with traffic = problem.",
             [target("time() - max(caption_last_success_timestamp_seconds)", "Last success")], 16, 4, unit="s"),
        stat("Active sessions", "Browser sessions that interacted with the app in the last 5 minutes.",
             [target("caption_active_sessions", "Sessions")], 20, 4),
    ]
    state["y"] += 4

    panels.append(row("2 · Throughput"))
    panels.append(note("**How much work is flowing?** Images/s split by Single vs Bulk, request outcomes, and in-flight work. "
                       "The dashed vertical markers are bulk ZIP uploads."))
    panels += [
        series("Images captioned per second",
               "rate() of caption_images_processed_total{status=\"success\"} over 1 min, by upload mode. "
               "Bulk jobs show as a sustained plateau; single uploads as short blips.",
               [target("caption:images_per_second:rate1m", "{{mode}}")],
               0, 12, "reqps", "Throughput (images/s, linear)",
               [style("single", BLUE), style("bulk", ORANGE, [10, 10])], minimum=0),
        series("Requests per second by outcome",
               "rate() of caption_requests_total over 1 min by mode and status. A bulk ZIP counts as one request.",
               [target("caption:requests_per_second:rate1m", "{{mode}} · {{status}}")],
               12, 12, "reqps", "Requests (req/s, linear)",
               [style("single · success", BLUE), style("bulk · success", ORANGE, [10, 10]),
                style("single · error", VERMILION, [2, 4]), style("bulk · error", PURPLE, [2, 4]),
                style("bulk · rejected", YELLOW, [2, 4]), style("bulk · empty", SKY, [6, 3])], minimum=0),
    ]
    state["y"] += 8
    panels += [
        series("In-flight requests and bulk queue",
               "caption_active_requests (gauge) per mode, and caption_bulk_queue_remaining (images still waiting in the running ZIP).",
               [target("sum by (mode) (caption_active_requests)", "active · {{mode}}"),
                target("caption_bulk_queue_remaining", "bulk queue remaining", "B")],
               0, 12, "short", "Count (linear)",
               [style("active · single", BLUE), style("active · bulk", ORANGE, [10, 10]),
                style("bulk queue remaining", GREEN, [2, 4], right_axis("Images waiting (linear)", "short"))],
               minimum=0),
        series("Upload volume",
               "rate() of caption_upload_bytes_total over 1 min by mode: how many bytes the app is ingesting.",
               [target("sum by (mode) (rate(caption_upload_bytes_total[1m]))", "{{mode}}")],
               12, 12, "Bps", "Upload rate (bytes/s, linear)",
               [style("single", BLUE), style("bulk", ORANGE, [10, 10])], minimum=0),
    ]
    state["y"] += 8

    panels.append(row("3 · Latency"))
    panels.append(note("**How fast is each image?** Percentiles from the histogram (log scale, so 0.5 s and 10 s are both readable), "
                       "the full distribution as a heatmap, and where the time goes."))
    panels += [
        series("Inference latency percentiles",
               "histogram_quantile() over caption_inference_seconds_bucket (1 min window). "
               "p50 = typical image, p99 = worst 1 %. Log₁₀ y-axis.",
               [target("caption:inference_seconds:p50_1m", "p50 · {{mode}}"),
                target("caption:inference_seconds:p95_1m", "p95 · {{mode}}", "B"),
                target("caption:inference_seconds:p99_1m", "p99 · {{mode}}", "C")],
               0, 12, "s", "Inference time (s, log₁₀ scale)",
               [style("p50 · single", BLUE), style("p95 · single", BLUE, [10, 10]), style("p99 · single", BLUE, [2, 4]),
                style("p50 · bulk", ORANGE), style("p95 · bulk", ORANGE, [10, 10]), style("p99 · bulk", ORANGE, [2, 4])],
               scale="log"),
        heatmap("Inference time distribution",
                "Per-bucket increase of caption_inference_seconds_bucket. Each column is one time step; "
                "brighter cells = more images finished in that latency band.",
                "sum by (le) (increase(caption_inference_seconds_bucket[1m]))", 12, 12),
    ]
    state["y"] += 8
    panels += [
        series("Average time per stage",
               "Mean seconds per image for decode (Summary _sum/_count), preprocess and inference (Histogram _sum/_count). "
               "Inference dominates on CPU.",
               [target("caption:decode_seconds:avg_1m", "decode · {{mode}}"),
                target("sum by (mode) (rate(caption_preprocess_seconds_sum[1m])) / sum by (mode) (rate(caption_preprocess_seconds_count[1m]))",
                       "preprocess · {{mode}}", "B"),
                target("caption:inference_seconds:avg_1m", "inference · {{mode}}", "C")],
               0, 12, "s", "Mean time per image (s, log₁₀ scale)",
               [style("decode · single", GREEN, [2, 4]), style("decode · bulk", GREEN, [10, 10]),
                style("preprocess · single", PURPLE, [2, 4]), style("preprocess · bulk", PURPLE, [10, 10]),
                style("inference · single", BLUE), style("inference · bulk", ORANGE)],
               scale="log"),
        series("End-to-end request duration",
               "Average of caption_request_duration_seconds (histogram) per mode. For bulk this is the whole ZIP; "
               "dotted line is caption_bulk_per_image_seconds (Summary).",
               [target("sum by (mode) (rate(caption_request_duration_seconds_sum[5m])) / sum by (mode) (rate(caption_request_duration_seconds_count[5m]))",
                       "request · {{mode}}"),
                target("rate(caption_bulk_per_image_seconds_sum[5m]) / rate(caption_bulk_per_image_seconds_count[5m])",
                       "bulk per image", "B")],
               12, 12, "s", "Duration (s, log₁₀ scale)",
               [style("request · single", BLUE), style("request · bulk", ORANGE, [10, 10]),
                style("bulk per image", GREEN, [2, 4])],
               scale="log"),
    ]
    state["y"] += 8

    panels.append(row("4 · Errors and data quality"))
    panels.append(note("**What is going wrong?** Failure rate, error types and files dropped from ZIPs, plus a sanity check on caption output."))
    panels += [
        series("Errors per second by type",
               "rate() of caption_errors_total over 1 min by exception class. Dashed line (right axis) is the error ratio.",
               [target("sum by (error_type) (rate(caption_errors_total[1m]))", "{{error_type}}"),
                target("caption:error_ratio:rate1m", "error ratio", "B")],
               0, 8, "short", "Errors (errors/s, linear)",
               [style("error ratio", VERMILION, [10, 10], right_axis("Error ratio (0–1, linear)", "percentunit"))],
               bars=False, minimum=0),
        series("Files skipped in ZIPs",
               "increase() of caption_files_skipped_total over 1 min by reason: non_image, hidden, corrupt, too_large, over_limit.",
               [target("sum by (reason) (increase(caption_files_skipped_total[1m]))", "{{reason}}")],
               8, 8, "short", "Files skipped (count per minute, linear)",
               [style("non_image", BLUE), style("hidden", ORANGE, [10, 10]), style("corrupt", VERMILION, [2, 4]),
                style("too_large", PURPLE, [6, 3]), style("over_limit", GREEN, [2, 2])],
               bars=True, stack=True, minimum=0),
        series("Caption length",
               "Median and p90 of caption_length_words (histogram). A sudden drop to 1–2 words suggests bad inputs.",
               [target("histogram_quantile(0.5, sum by (le) (rate(caption_length_words_bucket[5m])))", "median words"),
                target("histogram_quantile(0.9, sum by (le) (rate(caption_length_words_bucket[5m])))", "p90 words", "B")],
               16, 8, "short", "Words per caption (linear)",
               [style("median words", BLUE), style("p90 words", ORANGE, [10, 10])], minimum=0),
    ]
    state["y"] += 8

    panels.append(row("5 · Clients and inputs"))
    panels.append(note("**Who is sending what?** Per-client volume from the client_ip label, and what kind of images arrive."))
    panels += [
        table("Images per client (last 15 min)",
              "sum by (client_ip, mode) of increase(caption_images_processed_total[15m]). Uses the client_ip label.",
              "sum by (client_ip, mode) (increase(caption_images_processed_total[15m])) > 0", 0, 8),
        bar_gauge("Requests per session (last 15 min)",
                  "increase(caption_requests_total[15m]) by session label (first 8 chars of the Streamlit session id).",
                  "topk(10, sum by (session) (increase(caption_requests_total[15m])))", "{{session}}", 8, 8, "short"),
        series("Uploaded image size and tokens",
               "Median of caption_image_size_bytes (left axis) and tokens generated per second (right axis, dashed).",
               [target("histogram_quantile(0.5, sum by (le) (rate(caption_image_size_bytes_bucket[5m])))", "median image size"),
                target("sum(rate(caption_tokens_generated_total[1m]))", "tokens/s", "B")],
               16, 8, "bytes", "Image size (bytes, linear)",
               [style("median image size", BLUE),
                style("tokens/s", ORANGE, [10, 10], right_axis("Tokens generated (tokens/s, linear)", "short"))],
               minimum=0),
    ]
    state["y"] += 8

    panels.append(row("6 · System resources (correlated with bulk uploads)"))
    panels.append(note("**Does the hardware explain the app?** Host CPU, memory, disk and load from node_exporter, overlaid with app throughput "
                       "and the app's own memory. Bulk-upload markers line up spikes with their cause."))
    panels += [
        series("Host CPU vs captioning throughput",
               "Left: node CPU utilisation % (100 − idle). Right, dashed: images/s across both modes. "
               "During a bulk ZIP both rise together.",
               [target("node:cpu_utilisation:percent", "host CPU %"),
                target("sum(caption:images_per_second:rate1m)", "images/s", "B")],
               0, 12, "percent", "CPU utilisation (%, linear)",
               [style("host CPU %", BLUE),
                style("images/s", ORANGE, [10, 10], right_axis("Throughput (images/s, linear)", "reqps"))],
               minimum=0),
        series("Host memory vs app memory",
               "Left: node memory used %. Right, dashed: resident memory of the app process (caption_process_rss_bytes). "
               "The model alone is ~1 GB.",
               [target("node:memory_used:percent", "host memory used %"),
                target("caption_process_rss_bytes", "app RSS", "B")],
               12, 12, "percent", "Memory used (%, linear)",
               [style("host memory used %", BLUE),
                style("app RSS", ORANGE, [10, 10], right_axis("App resident memory (bytes, linear)", "bytes"))],
               minimum=0),
    ]
    state["y"] += 8
    panels += [
        series("CPU time by mode",
               "rate(node_cpu_seconds_total[1m]) summed across cores by mode (user, system, iowait). Stacked, in cores busy.",
               [target('sum by (mode) (rate(node_cpu_seconds_total{mode=~"user|system|iowait"}[1m]))', "{{mode}}")],
               0, 8, "short", "CPU cores busy (cores, linear)",
               [style("user", BLUE), style("system", ORANGE, [10, 10]), style("iowait", VERMILION, [2, 4])],
               stack=True, minimum=0),
        series("Disk I/O",
               "rate() of node_disk_read_bytes_total and node_disk_written_bytes_total. ZIP uploads and model load cause reads/writes.",
               [target('sum(rate(node_disk_read_bytes_total{device!~"loop.*"}[1m]))', "read"),
                target('sum(rate(node_disk_written_bytes_total{device!~"loop.*"}[1m]))', "write", "B")],
               8, 8, "Bps", "Disk throughput (bytes/s, linear)",
               [style("read", BLUE), style("write", ORANGE, [10, 10])], minimum=0),
        series("Load average and app CPU",
               "node_load1 and node_load5 (left) against the number of CPU cores; app process CPU % from psutil (right, dotted).",
               [target("node_load1", "load 1m"), target("node_load5", "load 5m", "B"),
                target('count(node_cpu_seconds_total{mode="idle"})', "CPU cores", "C"),
                target("caption_process_cpu_percent", "app CPU %", "D")],
               16, 8, "short", "Load (runnable tasks, linear)",
               [style("load 1m", BLUE), style("load 5m", BLUE, [10, 10]), style("CPU cores", GREEN, [6, 3]),
                style("app CPU %", ORANGE, [2, 4], right_axis("App CPU (% of one core, linear)", "percent"))],
               minimum=0),
    ]
    state["y"] += 8
    panels += [
        series("Network traffic",
               "rate() of node_network_receive/transmit_bytes_total excluding loopback. Includes browser uploads over the VM NAT.",
               [target('sum(rate(node_network_receive_bytes_total{device!="lo"}[1m]))', "receive"),
                target('sum(rate(node_network_transmit_bytes_total{device!="lo"}[1m]))', "transmit", "B")],
               0, 12, "Bps", "Network (bytes/s, linear)",
               [style("receive", BLUE), style("transmit", ORANGE, [10, 10])], minimum=0),
        stat("Root disk used", "node:disk_used:percent for /. Above 85 % turns orange, above 95 % vermilion.",
             [target("node:disk_used:percent", "Disk used")], 12, 6, unit="percent", h=8,
             thresholds={"mode": "absolute", "steps": [
                 {"color": BLUE, "value": None}, {"color": ORANGE, "value": 85}, {"color": VERMILION, "value": 95}]}),
        stat("Swap used", "Swap in use on the VM. Non-zero during bulk jobs means the VM needs more RAM.",
             [target("node_memory_SwapTotal_bytes - node_memory_SwapFree_bytes", "Swap")], 18, 6, unit="bytes", h=8),
    ]
    state["y"] += 8

    return {
        "__inputs": [{
            "name": "DS_PROMETHEUS", "label": "Prometheus", "type": "datasource",
            "pluginId": "prometheus", "pluginName": "Prometheus",
        }],
        "__requires": [
            {"type": "grafana", "id": "grafana", "name": "Grafana", "version": "10.0.0"},
            {"type": "datasource", "id": "prometheus", "name": "Prometheus", "version": "1.0.0"},
        ],
        "title": "DA3408 A4 · CPU Image Captioning — Observability",
        "description": "Health → throughput → latency → errors → clients → system resources. Refresh 5 s.",
        "uid": "da3408-a4-captioning",
        "tags": ["da3408", "prometheus", "captioning"],
        "timezone": "browser",
        "editable": True,
        "graphTooltip": 1,
        "refresh": "5s",
        "schemaVersion": 39,
        "time": {"from": "now-15m", "to": "now"},
        "timepicker": {"refresh_intervals": ["5s", "10s", "30s", "1m"]},
        "annotations": {"list": [
            {
                "builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"},
                "enable": True, "hide": True, "iconColor": "rgba(0, 211, 255, 1)",
                "name": "Annotations & Alerts", "type": "dashboard",
            },
            {
                "datasource": DS, "enable": True, "iconColor": ORANGE,
                "name": "Bulk ZIP upload",
                "expr": "sum(increase(caption_zip_uploads_total[10s])) > 0",
                "step": "10s", "titleFormat": "Bulk ZIP upload", "textFormat": "A ZIP job finished",
            },
        ]},
        "templating": {"list": []},
        "panels": panels,
    }


def main():
    out = Path(__file__).resolve().parent.parent / "grafana" / "dashboard.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(build(), indent=2))
    print(out)


if __name__ == "__main__":
    main()
