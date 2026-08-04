#!/usr/bin/env python3
"""Create a deterministic evidence ZIP and external SHA-256 receipt.

The manifest hashes evidence files but intentionally does not attempt to hash
itself or the final archive. The archive receipt is emitted beside the ZIP.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import stat
import zipfile

MANIFEST_NAME = "SHA256SUMS.txt"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evidence_files(root: Path) -> list[Path]:
    excluded_suffixes = (".zip", ".zip.sha256")
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.as_posix() == MANIFEST_NAME:
            continue
        if path.name.endswith(excluded_suffixes):
            continue
        files.append(relative)
    return sorted(files, key=lambda value: value.as_posix())


def write_manifest(root: Path, files: list[Path]) -> Path:
    manifest = root / MANIFEST_NAME
    lines = [f"{sha256_file(root / relative)}  {relative.as_posix()}\n" for relative in files]
    manifest.write_text("".join(lines), encoding="utf-8", newline="\n")
    return manifest


def add_file(archive: zipfile.ZipFile, root: Path, relative: Path, prefix: str) -> None:
    source = root / relative
    archive_name = f"{prefix}/{relative.as_posix()}" if prefix else relative.as_posix()
    info = zipfile.ZipInfo(archive_name, ZIP_TIMESTAMP)
    mode = source.stat().st_mode
    permissions = 0o755 if mode & stat.S_IXUSR else 0o644
    info.external_attr = (permissions & 0xFFFF) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, source.read_bytes())


def package_evidence(root: Path, output: Path, prefix: str | None = None) -> tuple[Path, Path]:
    root = root.resolve()
    output = output.resolve()
    if not root.is_dir():
        raise ValueError(f"evidence directory does not exist: {root}")
    if output.parent == root or root in output.parents:
        raise ValueError("output ZIP must live outside the evidence directory")

    files = evidence_files(root)
    manifest = write_manifest(root, files)
    archive_files = [*files, manifest.relative_to(root)]
    archive_prefix = root.name if prefix is None else prefix.strip("/")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "w") as archive:
            for relative in archive_files:
                add_file(archive, root, relative, archive_prefix)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()

    receipt = output.with_suffix(output.suffix + ".sha256")
    receipt.write_text(
        f"{sha256_file(output)}  {output.name}\n",
        encoding="utf-8",
        newline="\n",
    )
    return output, receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_dir", type=Path)
    parser.add_argument("output_zip", type=Path)
    parser.add_argument(
        "--prefix",
        default=None,
        help="archive directory prefix (default: evidence directory name)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    archive, receipt = package_evidence(args.evidence_dir, args.output_zip, args.prefix)
    print(archive)
    print(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
