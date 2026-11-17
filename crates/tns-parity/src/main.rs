//! Runs the Rust TNS engine for the Python parity harness.
//!
//! The harness owns the independent openpyxl signature and the golden files.
//! This binary only produces the Rust result and (once the output writer is
//! implemented) the workbook at `target_path`, so pytest can compare both
//! implementations through the same oracle.

use std::path::PathBuf;
use tns_core::{process_statement, ProcessOptions};

struct Args {
    fixture: PathBuf,
    output_dir: PathBuf,
    month: Option<String>,
    year: Option<String>,
    result: Option<PathBuf>,
}

fn next_value(args: &mut impl Iterator<Item = String>, flag: &str) -> Result<String, String> {
    args.next().ok_or_else(|| format!("{flag} requires a value"))
}

fn parse_args() -> Result<Args, String> {
    let mut fixture = None;
    let mut output_dir = None;
    let mut month = None;
    let mut year = None;
    let mut result = None;
    let mut args = std::env::args().skip(1);

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--fixture" => fixture = Some(PathBuf::from(next_value(&mut args, "--fixture")?)),
            "--output-dir" => {
                output_dir = Some(PathBuf::from(next_value(&mut args, "--output-dir")?))
            }
            "--month" => month = Some(next_value(&mut args, "--month")?),
            "--year" => year = Some(next_value(&mut args, "--year")?),
            "--result" => result = Some(PathBuf::from(next_value(&mut args, "--result")?)),
            "--help" | "-h" => {
                println!(
                    "Usage: tns-parity --fixture <xlsx> --output-dir <dir> [--month <name>] [--year <year>] [--result <json>]"
                );
                std::process::exit(0);
            }
            other => return Err(format!("unknown argument: {other}")),
        }
    }

    Ok(Args {
        fixture: fixture.ok_or_else(|| "--fixture is required".to_string())?,
        output_dir: output_dir.ok_or_else(|| "--output-dir is required".to_string())?,
        month,
        year,
        result,
    })
}

fn run() -> Result<(), String> {
    let args = parse_args()?;
    let result = process_statement(
        &args.fixture,
        ProcessOptions {
            output_dir: Some(args.output_dir),
            month: args.month,
            year: args.year,
            ..Default::default()
        },
    )
    .map_err(|error| error.to_string())?;

    let json = serde_json::to_string_pretty(&result).map_err(|error| error.to_string())?;
    match args.result {
        Some(path) => {
            if let Some(parent) = path.parent() {
                std::fs::create_dir_all(parent).map_err(|error| {
                    format!("cannot create result directory {}: {error}", parent.display())
                })?;
            }
            std::fs::write(&path, json)
                .map_err(|error| format!("cannot write result {}: {error}", path.display()))?;
        }
        None => println!("{json}"),
    }
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("tns-parity: {error}");
        std::process::exit(1);
    }
}
