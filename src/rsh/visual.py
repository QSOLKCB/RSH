"""Dependency-free SVG output for RSH paths."""
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Sequence

from .constants import KAPPA_MAX, PSI, VERSION
from .geometry import Sample


def write_svg(rows: Sequence[Sample], path: str | Path, title: str = "RSH bounded helix") -> None:
    if len(rows) < 3:
        raise ValueError("at least three samples are required")

    projected = [(row.x + 0.28 * row.z, row.y - 0.22 * row.z) for row in rows]
    xs = [point[0] for point in projected]
    ys = [point[1] for point in projected]
    extent = max(max(xs) - min(xs), max(ys) - min(ys), 1.0e-9)
    pad = extent * 0.10
    min_x, max_x = min(xs) - pad, max(xs) + pad
    min_y, max_y = min(ys) - pad, max(ys) + pad
    width, height = 960, 720

    def transform(point: tuple[float, float]) -> tuple[float, float]:
        x = 56.0 + (point[0] - min_x) / (max_x - min_x) * (width - 112.0)
        y = height - (56.0 + (point[1] - min_y) / (max_y - min_y) * (height - 112.0))
        return x, y

    polyline = " ".join(f"{x:.2f},{y:.2f}" for x, y in map(transform, projected))
    centre_index = len(rows) // 2
    markers = (
        ("entry", 0, "#f0a34a"),
        ("centre", centre_index, "#f4f7f8"),
        ("exit", len(rows) - 1, "#55d6be"),
    )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" data-model="RSH" data-version="{VERSION}">',
        f"<title>{escape(title)}</title>",
        '<rect width="100%" height="100%" fill="#0b1116"/>',
        '<g opacity="0.24" stroke="#7d929e" stroke-width="1">',
    ]
    for x in range(80, width, 80):
        parts.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{height}"/>')
    for y in range(80, height, 80):
        parts.append(f'<line x1="0" y1="{y}" x2="{width}" y2="{y}"/>')
    parts.extend(
        [
            "</g>",
            f'<text x="36" y="38" fill="#dce7eb" font-family="ui-monospace,monospace" font-size="18">{escape(title)}</text>',
            f'<text x="36" y="63" fill="#8ca1ac" font-family="ui-monospace,monospace" font-size="13">ψ={PSI:.9f} · κ≤{KAPPA_MAX:.9f} · midpoint normalised to origin</text>',
            f'<polyline points="{polyline}" fill="none" stroke="#55d6be" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
        ]
    )
    for label, index, colour in markers:
        x, y = transform(projected[index])
        radius = 9 if label != "centre" else 12
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius}" fill="{colour}"/>')
        if label == "centre":
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="22" fill="none" stroke="{colour}" stroke-opacity="0.35" stroke-width="2"/>')
        parts.append(f'<text x="{x + 14:.2f}" y="{y - 12:.2f}" fill="{colour}" font-family="ui-monospace,monospace" font-size="13">{label}</text>')
    parts.append("</svg>")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")
