import threading
import time

import psutil
import streamlit as st
from prometheus_client import Counter, Gauge, Histogram, Info, Summary, start_http_server

images = Counter("caption_images_processed", "Images captioned", ["mode", "status", "client_ip"])
requests = Counter("caption_requests", "Caption requests", ["mode", "status", "session"])
errors = Counter("caption_errors", "Errors raised", ["mode", "error_type"])
zips = Counter("caption_zip_uploads", "ZIP uploads", ["status"])
skipped = Counter("caption_files_skipped", "Files skipped inside ZIPs", ["reason"])
upload_bytes = Counter("caption_upload_bytes", "Bytes uploaded", ["mode"])
tokens = Counter("caption_tokens_generated", "Tokens generated", ["mode"])
model_loads = Counter("caption_model_loads", "Model loads", ["model"])

active = Gauge("caption_active_requests", "Requests in progress", ["mode"])
sessions = Gauge("caption_active_sessions", "Sessions seen in the last 5 minutes")
model_loaded = Gauge("caption_model_loaded", "1 if the model is loaded", ["model"])
rss = Gauge("caption_process_rss_bytes", "Resident memory of the app process")
cpu = Gauge("caption_process_cpu_percent", "CPU usage of the app process")
queue = Gauge("caption_bulk_queue_remaining", "Images left in the current bulk job")
batch_size = Gauge("caption_last_batch_size", "Images in the last bulk job")
last_success = Gauge("caption_last_success_timestamp_seconds", "Time of last successful request", ["mode"])
info = Info("caption_app", "App build information")

inference = Histogram(
    "caption_inference_seconds", "Model inference time per image", ["mode"],
    buckets=[0.25, 0.5, 1, 2, 3, 5, 8, 13, 20],
)
preprocess = Histogram(
    "caption_preprocess_seconds", "Preprocessing time per image", ["mode"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1],
)
duration = Histogram(
    "caption_request_duration_seconds", "End-to-end request time", ["mode"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600],
)
image_size = Histogram(
    "caption_image_size_bytes", "Uploaded image size", ["mode"],
    buckets=[10e3, 50e3, 100e3, 250e3, 500e3, 1e6, 2.5e6, 5e6, 10e6],
)
caption_words = Histogram(
    "caption_length_words", "Words per generated caption",
    buckets=[2, 4, 6, 8, 10, 12, 15, 20, 30],
)
zip_count = Histogram(
    "caption_zip_image_count", "Valid images per ZIP",
    buckets=[1, 5, 10, 25, 50, 100, 200],
)

decode = Summary("caption_image_decode_seconds", "Image decode time", ["mode"])
batch_time = Summary("caption_bulk_batch_seconds", "Total time per bulk job")
per_image = Summary("caption_bulk_per_image_seconds", "Time per image in bulk jobs")

lock = threading.Lock()
seen = {}
proc = psutil.Process()


def touch(session):
    with lock:
        seen[session] = time.time()


def watch():
    proc.cpu_percent(None)
    while True:
        rss.set(proc.memory_info().rss)
        cpu.set(proc.cpu_percent(None))
        now = time.time()
        with lock:
            for key in [k for k, v in seen.items() if now - v > 300]:
                del seen[key]
            sessions.set(len(seen))
        time.sleep(2)


@st.cache_resource
def start(port=8000):
    start_http_server(port)
    threading.Thread(target=watch, daemon=True).start()
    return True
