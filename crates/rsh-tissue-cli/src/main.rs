use rsh_tissue::{
    check_python_conformance, simulate_tissue, tissue_report_json, tissue_trace_csv,
    SidecarBackend, TissueConfig, TISSUE_CONTRACT_VERSION,
};
use serde_json::json;
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process;

#[derive(Debug)]
struct RunArgs {
    config: TissueConfig,
    json: Option<PathBuf>,
    csv: Option<PathBuf>,
}

fn usage() -> &'static str {
    "RSH Rust tissue runtime\n\n\
Usage:\n  rsh-tissue info\n  rsh-tissue run [--cells N] [--ticks N] [--geometry-samples N]\n\
                 [--ds VALUE] [--phase-coupling VALUE]\n\
                 [--binding-diffusion VALUE] [--sidecar-backend NAME]\n\
                 [--sidecar-residual VALUE] [--residual-gate VALUE]\n\
                 [--qf-floor VALUE] [--json PATH] [--csv PATH]\n  rsh-tissue conformance [--json PATH]\n"
}

fn parse_value<T: std::str::FromStr>(name: &str, value: Option<String>) -> Result<T, String> {
    value
        .ok_or_else(|| format!("missing value for {name}"))?
        .parse::<T>()
        .map_err(|_| format!("invalid value for {name}"))
}

fn parse_run_args(arguments: impl Iterator<Item = String>) -> Result<RunArgs, String> {
    let mut config = TissueConfig::default();
    let mut json_path = None;
    let mut csv_path = None;
    let mut arguments = arguments.peekable();

    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--cells" => config.cells = parse_value("cells", arguments.next())?,
            "--ticks" => config.ticks = parse_value("ticks", arguments.next())?,
            "--geometry-samples" => {
                config.geometry_samples = parse_value("geometry-samples", arguments.next())?;
            }
            "--ds" => config.ds = parse_value("ds", arguments.next())?,
            "--phase-coupling" => {
                config.phase_coupling = parse_value("phase-coupling", arguments.next())?;
            }
            "--binding-diffusion" => {
                config.binding_diffusion = parse_value("binding-diffusion", arguments.next())?;
            }
            "--sidecar-backend" => {
                let value = arguments
                    .next()
                    .ok_or_else(|| "missing value for sidecar-backend".to_string())?;
                config.sidecar_backend = SidecarBackend::from_name(&value)?;
            }
            "--sidecar-residual" => {
                config.sidecar_residual = parse_value("sidecar-residual", arguments.next())?;
            }
            "--residual-gate" => {
                config.residual_gate = parse_value("residual-gate", arguments.next())?;
            }
            "--qf-floor" => {
                config.qf_floor = parse_value("qf-floor", arguments.next())?;
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
            "-h" | "--help" => return Err(usage().into()),
            _ => return Err(format!("unknown argument: {argument}")),
        }
    }

    Ok(RunArgs {
        config: config.validate()?,
        json: json_path,
        csv: csv_path,
    })
}

fn command_info() -> Result<i32, String> {
    let payload = json!({
        "schema": "RSH-TISSUE-RUST-INFO-V1",
        "tissue_contract": TISSUE_CONTRACT_VERSION,
        "implementation": "rust-f64",
        "implementation_version": env!("CARGO_PKG_VERSION"),
        "python_reference_authority": true,
        "geometry_receipt_authority": false,
        "subjective_awareness_claim": false
    });
    println!(
        "{}",
        serde_json::to_string_pretty(&payload).map_err(|error| error.to_string())?
    );
    Ok(0)
}

fn command_run(arguments: impl Iterator<Item = String>) -> Result<i32, String> {
    let parsed = parse_run_args(arguments)?;
    let report = simulate_tissue(parsed.config)?;

    if let Some(path) = parsed.json {
        fs::write(&path, tissue_report_json(&report)?)
            .map_err(|error| format!("{}: {error}", path.display()))?;
    }
    if let Some(path) = parsed.csv {
        fs::write(&path, tissue_trace_csv(&report))
            .map_err(|error| format!("{}: {error}", path.display()))?;
    }

    println!("RSH Rust tissue [{}]", if report.pass_all { "PASS" } else { "FAIL" });
    println!("  tissue contract      = {}", report.tissue_contract);
    println!("  cells                = {}", report.config.cells);
    println!("  ticks                = {}", report.config.ticks);
    println!("  final Q_f            = {:.17e}", report.final_q_f);
    println!("  seed receipt         = {}", report.seed_geometry_receipt);
    println!("  tissue receipt       = {}", report.receipt);
    println!("  geometry authority   = false");
    println!("  awareness claim      = false");
    Ok(if report.pass_all { 0 } else { 1 })
}

fn command_conformance(arguments: impl Iterator<Item = String>) -> Result<i32, String> {
    let mut json_path = None;
    let mut arguments = arguments.peekable();
    while let Some(argument) = arguments.next() {
        match argument.as_str() {
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

    let result = check_python_conformance()?;
    let encoded = serde_json::to_string_pretty(&result).map_err(|error| error.to_string())?;
    if let Some(path) = json_path {
        fs::write(&path, format!("{encoded}\n"))
            .map_err(|error| format!("{}: {error}", path.display()))?;
    }
    println!("{encoded}");
    Ok(if result.pass { 0 } else { 1 })
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
        "conformance" => command_conformance(subcommand_arguments.into_iter()),
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
            eprintln!("rsh-tissue: {error}");
            process::exit(2);
        }
    }
}
