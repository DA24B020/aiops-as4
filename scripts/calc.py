import json
import re
import sys
import time
import urllib.parse
import urllib.request

APP = "http://localhost:8000/metrics"
NODE = "http://localhost:9100/metrics"
PROM = "http://localhost:9090/api/v1/query"
WINDOW = 20

B = "\033[1m"
D = "\033[2m"
C = "\033[36m"
Y = "\033[33m"
G = "\033[32m"
N = "\033[0m"


def fetch(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.read().decode()


def parse(text):
    rows = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        m = re.match(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+(\S+)', line)
        if not m:
            continue
        labels = dict(re.findall(r'(\w+)="([^"]*)"', m.group(2) or ""))
        rows.append((m.group(1), labels, float(m.group(3))))
    return rows


def pick(rows, name, **want):
    return [(l, v) for n, l, v in rows if n == name and all(l.get(k) == w for k, w in want.items())]


def total(rows, name, **want):
    return sum(v for _, v in pick(rows, name, **want))


def prom(query):
    url = PROM + "?" + urllib.parse.urlencode({"query": query})
    try:
        data = json.loads(fetch(url))["data"]["result"]
        return float(data[0]["value"][1]) if data else None
    except Exception:
        return None


def title(text):
    print(f"\n{B}{C}━━━ {text} ━━━{N}\n")


def line(text=""):
    print(f"  {text}")


def result(text):
    print(f"  {B}{G}{text}{N}")


def compare(label, value, unit=""):
    if value is None:
        line(f"{D}Prometheus: no value yet{N}")
    else:
        line(f"{Y}Prometheus ({label}) = {value:.4g}{unit}{N}")


def pause():
    try:
        input(f"\n{D}[Enter]{N} ")
    except EOFError:
        print()


def countdown(secs):
    for s in range(secs, 0, -1):
        print(f"\r  {D}waiting {s:2d}s ...{N} ", end="", flush=True)
        time.sleep(1)
    print("\r" + " " * 30 + "\r", end="")


def show(name, rows):
    for labels, value in rows:
        tag = ",".join(f'{k}="{v}"' for k, v in labels.items())
        line(f"{D}{name}{{{tag}}} {value:g}{N}")


def summary(app):
    title("1 · Average decode time from a Summary")
    s = pick(app, "caption_image_decode_seconds_sum", mode="bulk")
    c = pick(app, "caption_image_decode_seconds_count", mode="bulk")
    show("caption_image_decode_seconds_sum", s)
    show("caption_image_decode_seconds_count", c)
    if not c or c[0][1] == 0:
        line("No bulk observations yet.")
        return
    total_s, count = s[0][1], c[0][1]
    print()
    line("average = _sum / _count")
    line(f"        = {total_s:.4f} / {count:g}")
    result(f"        = {total_s / count:.4f} s per image  (all-time)")
    compare("rate(_sum[1m]) / rate(_count[1m])", prom('caption:decode_seconds:avg_1m{mode="bulk"}'), " s")


def quantile(app, q, name):
    rows = []
    for labels, value in pick(app, "caption_inference_seconds_bucket", mode="bulk"):
        le = float("inf") if labels["le"] == "+Inf" else float(labels["le"])
        rows.append((le, value))
    rows.sort()
    n = rows[-1][1]
    rank = q * n
    lower_le, lower_c = 0.0, 0.0
    for le, c in rows:
        if c >= rank:
            upper_le, upper_c = le, c
            break
        lower_le, lower_c = le, c
    line(f"rank = {q} x N = {q} x {n:g} = {rank:g}")
    line(f"first bucket reaching the rank : le = {upper_le:g}  (count {upper_c:g})")
    line(f"bucket before it               : le = {lower_le:g}  (count {lower_c:g})")
    if upper_le == float("inf"):
        result(f"{name} lies above the last finite bucket -> reported as {lower_le:g} s")
        return
    value = lower_le + (rank - lower_c) / (upper_c - lower_c) * (upper_le - lower_le)
    line(f"{name} = lower + (rank - count_lower) / (count_upper - count_lower) x (upper - lower)")
    line(f"    = {lower_le:g} + ({rank:g} - {lower_c:g}) / ({upper_c:g} - {lower_c:g}) x ({upper_le:g} - {lower_le:g})")
    result(f"    = {value:.3f} s  (all-time)")


def histogram(app):
    title("2 · p50 and p95 inference latency from Histogram buckets")
    rows = pick(app, "caption_inference_seconds_bucket", mode="bulk")
    if not rows or max(v for _, v in rows) == 0:
        line("No bulk observations yet.")
        return
    line("Buckets are cumulative: each counts images that finished in <= le seconds.\n")
    line(f"{'le (s)':>8} | {'count':>6}")
    line(f"{'-' * 8}-+-{'-' * 6}")
    for labels, value in sorted(rows, key=lambda r: float("inf") if r[0]["le"] == "+Inf" else float(r[0]["le"])):
        line(f"{labels['le']:>8} | {value:>6g}")
    print()
    quantile(app, 0.5, "p50")
    print()
    quantile(app, 0.95, "p95")
    print()
    compare("histogram_quantile(0.5, rate(...[1m]))", prom('caption:inference_seconds:p50_1m{mode="bulk"}'), " s")
    compare("histogram_quantile(0.95, rate(...[1m]))", prom('caption:inference_seconds:p95_1m{mode="bulk"}'), " s")
    line(f"{D}Prometheus uses only the last minute of bucket increases, so it can differ from the all-time value.{N}")


def errors(app):
    title("3 · Error ratio")
    rows = pick(app, "caption_images_processed_total")
    show("caption_images_processed_total", rows)
    bad = total(app, "caption_images_processed_total", status="error")
    allv = total(app, "caption_images_processed_total")
    if allv == 0:
        line("No images processed yet.")
        return
    print()
    line("error ratio = errors / all images")
    line(f"            = {bad:g} / {allv:g}")
    result(f"            = {bad / allv:.4f}  =  {100 * bad / allv:.2f} %  (all-time)")
    compare("last 1 min", prom("caption:error_ratio:rate1m"))


def memory():
    title("4 · Host memory used %")
    node = parse(fetch(NODE))
    avail = total(node, "node_memory_MemAvailable_bytes")
    tot = total(node, "node_memory_MemTotal_bytes")
    line(f"{D}node_memory_MemAvailable_bytes {avail:g}{N}")
    line(f"{D}node_memory_MemTotal_bytes     {tot:g}{N}")
    print()
    line("memory used % = 100 x (1 - MemAvailable / MemTotal)")
    line(f"              = 100 x (1 - {avail / 2**30:.3f} GiB / {tot / 2**30:.3f} GiB)")
    result(f"              = {100 * (1 - avail / tot):.2f} %")
    compare("node:memory_used:percent", prom("node:memory_used:percent"), " %")


def idle(node):
    return {l["cpu"]: v for l, v in pick(node, "node_cpu_seconds_total", mode="idle")}


def rates():
    title(f"5 · rate() and host CPU % from two readings {WINDOW} s apart")
    if total(parse(fetch(APP)), "caption_active_requests", mode="bulk") == 0:
        line(f"{Y}Tip: start bulk_100.zip in Streamlit first so the counters are moving.{N}")
    line("Reading A ...")
    a_app, a_node, a_time = parse(fetch(APP)), parse(fetch(NODE)), time.time()
    countdown(WINDOW)
    line("Reading B ...")
    b_app, b_node, b_time = parse(fetch(APP)), parse(fetch(NODE)), time.time()
    dt = b_time - a_time

    print()
    line(f"{B}rate(caption_images_processed_total{{mode=\"bulk\",status=\"success\"}}){N}")
    a = total(a_app, "caption_images_processed_total", mode="bulk", status="success")
    b = total(b_app, "caption_images_processed_total", mode="bulk", status="success")
    line("rate = (value at B - value at A) / seconds between A and B")
    line(f"     = ({b:g} - {a:g}) / {dt:.1f}")
    result(f"     = {(b - a) / dt:.4f} images/s")
    compare(f"rate over the same {WINDOW} s",
            prom(f'sum(rate(caption_images_processed_total{{mode="bulk",status="success"}}[{WINDOW}s]))'), " images/s")

    print()
    line(f"{B}Host CPU %{N}")
    ia, ib = idle(a_node), idle(b_node)
    busy = []
    line(f"{'cpu':>4} | {'idle A':>10} | {'idle B':>10} | {'idle/s':>6} | {'busy %':>6}")
    line(f"{'-' * 4}-+-{'-' * 10}-+-{'-' * 10}-+-{'-' * 6}-+-{'-' * 6}")
    for cpu in sorted(ia, key=int):
        frac = (ib[cpu] - ia[cpu]) / dt
        busy.append(100 * (1 - frac))
        line(f"{cpu:>4} | {ia[cpu]:>10.2f} | {ib[cpu]:>10.2f} | {frac:>6.3f} | {busy[-1]:>6.1f}")
    print()
    line("busy % per core = 100 x (1 - increase in idle seconds / elapsed seconds)")
    line(f"host CPU %      = average over {len(busy)} cores")
    result(f"                = {sum(busy) / len(busy):.2f} %")
    compare(f"same formula over {WINDOW} s",
            prom(f'100 * (1 - avg(rate(node_cpu_seconds_total{{mode="idle"}}[{WINDOW}s])))'), " %")


def main():
    print(f"{B}Manual calculation of dashboard metrics from raw /metrics values{N}")
    pause()
    app = parse(fetch(APP))
    summary(app)
    pause()
    histogram(app)
    pause()
    errors(app)
    pause()
    memory()
    pause()
    rates()
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        sys.exit(0)
    except OSError as e:
        print(f"\n  Could not reach a metrics endpoint ({e}). Is the app running and opened once in the browser?")
        sys.exit(1)
