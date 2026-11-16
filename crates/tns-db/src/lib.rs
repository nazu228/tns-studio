//! Local SQLite storage for TNS Energy Studio.
//!
//! The schema mirrors legacy/pyqt/sync_manager.py:DatabaseManager.init_db,
//! except `sync_metadata` is intentionally not created: cloud sync and Yandex
//! are removed. The database stays local; backups are local files.

use rusqlite::{params, Connection, OptionalExtension};
use serde::Serialize;
use std::fmt;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};
use tns_core::TnsError;

#[derive(Debug)]
pub enum DbError {
    Sql(rusqlite::Error),
    Io(std::io::Error),
    Validation(String),
    Message(String),
}

impl fmt::Display for DbError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            DbError::Sql(error) => write!(f, "SQLite: {}", error),
            DbError::Io(error) => write!(f, "IO: {}", error),
            DbError::Validation(message) => write!(f, "{}", message),
            DbError::Message(message) => write!(f, "{}", message),
        }
    }
}

impl std::error::Error for DbError {}

impl From<rusqlite::Error> for DbError {
    fn from(value: rusqlite::Error) -> Self {
        DbError::Sql(value)
    }
}

impl From<std::io::Error> for DbError {
    fn from(value: std::io::Error) -> Self {
        DbError::Io(value)
    }
}

impl From<TnsError> for DbError {
    fn from(value: TnsError) -> Self {
        DbError::Message(value.to_string())
    }
}

pub type DbResult<T> = Result<T, DbError>;

