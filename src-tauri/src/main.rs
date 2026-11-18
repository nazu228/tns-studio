#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::json;
use std::path::PathBuf;
use std::sync::Mutex;
use tauri::Manager;
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

#[tauri::command]
fn detect_statement(_path: String) -> Result<serde_json::Value, String> {
    Err("detect_statement: Excel-порт ещё не подключён".into())
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
