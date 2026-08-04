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
from .constitution import constitution_report
from .evidence import (
    benchmark,
    build_and_verify,
    verify_parallel,
    write_report_json,
    write_trace_csv,
    write_verify_csv,
)
from .geometry import ModelConfig, build_path, logical_sample_indices
from .refinement import (
    evaluate_refinement,
    load_proposal,
    write_decision_json,
)
from .tissue import (
    TISSUE_CONTRACT_VERSION,
    TissueConfig,
    simulate_tissue,
    write_tissue_report_json,
    write_tissue_trace_csv,
)
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


def _tissue_config_from_args(args: argparse.Namespace) -> TissueConfig:
    return TissueConfig(
        cells=args.cells,
        ticks=args.ticks,
        geometry_samples=args.geometry_samples,
        ds=args.ds,
        phase_coupling=args.phase_coupling,
        binding_diffusion=args.binding_diffusion,
        sidecar_backend=args.sidecar_backend,
        sidecar_residual=args.sidecar_residual,
        residual_gate=args.residual_gate,
        qf_floor=args.qf_floor,
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


def _add_tissue_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cells", type=int, default=8)
    parser.add_argument("--ticks", type=int, default=20)
    parser.add_argument(
        "--geometry-samples",
        type=int,
        default=129,
        help="odd f64 geometry seed grid (default: 129)",
    )
    parser.add_argument("--ds", type=float, default=0.05)
    parser.add_argument("--phase-coupling", type=float, default=0.25)
    parser.add_argument("--binding-diffusion", type=float, default=0.15)
    parser.add_argument(
        "--sidecar-backend",
        choices=("none", "webgpu", "cuda", "npu"),
        default="none",
    )
    parser.add_argument("--sidecar-residual", type=float, default=0.0)
    parser.add_argument("--residual-gate", type=float, default=1.0e-4)
    parser.add_argument("--qf-floor", type=float, default=0.0)


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

    constitution_parser = subparsers.add_parser(
        "constitution",
        help="show the machine-checkable tissue constitution",
    )
    constitution_parser.add_argument(
        "--json",
        default="",
        help="optional JSON report path",
    )

    tissue_parser = subparsers.add_parser(
        "tissue",
        help="run the deterministic geometric tissue reference",
    )
    _add_tissue_arguments(tissue_parser)
    tissue_parser.add_argument(
        "--json",
        default="",
        help="optional complete tissue report path",
    )
    tissue_parser.add_argument(
        "--trace",
        default="",
        help="optional per-tick CSV path",
    )

    refinement_parser = subparsers.add_parser(
        "refine-dry-run",
        help="evaluate and seal one bounded tissue proposal",
    )
    refinement_parser.add_argument("proposal", help="proposal JSON path")
    refinement_parser.add_argument(
        "--json",
        default="",
        help="optional decision report path",
    )

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
                        "tissue_contract": TISSUE_CONTRACT_VERSION,
                        "tissue_semantics": (
                            "functional systems simulation; no subjective "
                            "awareness or qualia claim"
                        ),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "constitution":
            report = constitution_report()
            encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
            print(encoded, end="")
            if args.json:
                output = Path(args.json)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(encoded, encoding="utf-8")
            return 0 if report["pass_all"] else 1

        if args.command == "tissue":
            report = simulate_tissue(_tissue_config_from_args(args))
            if args.json:
                write_tissue_report_json(report, args.json)
            if args.trace:
                write_tissue_trace_csv(report, args.trace)
            status = "PASS" if report.pass_all else "FAIL"
            print(f"RSH tissue [{status}]")
            print(f"  cells / ticks        = {report.config.cells} / {report.config.ticks}")
            print(f"  seed_geometry        = {report.seed_geometry_receipt}")
            print(f"  tissue_contract      = {TISSUE_CONTRACT_VERSION}")
            print(f"  final_Q_f            = {report.final_q_f:.12f}")
            print(f"  Q_f range            = [{report.min_q_f:.12f}, {report.max_q_f:.12f}]")
            print(f"  audit_chain_valid    = {str(report.audit_chain_valid).lower()}")
            print(f"  sidecar_accepted     = {str(report.sidecar_accepted).lower()}")
            print(f"  fallback_used        = {str(report.fallback_used).lower()}")
            print(f"  receipt              = {report.receipt}")
            return 0 if report.pass_all else 1

        if args.command == "refine-dry-run":
            proposal = load_proposal(args.proposal)
            decision = evaluate_refinement(proposal)
            if args.json:
                write_decision_json(decision, args.json)
            print(f"RSH refinement [{decision.disposition}]")
            print(f"  proposal             = {decision.proposal_id}")
            print(f"  reason               = {decision.reason}")
            print(f"  dry_run_only         = {str(decision.dry_run_only).lower()}")
            print(f"  human_ack_required   = {str(decision.human_ack_required).lower()}")
            print(f"  intent_token         = {decision.intent_token}")
            print(f"  receipt              = {decision.receipt}")
            return 0 if decision.disposition == "KEEP_CANDIDATE" else 1

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
