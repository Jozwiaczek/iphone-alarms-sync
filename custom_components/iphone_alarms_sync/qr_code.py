from __future__ import annotations

import base64
from io import BytesIO

import segno


def generate_qr_code_data_url(url: str) -> str:
    qr = segno.make(url, error="M")
    buffer = BytesIO()
    qr.save(buffer, kind="png", scale=6, border=2)
    base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{base64_str}"
