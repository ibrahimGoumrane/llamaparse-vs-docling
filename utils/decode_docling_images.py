"""
Decode Docling image payloads from output/Docling/images.json into binary files.

Run:
    uv run python decode_docling_images.py
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from pathlib import Path


DATA_URI_RE = re.compile(r"^data:image/([a-zA-Z0-9+.-]+);base64,(.*)$", re.DOTALL)


def decode_base64_image_to_file(base64_payload: str, output_path: Path) -> None:
    """Decode a base64 (or data URI base64) image payload and write binary bytes."""
    payload = base64_payload.strip()

    match = DATA_URI_RE.match(payload)
    if match:
        payload = match.group(2)

    try:
        image_bytes = base64.b64decode(payload, validate=True)
    except binascii.Error as exc:
        raise ValueError("Invalid base64 image payload") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)


def decode_images_json(
    images_json_path: Path = Path("output") / "Docling" / "images.json",
    output_dir: Path = Path("output") / "Docling" / "decoded_images",
) -> int:
    """Decode all image payloads from Docling images.json into output_dir."""
    data = json.loads(images_json_path.read_text(encoding="utf-8"))

    count = 0
    for idx, item in enumerate(data, start=1):
        payload = item.get("path")
        if not isinstance(payload, str) or not payload.strip():
            continue

        ext = "png"
        match = DATA_URI_RE.match(payload.strip())
        if match:
            ext = match.group(1).lower().replace("jpeg", "jpg")

        image_name = f"img_{idx:03d}.{ext}"
        decode_base64_image_to_file(payload, output_dir / image_name)
        count += 1

    return count


if __name__ == "__main__":
    written = decode_images_json()
    print(f"Decoded {written} image(s) to output/Docling/decoded_images")