#[derive(Debug, Clone, Serialize)]
pub struct CalculationRecord {
    pub period_month: String,
    pub period_year: String,
    pub org_type: String,
    pub org_name: String,
    pub contract_number: String,
    pub houses_count: i64,
    pub total_day: f64,
    pub total_night: f64,
    pub total_odn: f64,
    pub total_all: f64,
    pub balance_diff: f64,
    pub saved_filename: Option<String>,
    pub calculated_at: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct HistoryEntry {
    pub id: i64,
    pub period_month: String,
    pub period_year: String,
    pub org_type: String,
    pub org_name: String,
    pub contract_number: String,
    pub houses_count: i64,
    pub total_day: f64,
    pub total_night: f64,
    pub total_odn: f64,
    pub total_all: f64,
    pub balance_diff: f64,
    pub saved_filename: Option<String>,
    pub calculated_at: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct Summary {
    pub houses_count: i64,
    pub calculations_count: i64,
    pub last_calculation: Option<String>,
    pub file_size: u64,
}

pub struct Database {
    conn: Connection,
    path: PathBuf,
}

impl Database {
    pub fn open(path: impl AsRef<Path>) -> DbResult<Self> {
        let path = path.as_ref().to_path_buf();
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let conn = Connection::open(&path)?;
        conn.pragma_update(None, "journal_mode", "WAL")?;
        let database = Self { conn, path };
        database.init_schema()?;
        database.seed()?;
        Ok(database)
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    fn init_schema(&self) -> DbResult<()> {
        self.conn.execute_batch(
            r#"
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contract_number TEXT NOT NULL UNIQUE,
                slug TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS houses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_contract TEXT NOT NULL,
                address TEXT NOT NULL UNIQUE,
                meters_count_active INTEGER DEFAULT 0,
                meters_count_reserve INTEGER DEFAULT 0,
                note TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS tariffs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone_code TEXT NOT NULL UNIQUE,
                zone_name TEXT NOT NULL,
                rate_rub REAL DEFAULT 0.0,
                note TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS calculation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_month TEXT NOT NULL,
                period_year TEXT NOT NULL,
                org_type TEXT NOT NULL,
                org_name TEXT NOT NULL,
                contract_number TEXT NOT NULL,
                houses_count INTEGER DEFAULT 0,
                total_day REAL DEFAULT 0.0,
                total_night REAL DEFAULT 0.0,
                total_odn REAL DEFAULT 0.0,
                total_all REAL DEFAULT 0.0,
                balance_diff REAL DEFAULT 0.0,
                saved_filename TEXT,
                calculated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            "#,
        )?;
        Ok(())
    }

    fn seed(&self) -> DbResult<()> {
        let organizations: i64 = self
            .conn
            .query_row("SELECT COUNT(*) FROM organizations", [], |row| row.get(0))?;
        if organizations == 0 {
            self.conn.execute(
                "INSERT INTO organizations (name, contract_number, slug) VALUES (?1, ?2, ?3)",
                params!["ООО «Южный Дом»", "23110603789", "dom"],
            )?;
            self.conn.execute(
                "INSERT INTO organizations (name, contract_number, slug) VALUES (?1, ?2, ?3)",
                params!["ООО «Южный Город»", "23110604327", "gorod"],
            )?;
        }
        let tariffs: i64 = self
            .conn
            .query_row("SELECT COUNT(*) FROM tariffs", [], |row| row.get(0))?;
        if tariffs == 0 {
            self.conn.execute(
                "INSERT INTO tariffs (zone_code, zone_name, rate_rub, note) VALUES (?1, ?2, ?3, ?4)",
                params![
                    "day",
                    "Дневной тариф (Пик / Полупик / Т1)",
                    7.15,
                    "Действует в часы 07:00-23:00"
                ],
            )?;
            self.conn.execute(
                "INSERT INTO tariffs (zone_code, zone_name, rate_rub, note) VALUES (?1, ?2, ?3, ?4)",
                params![
                    "night",
                    "Ночной тариф (Т2)",
                    4.22,
                    "Действует в часы 23:00-07:00"
                ],
            )?;
            self.conn.execute(
                "INSERT INTO tariffs (zone_code, zone_name, rate_rub, note) VALUES (?1, ?2, ?3, ?4)",
                params![
                    "odn",
                    "ОДН (общедомовые нужды / СОИ / коллективный)",
                    6.45,
                    "Общедомовые нужды: лифты, свет, СОИ, потери"
                ],
            )?;
        }
        Ok(())
    }

    pub fn record_calculation(&self, record: &CalculationRecord) -> DbResult<i64> {
        self.conn.execute(
            r#"
            INSERT INTO calculation_history (
                period_month, period_year, org_type, org_name, contract_number,
                houses_count, total_day, total_night, total_odn, total_all,
                balance_diff, saved_filename, calculated_at
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12,
                      COALESCE(?13, datetime('now')))
            "#,
            params![
                record.period_month,
                record.period_year,
                record.org_type,
                record.org_name,
                record.contract_number,
                record.houses_count,
                record.total_day,
                record.total_night,
                record.total_odn,
                record.total_all,
                record.balance_diff,
                record.saved_filename,
                record.calculated_at,
            ],
        )?;
        Ok(self.conn.last_insert_rowid())
    }

    pub fn register_or_update_house(
        &self,
        contract_number: &str,
        address: &str,
        meters_active: i64,
        meters_reserve: i64,
    ) -> DbResult<()> {
        self.conn.execute(
            r#"
            INSERT INTO houses (org_contract, address, meters_count_active, meters_count_reserve, updated_at)
            VALUES (?1, ?2, ?3, ?4, CURRENT_TIMESTAMP)
            ON CONFLICT(address) DO UPDATE SET
                org_contract=excluded.org_contract,
                meters_count_active=excluded.meters_count_active,
                meters_count_reserve=excluded.meters_count_reserve,
                updated_at=CURRENT_TIMESTAMP
            "#,
            params![contract_number, address, meters_active, meters_reserve],
        )?;
        Ok(())
    }

    pub fn history(&self, limit: usize) -> DbResult<Vec<HistoryEntry>> {
        let mut statement = self.conn.prepare(
            r#"
            SELECT id, period_month, period_year, org_type, org_name, contract_number,
                   houses_count, total_day, total_night, total_odn, total_all,
                   balance_diff, saved_filename, calculated_at
            FROM calculation_history
            ORDER BY id DESC
            LIMIT ?1
            "#,
        )?;
        let rows = statement.query_map(params![limit as i64], |row| {
            Ok(HistoryEntry {
                id: row.get(0)?,
                period_month: row.get(1)?,
                period_year: row.get(2)?,
                org_type: row.get(3)?,
                org_name: row.get(4)?,
                contract_number: row.get(5)?,
                houses_count: row.get(6)?,
                total_day: row.get(7)?,
                total_night: row.get(8)?,
                total_odn: row.get(9)?,
                total_all: row.get(10)?,
                balance_diff: row.get(11)?,
                saved_filename: row.get(12)?,
                calculated_at: row.get(13)?,
            })
        })?;
        let mut result = Vec::new();
        for row in rows {
            result.push(row?);
        }
        Ok(result)
    }

    pub fn summary(&self) -> DbResult<Summary> {
        let houses_count: i64 =
            self.conn
                .query_row("SELECT COUNT(*) FROM houses", [], |row| row.get(0))?;
        let calculations_count: i64 = self.conn.query_row(
            "SELECT COUNT(*) FROM calculation_history",
            [],
            |row| row.get(0),
        )?;
        let last_calculation: Option<String> = self
            .conn
            .query_row(
                "SELECT period_month || ' ' || period_year || ' (' || calculated_at || ')' \
                 FROM calculation_history ORDER BY id DESC LIMIT 1",
                [],
                |row| row.get(0),
            )
            .optional()?;
        let file_size = std::fs::metadata(&self.path).map(|meta| meta.len()).unwrap_or(0);
        Ok(Summary {
            houses_count,
            calculations_count,
            last_calculation,
            file_size,
        })
    }

    pub fn backup_to(&self, target: impl AsRef<Path>) -> DbResult<PathBuf> {
        let target = target.as_ref().to_path_buf();
        if let Some(parent) = target.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let target_text = target.to_string_lossy().replace('\'', "''");
        self.conn
            .execute_batch(&format!("VACUUM INTO '{}'", target_text))?;
        Ok(target)
    }

    pub fn validate(path: impl AsRef<Path>) -> DbResult<()> {
        let conn = Connection::open(path.as_ref())?;
        for table in ["organizations", "houses", "tariffs", "calculation_history"] {
            let exists: Option<String> = conn
                .query_row(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?1",
                    params![table],
                    |row| row.get(0),
                )
                .optional()?;
            if exists.is_none() {
                return Err(DbError::Validation(format!(
                    "В базе отсутствует обязательная таблица «{}».",
                    table
                )));
            }
        }
        Ok(())
    }
}

pub fn timestamp_now() -> String {
    let seconds = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0);
    format!("{}", seconds)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_db() -> (tempfile::TempDir, Database) {
        let dir = tempfile::tempdir().expect("tempdir");
        let database = Database::open(dir.path().join("tns_database.sqlite")).expect("open db");
        (dir, database)
    }

    #[test]
    fn creates_legacy_schema_and_seed() {
        let (_dir, database) = temp_db();
        let organizations: i64 = database
            .conn
            .query_row("SELECT COUNT(*) FROM organizations", [], |row| row.get(0))
            .unwrap();
        let tariffs: i64 = database
            .conn
            .query_row("SELECT COUNT(*) FROM tariffs", [], |row| row.get(0))
            .unwrap();
        let sync_metadata: i64 = database
            .conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sync_metadata'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(organizations, 2);
        assert_eq!(tariffs, 3);
        assert_eq!(sync_metadata, 0, "sync_metadata must not be created");
    }

    #[test]
    fn records_and_reads_history() {
        let (_dir, database) = temp_db();
        let record = CalculationRecord {
            period_month: "Апрель".into(),
            period_year: "2026".into(),
            org_type: "dom".into(),
            org_name: "ООО «Южный Дом»".into(),
            contract_number: "23110603789".into(),
            houses_count: 2,
            total_day: 215.5,
            total_night: 12.25,
            total_odn: 25.0,
            total_all: 252.75,
            balance_diff: 0.0,
            saved_filename: Some("Дом_Апрель_2026.xlsx".into()),
            calculated_at: None,
        };
        let id = database.record_calculation(&record).unwrap();
        assert!(id > 0);
        let history = database.history(10).unwrap();
        assert_eq!(history.len(), 1);
        assert_eq!(history[0].total_all, 252.75);
        assert_eq!(history[0].saved_filename.as_deref(), Some("Дом_Апрель_2026.xlsx"));
    }

    #[test]
    fn upserts_house() {
        let (_dir, database) = temp_db();
        database
            .register_or_update_house("23110603789", "ул. Ленина, д. 1", 3, 1)
            .unwrap();
        database
            .register_or_update_house("23110603789", "ул. Ленина, д. 1", 4, 2)
            .unwrap();
        let (count, active, reserve): (i64, i64, i64) = database
            .conn
            .query_row(
                "SELECT COUNT(*), MAX(meters_count_active), MAX(meters_count_reserve) FROM houses",
                [],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .unwrap();
        assert_eq!(count, 1);
        assert_eq!(active, 4);
        assert_eq!(reserve, 2);
    }

    #[test]
    fn backs_up_and_validates() {
        let (dir, database) = temp_db();
        let backup = database.backup_to(dir.path().join("backups").join("copy.sqlite")).unwrap();
        assert!(backup.is_file());
        Database::validate(&backup).unwrap();
    }
}
