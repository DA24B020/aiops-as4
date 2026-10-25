import io
import time
import zipfile

import pandas as pd
import streamlit as st

import bulk
import client
import metrics
import model

st.set_page_config(page_title="CPU Image Captioning", layout="wide")
metrics.start()


def run_single(file, ip, session):
    mode = "single"
    metrics.active.labels(mode=mode).inc()
    start = time.perf_counter()
    try:
        data = file.getvalue()
        metrics.upload_bytes.labels(mode=mode).inc(len(data))
        metrics.image_size.labels(mode=mode).observe(len(data))
        image = model.open_image(io.BytesIO(data), mode)
        with st.spinner("Generating caption..."):
            text = model.caption(image, mode)
        st.image(image)
        st.success(text)
        metrics.images.labels(mode=mode, status="success", client_ip=ip).inc()
        metrics.requests.labels(mode=mode, status="success", session=session).inc()
        metrics.last_success.labels(mode=mode).set_to_current_time()
    except Exception as e:
        metrics.images.labels(mode=mode, status="error", client_ip=ip).inc()
        metrics.requests.labels(mode=mode, status="error", session=session).inc()
        metrics.errors.labels(mode=mode, error_type=type(e).__name__).inc()
        st.error(f"Could not caption this image: {e}")
    finally:
        metrics.duration.labels(mode=mode).observe(time.perf_counter() - start)
        metrics.active.labels(mode=mode).dec()


def run_bulk(file, ip, session):
    mode = "bulk"
    metrics.active.labels(mode=mode).inc()
    start = time.perf_counter()
    rows = []
    status = "success"
    try:
        data = file.getvalue()
        metrics.upload_bytes.labels(mode=mode).inc(len(data))
        archive, entries = bulk.read_zip(data)
        total = len(entries)
        metrics.batch_size.set(total)
        metrics.zip_count.observe(total)
        if total == 0:
            st.warning("No valid images found in the ZIP.")
            status = "empty"
            return

        bar = st.progress(0.0, text=f"0 / {total}")
        for i, entry in enumerate(entries, start=1):
            metrics.queue.set(total - i + 1)
            one = time.perf_counter()
            try:
                raw = archive.read(entry)
                metrics.image_size.labels(mode=mode).observe(len(raw))
                image = model.open_image(io.BytesIO(raw), mode)
                text = model.caption(image, mode)
                rows.append({"file": entry.filename, "caption": text, "status": "ok"})
                metrics.images.labels(mode=mode, status="success", client_ip=ip).inc()
            except Exception as e:
                rows.append({"file": entry.filename, "caption": "", "status": f"error: {type(e).__name__}"})
                metrics.images.labels(mode=mode, status="error", client_ip=ip).inc()
                metrics.errors.labels(mode=mode, error_type=type(e).__name__).inc()
                metrics.skipped.labels(reason="corrupt").inc()
            metrics.per_image.observe(time.perf_counter() - one)
            bar.progress(i / total, text=f"{i} / {total}")

        metrics.queue.set(0)
        metrics.last_success.labels(mode=mode).set_to_current_time()
        table = pd.DataFrame(rows)
        st.dataframe(table)
        st.download_button("Download captions CSV", table.to_csv(index=False), "captions.csv", "text/csv")
    except (zipfile.BadZipFile, bulk.ZipTooBig) as e:
        status = "rejected"
        metrics.errors.labels(mode=mode, error_type=type(e).__name__).inc()
        st.error(f"ZIP rejected: {e}")
    except Exception as e:
        status = "error"
        metrics.errors.labels(mode=mode, error_type=type(e).__name__).inc()
        st.error(f"Bulk job failed: {e}")
    finally:
        metrics.queue.set(0)
        metrics.zips.labels(status=status).inc()
        metrics.requests.labels(mode=mode, status=status, session=session).inc()
        elapsed = time.perf_counter() - start
        metrics.duration.labels(mode=mode).observe(elapsed)
        metrics.batch_time.observe(elapsed)
        metrics.active.labels(mode=mode).dec()


def main():
    ip = client.client_ip()
    session = client.session_id()
    metrics.touch(session)

    st.title("CPU Image Captioning")
    st.caption(f"Model: {model.NAME} · session {session} · client {ip}")

    with st.spinner("Loading model..."):
        model.load()

    single, many = st.tabs(["Single image", "Bulk ZIP"])

    with single:
        file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png", "bmp", "webp"], key="one")
        if file and st.button("Caption image"):
            run_single(file, ip, session)

    with many:
        file = st.file_uploader("Upload a ZIP of images", type=["zip"], key="many")
        if file and st.button("Caption all"):
            run_bulk(file, ip, session)


main()
