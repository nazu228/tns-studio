//! Serializable statement model.

/// Top-level parsed statement.
#[derive(Debug, Clone, serde::Serialize)]
pub struct Statement {
    pub schema_version: u32,
    pub source: Source,
    pub statement: StatementMeta,
    pub layout: Layout,
    pub pages: Vec<PageInfo>,
    pub houses: Vec<House>,
    pub meters: Vec<Meter>,
    pub totals: Totals,
    pub warnings: Vec<String>,
}

impl Statement {
    pub const SCHEMA_VERSION: u32 = 1;
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct Source {
    pub file: String,
    pub pages: usize,
    pub producer: Option<String>,
    pub text_layer: bool,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct StatementMeta {
    pub kind: String,
    pub is_correction: bool,
    pub org: Option<String>,
    pub contract: Option<String>,
    pub month: Option<String>,
    pub base_period: Option<String>,
    pub month_label: Option<String>,
    pub page_range: [usize; 2],
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct Layout {
    pub page_size: [f64; 2],
    pub columns: usize,
    pub x_boundaries: Vec<f64>,
    pub confidence: f64,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct PageInfo {
    pub page: usize,
    pub footer: Option<String>,
    pub rows: usize,
    pub houses_started: usize,
    pub role: String,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct House {
    pub num: usize,
    pub name: String,
    pub page: usize,
    pub main: Option<f64>,
    pub sub_deduct: Option<f64>,
    pub control: Option<f64>,
    pub amount: Option<f64>,
    pub day: f64,
    pub night: f64,
    pub odn: f64,
    pub simple: f64,
    pub total: f64,
    pub diff: f64,
    pub meters_active: usize,
    pub meters_res: usize,
    pub sub_rows: usize,
    pub meter_range: [usize; 2],
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct Meter {
    pub house: usize,
    pub row: usize,
    pub page: usize,
    pub point: String,
    pub place: String,
    pub serial: String,
    pub zone: String,
    pub zone_raw: String,
    pub preview_bucket: String,
    pub sub_type: String,
    pub start: Option<f64>,
    pub end: Option<f64>,
    pub delta: Option<f64>,
    pub k: Option<f64>,
    pub main: Option<f64>,
    pub extra: Option<f64>,
    pub unmetered: Option<f64>,
    pub odn: Option<f64>,
    pub line_loss: Option<f64>,
    pub tr_loss: Option<f64>,
    pub sub_volume: Option<f64>,
    pub voltage: String,
    pub category: String,
    pub billed: Option<f64>,
    pub amount: Option<f64>,
    pub is_sub: bool,
    pub is_reserve: bool,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct Totals {
    pub day: f64,
    pub night: f64,
    pub odn: f64,
    pub control: f64,
    pub amount: f64,
    pub official: Official,
    pub balance: Balance,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct Official {
    pub volume: Option<f64>,
    pub amount: Option<f64>,
    pub page: Option<usize>,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct Balance {
    pub volume: f64,
    pub amount: f64,
}
