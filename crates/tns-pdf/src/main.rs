use std::path::PathBuf;
use std::process::ExitCode;
use tns_pdf::{parse_pdf, PdfError};

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(Error::Cli(message)) => {
            eprintln!("{message}");
            eprintln!("usage: tns-pdf parse <pdf> --json <out-dir>");
            ExitCode::from(1)
        }
        Err(Error::Pdf(error)) => {
            eprintln!("{error}");
            match error {
                PdfError::NoStatements => ExitCode::from(2),
                _ => ExitCode::from(1),
            }
        }
    }
}

enum Error {
    Cli(String),
    Pdf(PdfError),
}

fn run() -> Result<(), Error> {
    let mut arguments = std::env::args().skip(1);
    let command = arguments
        .next()
        .ok_or_else(|| Error::Cli("missing command".to_string()))?;
    if command != "parse" {
        return Err(Error::Cli(format!("unknown command: {command}")));
    }
    let input = arguments
        .next()
        .ok_or_else(|| Error::Cli("missing PDF path".to_string()))?;
    let mut output_dir: Option<PathBuf> = None;
    while let Some(argument) = arguments.next() {
        if argument == "--json" {
            let value = arguments
                .next()
                .ok_or_else(|| Error::Cli("--json requires a directory".to_string()))?;
            output_dir = Some(PathBuf::from(value));
        } else if let Some(value) = argument.strip_prefix("--json=") {
            output_dir = Some(PathBuf::from(value));
        } else {
            return Err(Error::Cli(format!("unknown argument: {argument}")));
        }
    }
    let output_dir =
        output_dir.ok_or_else(|| Error::Cli("missing --json <out-dir>".to_string()))?;
    let input = PathBuf::from(input);

    let statements = parse_pdf(&input).map_err(Error::Pdf)?;
    let document = if statements.len() == 1 {
        serde_json::to_value(&statements[0])
    } else {
        serde_json::to_value(&statements)
    }
    .map_err(|error| Error::Pdf(PdfError::Io(std::io::Error::other(error))))?;

    std::fs::create_dir_all(&output_dir).map_err(|error| Error::Pdf(PdfError::Io(error)))?;
    let stem = input
        .file_stem()
        .map(|stem| stem.to_string_lossy().into_owned())
        .ok_or_else(|| Error::Cli("PDF path has no file stem".to_string()))?;
    let output_path = output_dir.join(format!("{stem}.json"));
    let bytes = serde_json::to_vec_pretty(&document)
        .map_err(|error| Error::Pdf(PdfError::Io(std::io::Error::other(error))))?;
    std::fs::write(&output_path, bytes).map_err(|error| Error::Pdf(PdfError::Io(error)))?;
    println!("{}", output_path.display());
    Ok(())
}
