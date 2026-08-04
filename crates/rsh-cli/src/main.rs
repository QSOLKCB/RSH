use rsh_core::{
    build_and_verify, check_python_conformance, conformance_json, kappa_max,
    logical_sample_indices, psi, report_json, trace_csv, ModelConfig, CANONICAL_FLOAT_PRECISION,
    IMPLEMENTATION, MODEL_NAME, MODEL_VERSION,
};
use serde_json::json;
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process;

#[derive(Debug)]
struct ModelArgs {
    config: ModelConfig,
    output: Option<PathBuf>,
    json: Option<PathBuf>,
}

fn usage() -> &'static str {
    "RSH native evidence runner\n\n\
Usage:\n  rsh-rust info\n  rsh-rust verify [-n SAMPLES] [--s0 VALUE] [--s1 VALUE] [--kappa-fraction VALUE]\n\
                  [--tau-floor VALUE] [--tau-amplitude VALUE] [--json PATH]\n  rsh-rust trace [-n SAMPLES] [-o PATH]\n  rsh-rust conformance [--json PATH]\n  rsh-rust sample LOGICAL_COUNT RENDERED_COUNT\n"
}

fn parse_value<T: std::str::FromStr>(name: &str, value: Option<String>) -> Result<T, String> {
    value
        .ok_or_else(|| format!("missing value for {name}"))?
        .parse::<T>()
        .map_err(|_| format!("invalid value for {name}"))
}

fn parse_model_args(arguments: impl Iterator<Item = String>) -> Result<ModelArgs, String> {
    let mut config = ModelConfig::default();
    let mut output = None;
    let mut json_path = None;
    let mut arguments = arguments.peekable();

    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "-n" | "--samples" => {
                config.samples = parse_value("samples", arguments.next())?;
            }
            "--s0" => config.s0 = parse_value("s0", arguments.next())?,
            "--s1" => config.s1 = parse_value("s1", arguments.next())?,
            "--kappa-fraction" => {
                config.kappa_fraction = parse_value("kappa-fraction", arguments.next())?;
            }
            "--tau-floor" => {
                config.tau_floor = parse_value("tau-floor", arguments.next())?;
            }
            "--tau-amplitude" => {
                config.tau_amplitude = parse_value("tau-amplitude", arguments.next())?;
            }
            "-o" | "--output" => {
                output = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or_else(|| "missing value for output".to_string())?,
                ));
            }
            "--json" => {
                json_path = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or_else(|| "missing value for json".to_string())?,
                ));
            }
            "-h" | "--help" => return Err(usage().into()),
            _ => return Err(format!("unknown argument: {argument}")),
        }
    }

    Ok(ModelArgs {
        config: config.validate()?,
        output,
        json: json_path,
    })
}

fn command_info() -> Result<i32, String> {
    let payload = json!({
        "canonical_float_precision": CANONICAL_FLOAT_PRECISION,
        "implementation": IMPLEMENTATION,
        "implementation_version": env!("CARGO_PKG_VERSION"),
        "kappa_max": kappa_max(),
        "model": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "psi": psi(),
        "runtime": "native Rust",
        "tau_interval": "(0, 1)"
    });
    println!(
        "{}",
        serde_json::to_string_pretty(&payload).map_err(|error| error.to_string())?
    );
    Ok(0)
}

fn command_verify(arguments: impl Iterator<Item = String>) -> Result<i32, String> {
    let parsed = parse_model_args(arguments)?;
    if parsed.output.is_some() {
        return Err("verify accepts --json, not --output".into());
    }
    let (_, report) = build_and_verify(parsed.config)?;
    if let Some(path) = parsed.json {
        fs::write(&path, format!("{}\n", report_json(&report)?))
            .map_err(|error| format!("{}: {error}", path.display()))?;
    }

    let status = if report.pass_all { "PASS" } else { "FAIL" };
    println!("RSH Rust verify [{status}]");
    println!("  samples              = {}", report.samples);
    println!("  centre_error         = {:.3e}", report.centre_error);
    println!(
        "  max_kappa / bound    = {:.6} / {:.6}",
        report.max_kappa, report.kappa_bound
    );
    println!(
        "  tau range            = [{:.6}, {:.6}]",
        report.min_tau, report.max_tau
    );
    println!(
        "  frame_norm_error     = {:.3e}",
        report.max_frame_norm_error
    );
    println!(
        "  frame_orthogonality  = {:.3e}",
        report.max_frame_orthogonality_error
    );
    println!("  receipt              = {}", report.receipt);
    Ok(if report.pass_all { 0 } else { 1 })
}

