use rsh_core::ModelConfig;
use rsh_parallel::{
    build_parallel_path, build_shard_prefix_path, merge_segment_summaries, report_json,
    segment_summaries, shard_bundle_json, shard_report_json, trace_csv, INTERVAL_POLICY,
    LOCAL_PREFIX_POLICY, PARALLEL_CONTRACT, SCAN_POLICY, SHARD_ASSEMBLY_POLICY,
    SHARD_FINGERPRINT_POLICY, SHARD_PREFIX_CONTRACT, SHARD_PREFIX_POLICY,
};
use serde_json::json;
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process;
use std::time::Instant;

fn usage() -> &'static str {
    "RSH parallel Frenet research\n\n\
Usage:\n  rsh-parallel info\n  rsh-parallel run [--samples N] [--s0 VALUE] [--s1 VALUE]\n\
                   [--kappa-fraction VALUE] [--tau-floor VALUE]\n\
                   [--tau-amplitude VALUE] [--json PATH] [--csv PATH]\n  rsh-parallel shards [--samples N] [--interval-width N] [--json PATH]\n  rsh-parallel reconstruct [--samples N] [--interval-width N]\n\
                         [--s0 VALUE] [--s1 VALUE]\n\
                         [--kappa-fraction VALUE] [--tau-floor VALUE]\n\
                         [--tau-amplitude VALUE] [--json PATH] [--csv PATH]\n\
                         [--shards-json PATH]\n  rsh-parallel benchmark [--samples N] [--loops N] [--json PATH]\n"
}

fn parse_value<T: std::str::FromStr>(name: &str, value: Option<String>) -> Result<T, String> {
    value
        .ok_or_else(|| format!("missing value for {name}"))?
        .parse::<T>()
        .map_err(|_| format!("invalid value for {name}"))
}

#[derive(Debug)]
struct CommonArgs {
    config: ModelConfig,
    json: Option<PathBuf>,
    csv: Option<PathBuf>,
}

fn parse_common(arguments: impl Iterator<Item = String>) -> Result<CommonArgs, String> {
    let mut config = ModelConfig {
        samples: 1025,
        ..ModelConfig::default()
    };
    let mut json = None;
    let mut csv = None;
    let mut arguments = arguments.peekable();
    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--samples" => config.samples = parse_value("samples", arguments.next())?,
            "--s0" => config.s0 = parse_value("s0", arguments.next())?,
            "--s1" => config.s1 = parse_value("s1", arguments.next())?,
            "--kappa-fraction" => {
                config.kappa_fraction = parse_value("kappa-fraction", arguments.next())?;
            }
            "--tau-floor" => config.tau_floor = parse_value("tau-floor", arguments.next())?,
            "--tau-amplitude" => {
                config.tau_amplitude = parse_value("tau-amplitude", arguments.next())?;
            }
            "--json" => {
                json = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or_else(|| "missing value for json".to_string())?,
                ));
            }
            "--csv" => {
                csv = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or_else(|| "missing value for csv".to_string())?,
                ));
            }
            "-h" | "--help" => return Err(usage().into()),
            _ => return Err(format!("unknown argument: {argument}")),
        }
    }
    Ok(CommonArgs {
        config: config.validate()?,
        json,
        csv,
    })
}

#[derive(Debug)]
struct ReconstructArgs {
    config: ModelConfig,
    interval_width: usize,
    json: Option<PathBuf>,
    csv: Option<PathBuf>,
    shards_json: Option<PathBuf>,
}

fn parse_reconstruct(arguments: impl Iterator<Item = String>) -> Result<ReconstructArgs, String> {
    let mut config = ModelConfig {
        samples: 4097,
        ..ModelConfig::default()
    };
    let mut interval_width = 257usize;
    let mut json = None;
    let mut csv = None;
    let mut shards_json = None;
    let mut arguments = arguments.peekable();
    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--samples" => config.samples = parse_value("samples", arguments.next())?,
            "--interval-width" => {
                interval_width = parse_value("interval-width", arguments.next())?;
            }
            "--s0" => config.s0 = parse_value("s0", arguments.next())?,
            "--s1" => config.s1 = parse_value("s1", arguments.next())?,
            "--kappa-fraction" => {
                config.kappa_fraction = parse_value("kappa-fraction", arguments.next())?;
            }
            "--tau-floor" => config.tau_floor = parse_value("tau-floor", arguments.next())?,
            "--tau-amplitude" => {
                config.tau_amplitude = parse_value("tau-amplitude", arguments.next())?;
            }
            "--json" => {
                json = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or_else(|| "missing value for json".to_string())?,
                ));
            }
            "--csv" => {
                csv = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or_else(|| "missing value for csv".to_string())?,
                ));
            }
            "--shards-json" => {
                shards_json =
                    Some(PathBuf::from(arguments.next().ok_or_else(|| {
                        "missing value for shards-json".to_string()
                    })?));
            }
            "-h" | "--help" => return Err(usage().into()),
            _ => return Err(format!("unknown argument: {argument}")),
        }
    }
    Ok(ReconstructArgs {
        config: config.validate()?,
        interval_width,
        json,
        csv,
        shards_json,
    })
}

