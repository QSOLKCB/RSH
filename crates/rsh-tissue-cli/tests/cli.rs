use std::process::Command;

fn tissue_command() -> Command {
    Command::new(env!("CARGO_BIN_EXE_rsh-tissue"))
}

#[test]
fn help_lists_the_supported_commands() {
    let output = tissue_command().arg("--help").output().expect("run help");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("UTF-8 help output");
    assert!(stdout.contains("rsh-tissue run"));
    assert!(stdout.contains("rsh-tissue conformance"));
}

#[test]
fn valid_overrides_execute_the_runtime() {
    let output = tissue_command()
        .args([
            "run",
            "--cells",
            "6",
            "--ticks",
            "1",
            "--geometry-samples",
            "129",
            "--phase-coupling",
            "0.4",
            "--binding-diffusion",
            "0.2",
        ])
        .output()
        .expect("run tissue CLI");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8(output.stdout).expect("UTF-8 run output");
    assert!(stdout.contains("RSH Rust tissue [PASS]"));
    assert!(stdout.contains("cells                = 6"));
    assert!(stdout.contains("ticks                = 1"));
}

#[test]
fn unknown_arguments_return_usage_error_status() {
    let output = tissue_command()
        .args(["run", "--definitely-not-a-tissue-option"])
        .output()
        .expect("run invalid option");
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("unknown argument"));
}

#[test]
fn missing_values_return_usage_error_status() {
    let output = tissue_command()
        .args(["run", "--ticks"])
        .output()
        .expect("run missing value");
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("missing value for ticks"));
}

#[test]
fn invalid_count_ranges_are_rejected_before_simulation() {
    let output = tissue_command()
        .args(["run", "--cells", "2"])
        .output()
        .expect("run invalid count");
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("cells must be in"));
}
