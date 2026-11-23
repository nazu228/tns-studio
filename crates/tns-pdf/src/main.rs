use std::collections::HashSet;
use std::path::PathBuf;
use std::process::ExitCode;
use tns_pdf::{parse_pdf, unique_xlsx_file_name, write_statement_xlsx, PdfError};

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(Error::Cli(message)) => {
            eprintln!("{message}");
            eprintln!("usage: tns-pdf parse <pdf> --json <out-dir> [--xlsx <out-dir>]");
            eprintln!("       tns-pdf parse <pdf> --xlsx <out-dir>");
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
    let mut json_dir: Option<PathBuf> = None;
    let mut xlsx_dir: Option<PathBuf> = None;
    while let Some(argument) = arguments.next() {
        let (flag, inline_value) = match argument.split_once('=') {
            Some((flag, value)) => (flag.to_string(), Some(value.to_string())),
            None => (argument.clone(), None),
        };
        let value = match inline_value {
            Some(value) => value,
            None => arguments
                .next()
                .ok_or_else(|| Error::Cli(format!("{flag} requires a directory")))?,
        };
        if flag == "--json" {
            json_dir = Some(PathBuf::from(value));
        } else if flag == "--xlsx" {
            xlsx_dir = Some(PathBuf::from(value));
        } else {
            return Err(Error::Cli(format!("unknown argument: {argument}")));
        }
    }
    if json_dir.is_none() && xlsx_dir.is_none() {
        return Err(Error::Cli(
            "missing output: use --json <dir> and/or --xlsx <dir>".to_string(),
        ));
    }
    let input = PathBuf::from(input);

    let statements = parse_pdf(&input).map_err(Error::Pdf)?;

    if let Some(output_dir) = json_dir.as_deref() {
        let document = if statements.len() == 1 {
            serde_json::to_value(&statements[0])
        } else {
            serde_json::to_value(&statements)
        }
        .map_err(|error| Error::Pdf(PdfError::Io(std::io::Error::other(error))))?;
        std::fs::create_dir_all(output_dir).map_err(|error| Error::Pdf(PdfError::Io(error)))?;
        let stem = input
            .file_stem()
            .map(|stem| stem.to_string_lossy().into_owned())
            .ok_or_else(|| Error::Cli("PDF path has no file stem".to_string()))?;
        let output_path = output_dir.join(format!("{stem}.json"));
        let bytes = serde_json::to_vec_pretty(&document)
            .map_err(|error| Error::Pdf(PdfError::Io(std::io::Error::other(error))))?;
        std::fs::write(&output_path, bytes).map_err(|error| Error::Pdf(PdfError::Io(error)))?;
        println!("{}", output_path.display());
    }

    if let Some(output_dir) = xlsx_dir.as_deref() {
        std::fs::create_dir_all(output_dir).map_err(|error| Error::Pdf(PdfError::Io(error)))?;
        let mut used: HashSet<String> = HashSet::new();
        for statement in &statements {
            let file_name = unique_xlsx_file_name(statement, &mut used).map_err(Error::Pdf)?;
            let result = write_statement_xlsx(statement, output_dir, &file_name)
                .map_err(Error::Pdf)?;
            println!("{}", result.target_path);
        }
    }

    Ok(())
}