fn write_optional(path: Option<PathBuf>, content: String) -> Result<(), String> {
    if let Some(path) = path {
        fs::write(&path, content).map_err(|error| format!("{}: {error}", path.display()))?;
    }
    Ok(())
}

fn command_info() -> Result<i32, String> {
    println!(
        "{}",
        serde_json::to_string_pretty(&json!({
            "schema": "RSH-FRENET-PARALLEL-INFO-V2",
            "parallel_contract": PARALLEL_CONTRACT,
            "interval_policy": INTERVAL_POLICY,
            "scan_policy": SCAN_POLICY,
            "shard_prefix_contract": SHARD_PREFIX_CONTRACT,
            "local_prefix_policy": LOCAL_PREFIX_POLICY,
            "shard_prefix_policy": SHARD_PREFIX_POLICY,
            "shard_assembly_policy": SHARD_ASSEMBLY_POLICY,
            "shard_fingerprint_policy": SHARD_FINGERPRINT_POLICY,
            "implementation": "rust-f64",
            "implementation_version": env!("CARGO_PKG_VERSION"),
            "actual_parallel_hardware_execution": false,
            "actual_multi_device_execution": false,
            "distributed_execution": false,
            "speedup_claim": false,
            "geometry_receipt_authority": false
        }))
        .map_err(|error| error.to_string())?
    );
    Ok(0)
}

fn command_run(arguments: impl Iterator<Item = String>) -> Result<i32, String> {
    let parsed = parse_common(arguments)?;
    let (points, report) = build_parallel_path(parsed.config)?;
    write_optional(parsed.json, format!("{}\n", report_json(&report)?))?;
    write_optional(parsed.csv, trace_csv(&points))?;

    println!(
        "RSH parallel Frenet [{}]",
        if report.pass_all { "PASS" } else { "FAIL" }
    );
    println!("  contract             = {}", report.parallel_contract);
    println!(
        "  samples / intervals  = {} / {}",
        report.samples, report.intervals
    );
    println!("  scan passes          = {}", report.scan_passes);
    println!(
        "  scan residual        = {:.6e}",
        report.max_scan_vs_sequential_component_error
    );
    println!(
        "  shard residual       = {:.6e}",
        report.max_shard_merge_component_error
    );
    println!("  speedup claim        = false");
    println!("  geometry authority   = false");
    Ok(if report.pass_all { 0 } else { 1 })
}

