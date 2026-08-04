"""Command-line interface for RSH."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .constants import (
    KAPPA_MAX,
    MODEL_NAME,
    PSI,
    RECEIPT_DOMAIN,
    TAU_MAX_EXCLUSIVE,
    TAU_MIN_EXCLUSIVE,
    VERSION,
)
from .evidence import (
    benchmark,
    build_and_verify,
    verify_parallel,
    write_report_json,
    write_trace_csv,
    write_verify_csv,
)
from .geometry import ModelConfig, build_path, logical_sample_indices
from .visual import write_svg


def _config_from_args(args: argparse.Namespace) -> ModelConfig:
    return ModelConfig(
        samples=args.samples,
        s0=args.s0,
        s1=args.s1,
        kappa_fraction=args.kappa_fraction,
        tau_floor=args.tau_floor,
        tau_amplitude=args.tau_amplitude,
    ).validate()


def _add_model_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-n",
        "--samples",
        type=int,
        default=513,
        help="odd sample count (default: 513)",
    )
    parser.add_argument("--s0", type=float, default=0.0, help="arc-length start")
    parser.add_argument("--s1", type=float, default=4.0, help="arc-length end")
    parser.add_argument(
        "--kappa-fraction",
        type=float,
        default=0.85,
        help="fraction of the curvature bound",
    )
    parser.add_argument(
        "--tau-floor",
        type=float,
        default=0.22,
        help="minimum torsion",
    )
    parser.add_argument(
        "--tau-amplitude",
        type=float,
        default=0.13,
        help="half-width of torsion modulation",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rsh",
        description=(
            "Robitaille–Slade Helix: bounded Frenet–Serret geometry "
            "and deterministic evidence"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("info", help="show immutable model information")

    for command, help_text in (
        ("verify", "verify all geometric and replay contracts"),
        ("trace", "write the complete sample trace as CSV"),
        ("visual", "write a dependency-free SVG view"),
        ("receipt", "print the canonical receipt and replay status"),
        ("parity", "compare independent concurrent replays"),
        ("benchmark", "time repeated build-and-verify loops"),
    ):
        command_parser = subparsers.add_parser(command, help=help_text)
        _add_model_arguments(command_parser)
        if command in {"verify", "trace", "visual"}:
            command_parser.add_argument(
                "-o",
                "--output",
                default="",
                help="output file",
            )
        if command == "verify":
            command_parser.add_argument(
                "--json",
                default="",
                help="optional JSON report path",
            )
        if command == "parity":
            command_parser.add_argument("--workers", type=int, default=4)
        if command == "benchmark":
            command_parser.add_argument("--loops", type=int, default=20)

    sample_parser = subparsers.add_parser(
        "sample",
        help="emit exact bounded logical sample indices",
    )
    sample_parser.add_argument("logical_count", type=int)
    sample_parser.add_argument("rendered_count", type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "info":
            print(
                json.dumps(
                    {
                        "model": MODEL_NAME,
                        "version": VERSION,
                        "psi": PSI,
                        "kappa_max": KAPPA_MAX,
                        "tau_interval": (
                            f"({TAU_MIN_EXCLUSIVE:g}, "
                            f"{TAU_MAX_EXCLUSIVE:g})"
                        ),
                        "construction": (
                            "prescribed curvature/torsion -> "
                            "Frenet-Serret integration -> "
                            "midpoint coordinate normalisation"
                        ),
                        "receipt_domain_hex": RECEIPT_DOMAIN.hex(),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "sample":
            indices = logical_sample_indices(
                args.logical_count,
                args.rendered_count,
            )
            print("rendered_index,logical_index")
            for rendered_index, logical_index in enumerate(indices):
                print(f"{rendered_index},{logical_index}")
            return 0

        config = _config_from_args(args)

        if args.command == "trace":
            rows = build_path(config)
            output = Path(args.output or "rsh_trace.csv")
            write_trace_csv(rows, output)
            print(f"RSH trace -> {output} ({len(rows)} samples)")
            return 0

        if args.command == "visual":
            rows = build_path(config)
            output = Path(args.output or "rsh_visual.svg")
            write_svg(rows, output)
            print(f"RSH visual -> {output}")
            return 0

        if args.command == "parity":
            baseline, reports, parity_ok = verify_parallel(
                config,
                args.workers,
            )
            print(f"baseline_receipt={baseline.receipt}")
            for index, item in enumerate(reports):
                print(f"worker_{index}_receipt={item.receipt}")
            print(f"parity_ok={str(parity_ok).lower()}")
            return 0 if parity_ok else 1

        if args.command == "benchmark":
            print(
                json.dumps(
                    benchmark(config, args.loops),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        _rows, report = build_and_verify(config)

        if args.command == "verify":
            output = Path(args.output or "rsh_verify.csv")
            write_verify_csv(report, output)
            if args.json:
                write_report_json(report, args.json)
            status = "PASS" if report.pass_all else "FAIL"
            print(f"RSH verify [{status}] -> {output}")
            print(
                f"  centre_parameter     = "
                f"{report.centre_parameter:.6f}"
            )
            print(f"  centre_error         = {report.centre_error:.3e}")
            print(
                f"  max_kappa / bound    = "
                f"{report.max_kappa:.6f} / "
                f"{report.kappa_bound:.6f}"
            )
            print(
                f"  tau range            = "
                f"[{report.min_tau:.6f}, {report.max_tau:.6f}]"
            )
            print(
                f"  frame_norm_error     = "
                f"{report.max_frame_norm_error:.3e}"
            )
            print(
                f"  frame_orthogonality  = "
                f"{report.max_frame_orthogonality_error:.3e}"
            )
            print(f"  receipt              = {report.receipt}")
            return 0 if report.pass_all else 1

        if args.command == "receipt":
            second = build_and_verify(config)[1]
            replay_identical = report.receipt == second.receipt
            print(report.receipt)
            print(
                f"replay_identical="
                f"{str(replay_identical).lower()}"
            )
            return 0 if replay_identical else 1

    except (OSError, ValueError) as error:
        parser.exit(2, f"rsh: error: {error}\n")

    return 2
