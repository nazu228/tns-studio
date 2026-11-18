#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use tauri::Manager;
use tns_core::{detect_statement_type, StatementKind};
use tns_db::{Database, HistoryEntry};

struct AppState {
    db: Mutex<Database>,
    data_dir: PathBuf,
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

#[tauri::command]
fn process_statement(
    _source_path: String,
    _output_dir: Option<String>,
    _month: Option<String>,
    _year: Option<String>,
) -> Result<serde_json::Value, String> {
    Err("process_statement: Excel-порт ещё не подключён".into())
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
            update_check
        ])
        .run(tauri::generate_context!())
        .expect("error while running TNS Energy Studio");
}