fn command_trace(arguments: impl Iterator<Item = String>) -> Result<i32, String> {
    let parsed = parse_model_args(arguments)?;
    if parsed.json.is_some() {
        return Err("trace accepts --output, not --json".into());
    }
    let (rows, _) = build_and_verify(parsed.config)?;
    let path = parsed
        .output
        .unwrap_or_else(|| PathBuf::from("rsh_trace_rust.csv"));
    fs::write(&path, trace_csv(&rows)).map_err(|error| format!("{}: {error}", path.display()))?;
    println!(
        "RSH Rust trace -> {} ({} samples)",
        path.display(),
        rows.len()
    );
    Ok(0)
}

fn command_conformance(arguments: impl Iterator<Item = String>) -> Result<i32, String> {
    let arguments = arguments.collect::<Vec<_>>();
    let mut json_path = None;
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--json" => {
                index += 1;
                json_path = Some(PathBuf::from(
                    arguments
                        .get(index)
                        .ok_or_else(|| "missing value for json".to_string())?,
                ));
            }
            "-h" | "--help" => return Err(usage().into()),
            other => return Err(format!("unknown argument: {other}")),
        }
        index += 1;
    }

    let result = check_python_conformance()?;
    if let Some(path) = json_path {
        fs::write(&path, format!("{}\n", conformance_json(&result)?))
            .map_err(|error| format!("{}: {error}", path.display()))?;
    }
    let status = if result.pass { "PASS" } else { "FAIL" };
    println!("RSH Rust conformance [{status}]");
    println!(
        "  entry_max_abs_error  = {:.3e}",
        result.entry_max_abs_error
    );
    println!("  exit_max_abs_error   = {:.3e}", result.exit_max_abs_error);
    println!(
        "  tolerance            = {:.3e}",
        result.coordinate_tolerance
    );
    println!("  rust_receipt         = {}", result.rust_receipt);
    println!("  python_receipt       = {}", result.python_golden_receipt);
    println!("  receipt_identical    = {}", result.receipt_identical);
    Ok(if result.pass { 0 } else { 1 })
}

fn command_sample(mut arguments: impl Iterator<Item = String>) -> Result<i32, String> {
    let logical_count: u64 = parse_value("logical_count", arguments.next())?;
    let rendered_count: u64 = parse_value("rendered_count", arguments.next())?;
    if let Some(extra) = arguments.next() {
        return Err(format!("unexpected argument: {extra}"));
    }
    let indices = logical_sample_indices(logical_count, rendered_count)?;
    println!("rendered_index,logical_index");
    for (rendered_index, logical_index) in indices.into_iter().enumerate() {
        println!("{rendered_index},{logical_index}");
    }
    Ok(0)
}

fn run() -> Result<i32, String> {
    let arguments = env::args().skip(1).collect::<Vec<_>>();
    let command = arguments.first().map(String::as_str).unwrap_or("help");
    let subcommand_arguments = arguments.iter().skip(1).cloned().collect::<Vec<_>>();

    if subcommand_arguments
        .iter()
        .any(|argument| matches!(argument.as_str(), "-h" | "--help"))
    {
        print!("{}", usage());
        return Ok(0);
    }

    match command {
        "info" => command_info(),
        "verify" => command_verify(subcommand_arguments.into_iter()),
        "trace" => command_trace(subcommand_arguments.into_iter()),
        "conformance" => command_conformance(subcommand_arguments.into_iter()),
        "sample" => command_sample(subcommand_arguments.into_iter()),
        "help" | "-h" | "--help" => {
            print!("{}", usage());
            Ok(0)
        }
        _ => Err(format!("unknown command: {command}\n\n{}", usage())),
    }
}

fn main() {
    match run() {
        Ok(code) => process::exit(code),
        Err(error) => {
            eprintln!("rsh-rust: {error}");
            process::exit(2);
        }
    }
}
