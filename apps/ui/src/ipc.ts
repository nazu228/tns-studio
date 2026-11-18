import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";

export type StatementKind = "dom" | "gorod" | "unknown";

// Rust serializes payloads without renaming, so payload fields stay snake_case.
// Command arguments, on the other hand, are camelCase on the JS side.
export type DetectedFile = {
  path: string;
  kind: StatementKind;
  consumer: string;
  contract: string;
  error: string | null;
};

export type DetectResult = {
  path: string;
  is_dir: boolean;
  kind: StatementKind;
  consumer: string;
  contract: string;
  files: DetectedFile[];
};

export type PreviewRow = {
  num: number;
  name: string;
  day: number;
  night: number;
  odn: number;
  simple: number;
  total: number;
  control: number;
  diff: number;
  meters: string;
  meters_active: number;
  meters_res: number;
};

export type ProcessResult = {
  success: boolean;
  consumer: string;
  contract: string;
  period: string;
  subfolder_name: string;
  target_dir: string;
  target_path: string;
  warning: string | null;
  houses_count: number;
  total_day: number;
  total_night: number;
  total_odn: number;
  total_simple: number;
  total_all: number;
  statement_total: number;
  balance_diff: number;
  balance_ok: boolean;
  preview_rows: PreviewRow[];
  columns_used: Record<string, number>;
  history_warning?: string | null;
};

export type ProcessProgress = {
  percent: number;
  message: string;
};

export type HistoryEntry = {
  id: number;
  period_month: string;
  period_year: string;
  org_type: string;
  org_name: string;
  contract_number: string;
  houses_count: number;
  total_day: number;
  total_night: number;
  total_odn: number;
  total_all: number;
  balance_diff: number;
  saved_filename: string | null;
  calculated_at: string;
};

export type ProcessStatementArgs = {
  sourcePath: string;
  outputDir?: string;
  month: string;
  year: string;
};

export const detectStatement = (path: string) => invoke<DetectResult>("detect_statement", { path });

export const processStatement = ({ sourcePath, outputDir, month, year }: ProcessStatementArgs) =>
  invoke<ProcessResult>("process_statement", { sourcePath, outputDir, month, year });

export const cancelStatement = () => invoke("cancel_statement");

export const historyList = (limit = 50) => invoke<HistoryEntry[]>("history_list", { limit });

export const backupDb = () => invoke<string>("backup_db");

export const openFile = (path: string) => invoke("open_file", { path });

export const openFolder = (path: string) => invoke("open_folder", { path });

export const listenProcessProgress = (handler: (progress: ProcessProgress) => void): Promise<UnlistenFn> =>
  listen<ProcessProgress>("process-progress", (event) => handler(event.payload));

const excelFilters = [{ name: "Excel", extensions: ["xlsx"] }];

export const pickFolder = async (): Promise<string | null> => {
  const selected = await open({ directory: true, multiple: false });
  return typeof selected === "string" ? selected : null;
};

export const pickFile = async (): Promise<string | null> => {
  const selected = await open({ directory: false, multiple: false, filters: excelFilters });
  return typeof selected === "string" ? selected : null;
};
