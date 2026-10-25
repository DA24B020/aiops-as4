import os
import time

import streamlit as st
import torch
from PIL import Image
from transformers import BlipForConditionalGeneration, BlipProcessor

import metrics

NAME = os.getenv("MODEL_NAME", "Salesforce/blip-image-captioning-base")
THREADS = int(os.getenv("TORCH_THREADS", str(max(1, (os.cpu_count() or 2) - 1))))
MAX_SIDE = 512


@st.cache_resource
def load():
    torch.set_num_threads(THREADS)
    processor = BlipProcessor.from_pretrained(NAME)
    model = BlipForConditionalGeneration.from_pretrained(NAME)
    model.eval()
    metrics.model_loads.labels(model=NAME).inc()
    metrics.model_loaded.labels(model=NAME).set(1)
    metrics.info.info({
        "model": NAME,
        "device": "cpu",
        "torch_threads": str(THREADS),
        "torch_version": torch.__version__,
    })
    return processor, model


def shrink(image):
    image = image.convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    return image


def caption(image, mode):
    processor, model = load()
    start = time.perf_counter()
    inputs = processor(images=shrink(image), return_tensors="pt")
    metrics.preprocess.labels(mode=mode).observe(time.perf_counter() - start)

    start = time.perf_counter()
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=30)
    metrics.inference.labels(mode=mode).observe(time.perf_counter() - start)

    text = processor.decode(output[0], skip_special_tokens=True).strip()
    metrics.tokens.labels(mode=mode).inc(int(output.shape[-1]))
    metrics.caption_words.observe(len(text.split()))
    return text


def open_image(data, mode):
    start = time.perf_counter()
    image = Image.open(data)
    image.load()
    metrics.decode.labels(mode=mode).observe(time.perf_counter() - start)
    return image
