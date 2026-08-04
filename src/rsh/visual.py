"""Dependency-free SVG output for RSH paths."""
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Sequence

from .constants import KAPPA_MAX, PSI, VERSION
from .geometry import Sample


def write_svg(
    rows: Sequence[Sample],
    path: str | Path,
    title: str = "RSH bounded helix",
) -> None:
    if len(rows) < 3:
        raise ValueError("at least three samples are required")

    projected = [
        (row.x + 0.28 * row.z, row.y - 0.22 * row.z)
        for row in rows
    ]
    xs = [point[0] for point in projected]
    ys = [point[1] for point in projected]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max_x - min_x
    span_y = max_y - min_y
    extent = max(span_x, span_y, 1.0e-9)
    pad = extent * 0.10

    width, height = 960, 720
    left, right = 56.0, width - 56.0
    top, bottom = 88.0, height - 56.0
    drawable_width = right - left
    drawable_height = bottom - top
    data_width = max(span_x + 2.0 * pad, 1.0e-9)
    data_height = max(span_y + 2.0 * pad, 1.0e-9)
    pixels_per_unit = min(
        drawable_width / data_width,
        drawable_height / data_height,
    )
    data_centre_x = 0.5 * (min_x + max_x)
    data_centre_y = 0.5 * (min_y + max_y)
    canvas_centre_x = 0.5 * (left + right)
    canvas_centre_y = 0.5 * (top + bottom)

    def transform(point: tuple[float, float]) -> tuple[float, float]:
        x = canvas_centre_x + (
            point[0] - data_centre_x
        ) * pixels_per_unit
        y = canvas_centre_y - (
            point[1] - data_centre_y
        ) * pixels_per_unit
        return x, y

    polyline = " ".join(
        f"{x:.2f},{y:.2f}"
        for x, y in map(transform, projected)
    )
    centre_index = len(rows) // 2
    markers = (
        ("entry", 0, "#f0a34a"),
        ("centre", centre_index, "#f4f7f8"),
        ("exit", len(rows) - 1, "#55d6be"),
    )

    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" '
            f'data-model="RSH" data-version="{VERSION}" '
            f'data-pixels-per-unit="{pixels_per_unit:.17e}">'
        ),
        f"<title>{escape(title)}</title>",
        '<rect width="100%" height="100%" fill="#0b1116"/>',
        '<g opacity="0.24" stroke="#7d929e" stroke-width="1">',
    ]
    for x in range(80, width, 80):
        parts.append(
            f'<line x1="{x}" y1="0" x2="{x}" y2="{height}"/>'
        )
    for y in range(80, height, 80):
        parts.append(
            f'<line x1="0" y1="{y}" x2="{width}" y2="{y}"/>'
        )
    parts.extend(
        [
            "</g>",
            (
                '<text x="36" y="38" fill="#dce7eb" '
                'font-family="ui-monospace,monospace" '
                f'font-size="18">{escape(title)}</text>'
            ),
            (
                '<text x="36" y="63" fill="#8ca1ac" '
                'font-family="ui-monospace,monospace" '
                f'font-size="13">ψ={PSI:.9f} · '
                f'κ≤{KAPPA_MAX:.9f} · '
                'midpoint normalised to origin</text>'
            ),
            (
                f'<polyline points="{polyline}" fill="none" '
                'stroke="#55d6be" stroke-width="4" '
                'stroke-linecap="round" '
                'stroke-linejoin="round"/>'
            ),
        ]
    )
    for label, index, colour in markers:
        x, y = transform(projected[index])
        radius = 9 if label != "centre" else 12
        parts.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" '
            f'r="{radius}" fill="{colour}"/>'
        )
        if label == "centre":
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" '
                f'r="22" fill="none" stroke="{colour}" '
                'stroke-opacity="0.35" stroke-width="2"/>'
            )
        parts.append(
            f'<text x="{x + 14:.2f}" y="{y - 12:.2f}" '
            f'fill="{colour}" '
            'font-family="ui-monospace,monospace" '
            f'font-size="13">{label}</text>'
        )
    parts.append("</svg>")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")
