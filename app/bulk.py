import io
import os
import zipfile

import metrics

IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".tiff"}
MAX_FILES = 200
MAX_TOTAL = 200 * 1024 * 1024
MAX_FILE = 20 * 1024 * 1024


class ZipTooBig(Exception):
    pass


def skip_reason(entry):
    name = entry.filename
    base = os.path.basename(name)
    if entry.is_dir():
        return "directory"
    if name.startswith("__MACOSX/") or base.startswith("."):
        return "hidden"
    if os.path.splitext(base)[1].lower() not in IMAGE_TYPES:
        return "non_image"
    if entry.file_size > MAX_FILE:
        return "too_large"
    return None


def read_zip(data):
    archive = zipfile.ZipFile(io.BytesIO(data))
    entries = archive.infolist()
    if sum(e.file_size for e in entries) > MAX_TOTAL:
        raise ZipTooBig("ZIP expands beyond 200 MB")

    keep = []
    for entry in entries:
        reason = skip_reason(entry)
        if reason:
            if reason != "directory":
                metrics.skipped.labels(reason=reason).inc()
            continue
        keep.append(entry)

    if len(keep) > MAX_FILES:
        metrics.skipped.labels(reason="over_limit").inc(len(keep) - MAX_FILES)
        keep = keep[:MAX_FILES]

    return archive, keep