fn command_shards(arguments: impl Iterator<Item = String>) -> Result<i32, String> {
    let mut config = ModelConfig {
        samples: 1025,
        ..ModelConfig::default()
    };
    let mut interval_width = 128usize;
    let mut json_path = None;
    let mut arguments = arguments.peekable();
    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--samples" => config.samples = parse_value("samples", arguments.next())?,
            "--interval-width" => {
                interval_width = parse_value("interval-width", arguments.next())?;
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
    let config = config.validate()?;
    let expected_intervals = config.samples - 1;
    let summaries = segment_summaries(config, interval_width)?;
    let merged = merge_segment_summaries(&summaries, expected_intervals)?;
    let payload = json!({
        "schema": "RSH-FRENET-PARALLEL-SHARDS-V1",
        "parallel_contract": PARALLEL_CONTRACT,
        "configuration": {
            "samples": config.samples,
            "s0": config.s0,
            "s1": config.s1,
            "kappa_fraction": config.kappa_fraction,
            "tau_floor": config.tau_floor,
            "tau_amplitude": config.tau_amplitude
        },
        "expected_intervals": expected_intervals,
        "interval_width": interval_width,
        "shard_count": summaries.len(),
        "summaries": summaries,
        "merged_transform": merged,
        "distributed_execution": false,
        "geometry_receipt_authority": false,
        "evidence_note": "These deterministic local reductions cover the declared interval range and define ordered shard composition only. They do not claim networked or multi-device execution."
    });
    let encoded = format!(
        "{}\n",
        serde_json::to_string_pretty(&payload).map_err(|error| error.to_string())?
    );
    write_optional(json_path, encoded.clone())?;
    print!("{encoded}");
    Ok(0)
}

fn command_reconstruct(arguments: impl Iterator<Item = String>) -> Result<i32, String> {
    let parsed = parse_reconstruct(arguments)?;
    let result = build_shard_prefix_path(parsed.config, parsed.interval_width)?;
    write_optional(
        parsed.json,
        format!("{}\n", shard_report_json(&result.report)?),
    )?;
    write_optional(parsed.csv, trace_csv(&result.points))?;
    write_optional(
        parsed.shards_json,
        format!("{}\n", shard_bundle_json(&result.bundle)?),
    )?;

    println!(
        "RSH shard-prefix reconstruction [{}]",
        if result.report.pass_all {
            "PASS"
        } else {
            "FAIL"
        }
    );
    println!(
        "  contract             = {}",
        result.report.shard_prefix_contract
    );
    println!(
        "  samples / intervals  = {} / {}",
        result.report.samples, result.report.intervals
    );
    println!(
        "  shard width / count  = {} / {}",
        result.report.interval_width, result.report.shard_count
    );
    println!(
        "  shard prefix passes  = {}",
        result.report.shard_prefix_passes
    );
    println!(
        "  reconstruction error = {:.6e}",
        result.report.max_reconstruction_vs_parallel_component_error
    );
    println!(
        "  manifest fingerprint = {}",
        result.report.manifest_fingerprint
    );
    println!("  multi-device         = false");
    println!("  distributed          = false");
    println!("  speedup claim        = false");
    println!("  geometry authority   = false");
    Ok(if result.report.pass_all { 0 } else { 1 })
}

fn median(values: &mut [f64]) -> f64 {
    values.sort_by(f64::total_cmp);
    let middle = values.len() / 2;
    if values.len().is_multiple_of(2) {
        0.5 * (values[middle - 1] + values[middle])
    } else {
        values[middle]
    }
}

fn command_benchmark(arguments: impl Iterator<Item = String>) -> Result<i32, String> {
    let mut config = ModelConfig {
        samples: 16_385,
        ..ModelConfig::default()
    };
    let mut loops = 10usize;
    let mut json_path = None;
    let mut arguments = arguments.peekable();
    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--samples" => config.samples = parse_value("samples", arguments.next())?,
            "--loops" => loops = parse_value("loops", arguments.next())?,
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
    let config = config.validate()?;
    if !(1..=1000).contains(&loops) {
        return Err("loops must be in [1, 1000]".into());
    }

    let (points, report) = build_parallel_path(config)?;
    if !report.pass_all || points.len() != config.samples {
        return Err("parallel benchmark preflight did not pass".into());
    }

    let mut milliseconds = Vec::with_capacity(loops);
    for _ in 0..loops {
        let started = Instant::now();
        let (_, run_report) = build_parallel_path(config)?;
        if !run_report.pass_all {
            return Err("parallel benchmark iteration failed conformance".into());
        }
        milliseconds.push(started.elapsed().as_secs_f64() * 1000.0);
    }
    let median_milliseconds = median(&mut milliseconds);
    let payload = json!({
        "schema": "RSH-FRENET-PARALLEL-CPU-BENCHMARK-V1",
        "parallel_contract": PARALLEL_CONTRACT,
        "implementation": "rust-f64-single-process",
        "samples": config.samples,
        "loops": loops,
        "median_milliseconds": median_milliseconds,
        "observations_milliseconds": milliseconds,
        "actual_parallel_hardware_execution": false,
        "speedup_claim": false,
        "geometry_receipt_authority": false,
        "evidence_note": "This command times the deterministic CPU reference. It is not a GPU or distributed speedup result."
    });
    let encoded = format!(
        "{}\n",
        serde_json::to_string_pretty(&payload).map_err(|error| error.to_string())?
    );
    write_optional(json_path, encoded.clone())?;
    print!("{encoded}");
    Ok(0)
}

fn run() -> Result<i32, String> {
    let arguments = env::args().skip(1).collect::<Vec<_>>();
    let command = arguments.first().map(String::as_str).unwrap_or("help");
    let rest = arguments.iter().skip(1).cloned().collect::<Vec<_>>();
    if rest
        .iter()
        .any(|argument| matches!(argument.as_str(), "-h" | "--help"))
    {
        print!("{}", usage());
        return Ok(0);
    }

    match command {
        "info" => command_info(),
        "run" => command_run(rest.into_iter()),
        "shards" => command_shards(rest.into_iter()),
        "reconstruct" => command_reconstruct(rest.into_iter()),
        "benchmark" => command_benchmark(rest.into_iter()),
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
            eprintln!("rsh-parallel: {error}");
            process::exit(2);
        }
    }
}
