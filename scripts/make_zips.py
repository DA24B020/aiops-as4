import argparse
import io
import random
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

TYPES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def synthetic(i):
    random.seed(i)
    image = Image.new("RGB", (640, 480), tuple(random.randint(0, 255) for _ in range(3)))
    draw = ImageDraw.Draw(image)
    for _ in range(6):
        x, y = random.randint(0, 560), random.randint(0, 400)
        w, h = random.randint(40, 200), random.randint(40, 200)
        colour = tuple(random.randint(0, 255) for _ in range(3))
        if random.random() < 0.5:
            draw.ellipse([x, y, x + w, y + h], fill=colour)
        else:
            draw.rectangle([x, y, x + w, y + h], fill=colour)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=90)
    return buffer.getvalue()


def collect(folder):
    if not folder:
        return []
    return sorted(p for p in Path(folder).rglob("*") if p.suffix.lower() in TYPES)


def pick(files, n):
    out = []
    for i in range(n):
        if files:
            path = files[i % len(files)]
            out.append((f"img_{i:03d}{path.suffix.lower()}", path.read_bytes()))
        else:
            out.append((f"img_{i:03d}.jpg", synthetic(i)))
    return out


def write(path, items):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in items:
            z.writestr(name, data)
    print(f"{path}  ({len(items)} entries)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", help="folder of real images to sample from")
    parser.add_argument("--out", default="test_zips")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(exist_ok=True)
    files = collect(args.images)

    for n in (10, 50, 100):
        write(out / f"bulk_{n}.zip", pick(files, n))

    dirty = pick(files, 8)
    dirty.append(("broken.jpg", b"this is not a jpeg"))
    dirty.append(("notes.txt", b"plain text file"))
    dirty.append(("__MACOSX/._img_000.jpg", b"mac metadata"))
    dirty.append((".hidden.png", synthetic(999)))
    dirty.append(("nested/deeper/img_nested.jpg", synthetic(1000)))
    write(out / "dirty.zip", dirty)

    (out / "not_a_zip.zip").write_bytes(b"definitely not a zip archive")
    print(f"{out / 'not_a_zip.zip'}  (invalid archive)")


if __name__ == "__main__":
    main()
