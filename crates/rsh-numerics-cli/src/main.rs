use rsh_core::ModelConfig;
use rsh_numerics::{build_lie_path, report_json, trace_csv, INTEGRATOR, NUMERICAL_CONTRACT};
use serde_json::json;
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process;
use std::time::Instant;

#[derive(Debug)]
struct RunArgs {
    config: ModelConfig,
    json: Option<PathBuf>,
    csv: Option<PathBuf>,
    loops: usize,
}

fn usage() -> &'static str {
    "RSH separately versioned Frenet numerical research runner\n\n\
Usage:\n  rsh-frenet info\n  rsh-frenet run [-n SAMPLES] [--s0 VALUE] [--s1 VALUE]\n\
                 [--kappa-fraction VALUE] [--tau-floor VALUE]\n\
                 [--tau-amplitude VALUE] [--json PATH] [--csv PATH]\n  rsh-frenet benchmark [-n SAMPLES] [--loops N]\n"
}

fn parse_value<T: std::str::FromStr>(name: &str, value: Option<String>) -> Result<T, String> {
    value
        .ok_or_else(|| format!("missing value for {name}"))?
        .parse::<T>()
        .map_err(|_| format!("invalid value for {name}"))
}

fn parse_run_args(arguments: impl Iterator<Item = String>) -> Result<RunArgs, String> {
    let mut config = ModelConfig {
        samples: 1025,
        ..ModelConfig::default()
    };
    let mut json_path = None;
    let mut csv_path = None;
    let mut loops = 20_usize;
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
            "--json" => {
                json_path = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or_else(|| "missing value for json".to_string())?,
                ));
            }
            "--csv" => {
                csv_path = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or_else(|| "missing value for csv".to_string())?,
                ));
            }
            "--loops" => loops = parse_value("loops", arguments.next())?,
            "-h" | "--help" => return Err(usage().into()),
            _ => return Err(format!("unknown argument: {argument}")),
        }
    }

    if loops == 0 || loops > 10_000 {
        return Err("loops must be in [1, 10000]".into());
    }

    Ok(RunArgs {
        config: config.validate()?,
        json: json_path,
        csv: csv_path,
        loops,
    })
}

fn command_info() -> Result<i32, String> {
    let payload = json!({
        "schema": "RSH-FRENET-NUMERICS-INFO-V1",
        "numerical_contract": NUMERICAL_CONTRACT,
        "integrator": INTEGRATOR,
        "implementation": "rust-f64",
        "implementation_version": env!("CARGO_PKG_VERSION"),
        "canonical_geometry_authority": false,
        "speedup_claim": false,
        "purpose": "path-level reference and accelerator conformance research"
    });
    println!(
        "{}",
        serde_json::to_string_pretty(&payload).map_err(|error| error.to_string())?
    );
    Ok(0)
}

fn command_run(arguments: impl Iterator<Item = String>) -> Result<i32, String> {
    let parsed = parse_run_args(arguments)?;
    let (rows, report) = build_lie_path(parsed.config)?;

    if let Some(path) = parsed.json {
        fs::write(&path, format!("{}\n", report_json(&report)?))
            .map_err(|error| format!("{}: {error}", path.display()))?;
    }
    if let Some(path) = parsed.csv {
        fs::write(&path, trace_csv(&rows))
            .map_err(|error| format!("{}: {error}", path.display()))?;
    }

    let status = if report.pass_all { "PASS" } else { "FAIL" };
    println!("RSH Frenet numerical path [{status}]");
    println!("  contract             = {}", report.numerical_contract);
    println!("  integrator           = {}", report.integrator);
    println!("  samples              = {}", report.samples);
    println!(
        "  centre_error         = {:.3e}",
        report
            .centre
            .iter()
            .map(|value| value * value)
            .sum::<f64>()
            .sqrt()
    );
    println!(
        "  frame_norm_error     = {:.3e}",
        report.max_frame_norm_error
    );
    println!(
        "  frame_orthogonality  = {:.3e}",
        report.max_frame_orthogonality_error
    );
    println!("  geometry_authority   = false");
    println!("  speedup_claim        = false");
    Ok(if report.pass_all { 0 } else { 1 })
}

fn command_benchmark(arguments: impl Iterator<Item = String>) -> Result<i32, String> {
    let parsed = parse_run_args(arguments)?;
    if parsed.json.is_some() || parsed.csv.is_some() {
        return Err("benchmark does not accept --json or --csv".into());
    }

    let started = Instant::now();
    let mut last_report = None;
    for _ in 0..parsed.loops {
        let (_, report) = build_lie_path(parsed.config)?;
        last_report = Some(report);
    }
    let elapsed = started.elapsed();
    let report = last_report.ok_or_else(|| "benchmark produced no report".to_string())?;
    let total_seconds = elapsed.as_secs_f64();
    let payload = json!({
        "schema": "RSH-FRENET-BENCHMARK-V1",
        "numerical_contract": NUMERICAL_CONTRACT,
        "integrator": INTEGRATOR,
        "samples": report.samples,
        "loops": parsed.loops,
        "total_seconds": total_seconds,
        "mean_seconds": total_seconds / parsed.loops as f64,
        "pass_all": report.pass_all,
        "performance_gate": false,
        "speedup_claim": false
    });
    println!(
        "{}",
        serde_json::to_string_pretty(&payload).map_err(|error| error.to_string())?
    );
    Ok(if report.pass_all { 0 } else { 1 })
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
        "run" => command_run(subcommand_arguments.into_iter()),
        "benchmark" => command_benchmark(subcommand_arguments.into_iter()),
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
            eprintln!("rsh-frenet: {error}");
            process::exit(2);
        }
    }
}
