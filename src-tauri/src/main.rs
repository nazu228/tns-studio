#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use tauri::{Emitter, Manager};
use tns_core::{
    detect_statement_type, process_statement as run_statement, ProcessOptions, ProcessResult,
    StatementKind,
};
use tns_db::{CalculationRecord, Database, HistoryEntry};

struct AppState {
    db: Mutex<Database>,
    data_dir: PathBuf,
    cancel: Arc<AtomicBool>,
    running: Arc<AtomicBool>,
}

struct RunningGuard(Arc<AtomicBool>);

impl Drop for RunningGuard {
    fn drop(&mut self) {
        self.0.store(false, Ordering::SeqCst);
    }
}

fn data_dir() -> PathBuf {
    let base = std::env::var_os("LOCALAPPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|| std::env::temp_dir());
    base.join("TNS Energy Studio")
}

#[tauri::command]
fn history_list(limit: Option<usize>, state: tauri::State<'_, AppState>) -> Result<Vec<HistoryEntry>, String> {
    let db = state.db.lock().map_err(|error| error.to_string())?;
    db.history(limit.unwrap_or(50)).map_err(|error| error.to_string())
}

#[tauri::command]
fn backup_db(state: tauri::State<'_, AppState>) -> Result<String, String> {
    let db = state.db.lock().map_err(|error| error.to_string())?;
    let target = state
        .data_dir
        .join("backups")
        .join(format!("tns_database_backup_{}.sqlite", tns_db::timestamp_now()));
    db.backup_to(&target)
        .map(|path| path.to_string_lossy().to_string())
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn open_file(path: String) -> Result<(), String> {
    std::process::Command::new("explorer")
        .arg(&path)
        .spawn()
        .map(|_| ())
        .map_err(|error| format!("Не удалось открыть файл {path}: {error}"))
}

#[tauri::command]
fn open_folder(path: String) -> Result<(), String> {
    std::process::Command::new("explorer")
        .arg(&path)
        .spawn()
        .map(|_| ())
        .map_err(|error| format!("Не удалось открыть папку {path}: {error}"))
}

#[tauri::command]
fn config_get(state: tauri::State<'_, AppState>) -> serde_json::Value {
    json!({
        "app_version": env!("CARGO_PKG_VERSION"),
        "data_dir": state.data_dir.to_string_lossy(),
        "database": state.data_dir.join("tns_database.sqlite").to_string_lossy(),
        "cloud_sync": false
    })
}

struct DetectedFile {
    path: PathBuf,
    kind: StatementKind,
    consumer: String,
    contract: String,
    error: Option<String>,
}

impl DetectedFile {
    fn read(path: PathBuf) -> Self {
        match tns_excel::read(&path) {
            Ok(book) => {
                let (kind, consumer, contract) = detect_statement_type(&book);
                Self {
                    path,
                    kind,
                    consumer,
                    contract,
                    error: None,
                }
            }
            Err(error) => Self {
                path,
                kind: StatementKind::Unknown,
                consumer: String::new(),
                contract: String::new(),
                error: Some(error.to_string()),
            },
        }
    }

    fn to_json(&self) -> Value {
        json!({
            "path": self.path.to_string_lossy(),
            "kind": self.kind.as_str(),
            "consumer": self.consumer,
            "contract": self.contract,
            "error": self.error,
        })
    }
}

fn detect_path(path: &Path) -> Result<Value, String> {
    if !path.exists() {
        return Err(format!("Путь не найден: {}", path.display()));
    }

    if path.is_file() {
        let file = DetectedFile::read(path.to_path_buf());
        if let Some(error) = file.error.as_deref() {
            return Err(error.to_string());
        }
        return Ok(json!({
            "path": file.path.to_string_lossy(),
            "is_dir": false,
            "kind": file.kind.as_str(),
            "consumer": file.consumer,
            "contract": file.contract,
            "files": [file.to_json()],
        }));
    }

    let mut candidates: Vec<PathBuf> = std::fs::read_dir(path)
        .map_err(|error| format!("Не удалось прочитать папку {}: {error}", path.display()))?
        .filter_map(|entry| entry.ok())
        .map(|entry| entry.path())
        .filter(|entry| entry.is_file())
        .filter(|entry| {
            entry
                .extension()
                .is_some_and(|extension| extension.eq_ignore_ascii_case("xlsx"))
        })
        .filter(|entry| {
            entry
                .file_name()
                .map_or(false, |name| !name.to_string_lossy().starts_with("~$"))
        })
        .collect();
    candidates.sort_by_key(|entry| {
        entry
            .file_name()
            .map(|name| name.to_string_lossy().to_lowercase())
            .unwrap_or_default()
    });

    let files: Vec<DetectedFile> = candidates.into_iter().map(DetectedFile::read).collect();
    let readable: Vec<&DetectedFile> = files.iter().filter(|file| file.error.is_none()).collect();
    // The folder is a statement batch only when every readable workbook agrees on the type.
    let kind = match readable.first() {
        Some(first)
            if first.kind != StatementKind::Unknown
                && readable.iter().all(|file| file.kind == first.kind) =>
        {
            first.kind
        }
        _ => StatementKind::Unknown,
    };
    let (consumer, contract) = match readable.first() {
        Some(first) if kind != StatementKind::Unknown => (first.consumer.clone(), first.contract.clone()),
        _ => (String::new(), String::new()),
    };

    Ok(json!({
        "path": path.to_string_lossy(),
        "is_dir": true,
        "kind": kind.as_str(),
        "consumer": consumer,
        "contract": contract,
        "files": files.iter().map(|file| file.to_json()).collect::<Vec<Value>>(),
    }))
}

#[tauri::command]
async fn detect_statement(path: String) -> Result<Value, String> {
    tauri::async_runtime::spawn_blocking(move || detect_path(Path::new(&path)))
        .await
        .map_err(|error| error.to_string())?
}

fn split_period(period: &str) -> (String, String) {
    let cleaned = period.replace("г.", "");
    let mut tokens = cleaned.split_whitespace().map(str::to_string);
    match (tokens.next(), tokens.next()) {
        (Some(month), Some(year)) if year.len() == 4 && year.chars().all(|value| value.is_ascii_digit()) => {
            (month, year)
        }
        _ => (String::new(), String::new()),
    }
}

fn record_history(db: &Database, result: &ProcessResult) -> Option<String> {
    let org_type = if result.consumer.to_lowercase().contains("город") {
        "gorod"
    } else {
        "dom"
    };
    let (month, year) = split_period(&result.period);
    let saved_filename = Path::new(&result.target_path)
        .file_name()
        .map(|name| name.to_string_lossy().to_string());
    let record = CalculationRecord {
        period_month: month,
        period_year: year,
        org_type: org_type.to_string(),
        org_name: result.consumer.clone(),
        contract_number: result.contract.clone(),
        houses_count: result.houses_count as i64,
        total_day: result.total_day,
        total_night: result.total_night,
        total_odn: result.total_odn,
        total_all: result.total_all,
        balance_diff: result.balance_diff,
        saved_filename,
        calculated_at: None,
    };
    if let Err(error) = db.record_calculation(&record) {
        return Some(error.to_string());
    }
    for row in &result.preview_rows {
        if let Err(error) = db.register_or_update_house(
            &result.contract,
            &row.name,
            row.meters_active as i64,
            row.meters_res as i64,
        ) {
            return Some(error.to_string());
        }
    }
    None
}

#[tauri::command]
async fn process_statement(
    app: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
    source_path: String,
    output_dir: Option<String>,
    month: Option<String>,
    year: Option<String>,
    custom_filename: Option<String>,
) -> Result<serde_json::Value, String> {
    if state
        .running
        .compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst)
        .is_err()
    {
        return Err("Расчет уже выполняется.".into());
    }
    let _guard = RunningGuard(state.running.clone());
    state.cancel.store(false, Ordering::SeqCst);

    let app = app.clone();
    let cancel_flag = state.cancel.clone();
    let source = PathBuf::from(source_path);
    let output = output_dir.map(PathBuf::from);
    let result = tauri::async_runtime::spawn_blocking(move || {
        let progress = |percent: u8, message: &str| {
            let _ = app.emit(
                "process-progress",
                json!({ "percent": percent, "message": message }),
            );
        };
        let cancel = move || cancel_flag.load(Ordering::SeqCst);
        run_statement(
            Path::new(&source),
            ProcessOptions {
                output_dir: output,
                custom_filename,
                month,
                year,
                progress: Some(&progress),
                cancel: Some(&cancel),
            },
        )
        .map_err(|error| error.to_string())
    })
    .await
    .map_err(|error| error.to_string())??;

    let mut payload = serde_json::to_value(&result).map_err(|error| error.to_string())?;
    let warning = match state.db.lock() {
        Ok(db) => record_history(&db, &result),
        Err(error) => Some(error.to_string()),
    };
    if let Some(warning) = warning {
        payload["history_warning"] = json!(warning);
    }
    Ok(payload)
}

#[tauri::command]
fn cancel_statement(state: tauri::State<'_, AppState>) -> serde_json::Value {
    state.cancel.store(true, Ordering::SeqCst);
    json!({ "cancelled": true })
}

#[tauri::command]
fn update_check() -> serde_json::Value {
    json!({ "status": "not_configured", "source": "github" })
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let directory = data_dir();
            let database = Database::open(directory.join("tns_database.sqlite"))
                .map_err(|error| format!("Не удалось открыть локальную БД: {error}"))?;
            app.manage(AppState {
                db: Mutex::new(database),
                data_dir: directory,
                cancel: Arc::new(AtomicBool::new(false)),
                running: Arc::new(AtomicBool::new(false)),
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            history_list,
            backup_db,
            open_file,
            open_folder,
            config_get,
            detect_statement,
            process_statement,
            cancel_statement,
            update_check
        ])
        .run(tauri::generate_context!())
        .expect("error while running TNS Energy Studio");
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixtures() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("tests")
            .join("parity")
            .join("fixtures")
    }

    fn temp_dir(label: &str) -> PathBuf {
        let unique = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|duration| duration.as_nanos())
            .unwrap_or_default();
        std::env::temp_dir().join(format!("tns-{label}-{}-{unique}", std::process::id()))
    }

    #[test]
    fn detects_dom_file() {
        let value = detect_path(&fixtures().join("dom_april_2026.xlsx")).expect("detect dom");
        assert_eq!(value["is_dir"], false);
        assert_eq!(value["kind"], "dom");
        assert!(!value["contract"].as_str().unwrap_or_default().is_empty());
        assert_eq!(value["files"].as_array().map(Vec::len), Some(1));
    }

    #[test]
    fn detects_gorod_file() {
        let value = detect_path(&fixtures().join("gorod_april_2026.xlsx")).expect("detect gorod");
        assert_eq!(value["is_dir"], false);
        assert_eq!(value["kind"], "gorod");
        assert!(!value["contract"].as_str().unwrap_or_default().is_empty());
        assert_eq!(value["files"].as_array().map(Vec::len), Some(1));
    }

    #[test]
    fn lists_fixture_folder() {
        let value = detect_path(&fixtures()).expect("detect folder");
        assert_eq!(value["is_dir"], true);
        let files = value["files"].as_array().expect("files array");
        assert!(
            files.len() >= 3,
            "expected at least 3 xlsx candidates, got {}",
            files.len()
        );
        // dom_april, dom_march and gorod_april are mixed, so the folder has no single kind.
        assert_eq!(value["kind"], "unknown");
    }

    #[test]
    fn splits_period_into_month_and_year() {
        assert_eq!(
            split_period("Апрель 2026 г."),
            ("Апрель".to_string(), "2026".to_string())
        );
        assert_eq!(split_period("Без периода"), (String::new(), String::new()));
        assert_eq!(split_period("Апрель 26"), (String::new(), String::new()));
    }

    #[test]
    fn missing_path_is_an_error() {
        let error = detect_path(&temp_dir("missing")).expect_err("missing path");
        assert!(error.contains("Путь не найден"), "unexpected error: {error}");
    }

    #[test]
    fn empty_folder_is_unknown() {
        let directory = temp_dir("empty");
        std::fs::create_dir_all(&directory).expect("create temp dir");
        let value = detect_path(&directory).expect("empty folder");
        assert_eq!(value["is_dir"], true);
        assert_eq!(value["kind"], "unknown");
        assert_eq!(value["files"].as_array().map(Vec::len), Some(0));
        std::fs::remove_dir_all(directory).expect("remove temp dir");
    }

    #[test]
    fn records_calculation_and_houses() {
        let directory = temp_dir("history");
        std::fs::create_dir_all(&directory).expect("create temp dir");
        let db = Database::open(directory.join("test.sqlite")).expect("open test db");
        let result = run_statement(
            &fixtures().join("dom_april_2026.xlsx"),
            ProcessOptions {
                output_dir: Some(directory.join("out")),
                month: Some("Апрель".into()),
                year: Some("2026".into()),
                ..ProcessOptions::default()
            },
        )
        .expect("process fixture");
        assert!(record_history(&db, &result).is_none());
        let history = db.history(10).expect("read history");
        assert_eq!(history.len(), 1);
        assert_eq!(history[0].org_type, "dom");
        assert_eq!(history[0].period_month, "Апрель");
        assert_eq!(history[0].period_year, "2026");
        assert_eq!(history[0].houses_count, result.houses_count as i64);
        assert!(history[0].saved_filename.is_some());
        assert_eq!(
            db.summary().expect("db summary").houses_count,
            result.houses_count as i64
        );
        drop(db);
        std::fs::remove_dir_all(directory).expect("remove temp dir");
    }
}
