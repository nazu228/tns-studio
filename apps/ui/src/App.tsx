import { useEffect, useRef, useState } from "react";
import { MONTHS, YEARS } from "./data";
import {
  backupDb,
  cancelStatement,
  detectStatement,
  historyList,
  listenProcessProgress,
  openFile,
  openFolder,
  pickFile,
  pickFolder,
  processStatement,
  type DetectResult,
  type HistoryEntry,
  type ProcessResult,
  type StatementKind,
} from "./ipc";
import "./styles.css";

type Mode = "both" | "dom" | "gorod";
type Tab = "dom" | "gorod";
type HelpTab = "checks" | "fixes";
type ResultsMap = { dom?: ProcessResult; gorod?: ProcessResult };
type PlannedFile = { kind: Tab; path: string };
type CalculationPlan = { files: PlannedFile[]; outputDir?: string; warning?: string };

const DEFAULT_HINT = "ℹ️ В папке найдено 0 файлов .xlsx. Ведомости ТНС определяются при расчёте.";

const fmt = (value: number | undefined) => (value === undefined ? "—" : value.toFixed(3));
const energy = (value: number | undefined) => (value === undefined ? "—" : `${value.toFixed(3)} кВт*ч`);
const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const orgLabel = (kind: StatementKind) =>
  kind === "dom" ? "ООО «Южный Дом»" : kind === "gorod" ? "ООО «Южный Город»" : "неизвестная организация";

const errorText = (error: unknown) => {
  if (typeof error === "string") return error;
  if (error instanceof Error) return error.message;
  return String(error);
};

const isCancellation = (error: unknown) => errorText(error).toLowerCase().includes("отмен");

const describeDetect = (detected: DetectResult): string => {
  if (!detected.is_dir) {
    const file = detected.files[0];
    if (!file) return "⚠️ Файл не выбран.";
    if (file.error) return `⚠️ Не удалось прочитать файл: ${file.error}`;
    if (file.kind === "unknown") {
      return "⚠️ Не удалось определить тип ведомости. Ожидается ведомость ООО «Южный Дом» или ООО «Южный Город».";
    }
    return `ℹ️ Найден файл: ${orgLabel(file.kind)} · договор ${file.contract || "не указан"}`;
  }

  const dom = detected.files.filter((file) => file.error === null && file.kind === "dom").length;
  const gorod = detected.files.filter((file) => file.error === null && file.kind === "gorod").length;
  const unknown = detected.files.length - dom - gorod;
  const unreadable = detected.files.filter((file) => file.error !== null).length;
  const summary = `ℹ️ В папке найдено ${detected.files.length} файлов .xlsx: дом — ${dom}, город — ${gorod}, не определено — ${unknown}.`;
  return unreadable > 0 ? `${summary} ⚠️ Не удалось прочитать файлов: ${unreadable}.` : summary;
};

const planCalculation = (detected: DetectResult, currentMode: Mode): CalculationPlan | { error: string } => {
  const usable = detected.files.filter((file) => file.error === null && file.kind !== "unknown");

  if (!detected.is_dir) {
    const file = detected.files[0];
    if (!file) return { error: "⚠️ Файл не выбран. Выберите ведомость .xlsx." };
    if (file.error) return { error: `⚠️ Не удалось прочитать файл: ${file.error}` };
    if (file.kind === "unknown") {
      return { error: "⚠️ Не удалось определить тип ведомости. Ожидается ведомость ООО «Южный Дом» или ООО «Южный Город»." };
    }
    if (currentMode !== "both" && file.kind !== currentMode) {
      return {
        error: `⚠️ Выбрана ведомость ${orgLabel(file.kind)}, а режим расчёта — ${orgLabel(currentMode)}. Выберите файл другой организации или измените режим.`,
      };
    }
    return { files: [{ kind: file.kind, path: file.path }] };
  }

  const domFiles = usable.filter((file) => file.kind === "dom");
  const gorodFiles = usable.filter((file) => file.kind === "gorod");

  if (currentMode === "dom" || currentMode === "gorod") {
    const candidates = currentMode === "dom" ? domFiles : gorodFiles;
    if (candidates.length === 0) {
      return { error: `⚠️ В папке не найдена ведомость ${orgLabel(currentMode)}.` };
    }
    if (candidates.length > 1) {
      return { error: "⚠️ В папке несколько исходных ведомостей одной организации. Оставьте одну и повторите расчёт." };
    }
    return { files: [{ kind: currentMode, path: candidates[0].path }], outputDir: detected.path };
  }

  if (domFiles.length > 1 || gorodFiles.length > 1) {
    return {
      error: "⚠️ В папке несколько исходных ведомостей одной организации. Оставьте по одной ведомости «Дом» и «Город».",
    };
  }
  if (domFiles.length === 0 && gorodFiles.length === 0) {
    return { error: "⚠️ В папке не найдены ведомости ТНС (.xlsx)." };
  }

  const files: PlannedFile[] = [];
  if (domFiles[0]) files.push({ kind: "dom", path: domFiles[0].path });
  if (gorodFiles[0]) files.push({ kind: "gorod", path: gorodFiles[0].path });

  const warning =
    domFiles.length === 0
      ? `⚠️ Ведомость ${orgLabel("dom")} не найдена — обработана только ${orgLabel("gorod")}.`
      : gorodFiles.length === 0
        ? `⚠️ Ведомость ${orgLabel("gorod")} не найдена — обработана только ${orgLabel("dom")}.`
        : undefined;

  return { files, outputDir: detected.path, warning };
};

function MetricCard({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${tone}`}>{value}</div>
    </div>
  );
}

function ResultsTable({ rows }: { rows: ProcessResult["preview_rows"] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>№</th>
            <th>Адрес дома (Объект)</th>
            <th>Энергия День</th>
            <th>Энергия Ночь</th>
            <th>ОДН</th>
            <th>ИТОГО начислено</th>
            <th>Контроль (ст. АВ)</th>
            <th>Отклонение</th>
            <th>Приборы (раб/рез)</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td className="table-empty" colSpan={9}>
                Нет данных — выполните расчёт.
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={row.num}>
                <td>{row.num}</td>
                <td>{row.name}</td>
                <td>{fmt(row.day)}</td>
                <td>{fmt(row.night)}</td>
                <td>{fmt(row.odn)}</td>
                <td className="strong">{fmt(row.total)}</td>
                <td>{fmt(row.control)}</td>
                <td className={row.diff === 0 ? "ok" : "bad"}>{fmt(row.diff)}</td>
                <td>{`${row.meters_active} раб. / ${row.meters_res} рез.`}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [mode, setMode] = useState<Mode>("both");
  const [tab, setTab] = useState<Tab>("dom");
  const [month, setMonth] = useState("Апрель");
  const [year, setYear] = useState("2026");
  const [source, setSource] = useState("");
  const [status, setStatus] = useState("Готов к работе");
  const [calculating, setCalculating] = useState(false);
  const [progress, setProgress] = useState({ percent: 0, message: "" });
  const [detect, setDetect] = useState<DetectResult | null>(null);
  const [results, setResults] = useState<ResultsMap>({});
  const [helpOpen, setHelpOpen] = useState(false);
  const [helpTab, setHelpTab] = useState<HelpTab>("checks");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [backupMessage, setBackupMessage] = useState("");

  const modeRef = useRef<Mode>(mode);
  const processingKindRef = useRef<Tab | null>(null);
  const cancelledRef = useRef(false);

  useEffect(() => {
    if (!calculating) modeRef.current = mode;
  }, [mode, calculating]);

  useEffect(() => {
    let disposed = false;
    let unlisten: (() => void) | null = null;
    listenProcessProgress((event) => {
      let percent = clamp(event.percent, 0, 100);
      if (modeRef.current === "both" && processingKindRef.current === "dom") {
        percent = clamp(event.percent * 0.45, 5, 45);
      } else if (modeRef.current === "both" && processingKindRef.current === "gorod") {
        percent = clamp(50 + event.percent * 0.45, 50, 95);
      }
      setProgress({ percent, message: event.message });
    })
      .then((stop) => {
        if (disposed) stop();
        else unlisten = stop;
      })
      .catch(() => {
        // A failed listener must not break the UI; progress simply stays at the last value.
      });
    return () => {
      disposed = true;
      if (unlisten) unlisten();
    };
  }, []);

  const visibleTabs: Tab[] = mode === "both" ? ["dom", "gorod"] : [mode];
  const resultTabs = visibleTabs.filter((key) => results[key] !== undefined);
  const activeTab: Tab = visibleTabs.includes(tab) && results[tab] ? tab : (resultTabs[0] ?? visibleTabs[0]);
  const activeResult = results[activeTab];
  const hint = detect ? describeDetect(detect) : DEFAULT_HINT;

  const selectSource = async (target: "folder" | "file") => {
    if (calculating) return;
    try {
      const selected = target === "folder" ? await pickFolder() : await pickFile();
      if (!selected) return;
      setSource(selected);
      setDetect(null);
      setResults({});
      setProgress({ percent: 0, message: "" });
      setStatus("Проверка исходных данных...");
      try {
        const detected = await detectStatement(selected);
        setDetect(detected);
        setStatus("Готов к работе");
      } catch (error) {
        setStatus(`⚠️ ${errorText(error)}`);
      }
    } catch (error) {
      setStatus(`⚠️ ${errorText(error)}`);
    }
  };

  const calculate = async () => {
    if (calculating) return;
    if (!detect) {
      setStatus("⚠️ Сначала выберите файл или папку с исходными данными.");
      return;
    }
    const plan = planCalculation(detect, mode);
    if ("error" in plan) {
      setStatus(plan.error);
      return;
    }

    const collected: ResultsMap = {};
    const warnings: string[] = plan.warning ? [plan.warning] : [];
    setCalculating(true);
    setProgress({ percent: 5, message: "Подготовка..." });
    setResults({});
    setStatus("Идёт расчёт...");
    setTab(plan.files[0].kind);
    modeRef.current = mode;
    cancelledRef.current = false;

    try {
      for (const [index, file] of plan.files.entries()) {
        if (cancelledRef.current) break;
        processingKindRef.current = file.kind;
        setStatus(`Расчёт ${orgLabel(file.kind)}...`);

        const result = await processStatement({
          sourcePath: file.path,
          outputDir: plan.outputDir,
          month,
          year,
        });

        collected[file.kind] = result;
        setResults({ ...collected });
        setTab(file.kind);
        if (result.warning) warnings.push(result.warning);
        if (result.history_warning) warnings.push(result.history_warning);

        if (cancelledRef.current) break;

        const summary = `✅ ${result.consumer} · ${result.period}: домов ${result.houses_count}, итого ${fmt(result.total_all)} кВт*ч`;
        setStatus(warnings.length > 0 ? `${summary} ${warnings.map((warning) => `⚠️ ${warning}`).join(" ")}` : summary);
        if (index < plan.files.length - 1) setProgress({ percent: 45, message: "Дом готов" });
      }

      if (cancelledRef.current) {
        setStatus("Отмена...");
      } else {
        setProgress({ percent: 100, message: "Готово" });
        const parts = plan.files.flatMap((file) => {
          const result = collected[file.kind];
          return result
            ? [`${orgLabel(file.kind)} — ${result.houses_count} домов, ${fmt(result.total_all)} кВт*ч`]
            : [];
        });
        const warningParts = warnings.map((warning) => `⚠️ ${warning}`);
        setStatus([`✅ Расчёт завершён: ${parts.join("; ")}`, ...warningParts].join(" "));
      }
    } catch (error) {
      if (isCancellation(error)) {
        setStatus(`⏹ ${errorText(error)}`);
        setProgress({ percent: 0, message: "Отменено" });
      } else {
        setStatus(`⚠️ ${errorText(error)}`);
        setProgress({ percent: 0, message: "Ошибка" });
      }
    } finally {
      processingKindRef.current = null;
      setCalculating(false);
      cancelledRef.current = false;
    }
  };

  const cancelCalculation = () => {
    cancelledRef.current = true;
    setStatus("Отмена...");
    cancelStatement().catch((error: unknown) => setStatus(`⚠️ ${errorText(error)}`));
  };

  const openHistory = async () => {
    setHistoryOpen(true);
    setHistoryLoading(true);
    setHistoryError(null);
    setBackupMessage("");
    try {
      setHistory(await historyList(50));
    } catch (error) {
      setHistoryError(errorText(error));
    } finally {
      setHistoryLoading(false);
    }
  };

  const createBackup = async () => {
    setBackupMessage("Создание бэкапа...");
    try {
      const path = await backupDb();
      setBackupMessage(`✅ Бэкап создан: ${path}`);
    } catch (error) {
      setBackupMessage(`⚠️ ${errorText(error)}`);
    }
  };

  const openResultFile = () => {
    if (!activeResult) return;
    openFile(activeResult.target_path).catch((error: unknown) => setStatus(`⚠️ ${errorText(error)}`));
  };

  const openResultFolder = () => {
    if (!activeResult) return;
    openFolder(activeResult.target_dir).catch((error: unknown) => setStatus(`⚠️ ${errorText(error)}`));
  };

  return (
    <div className="app">
      <header className="header card">
        <div>
          <h1>ТНС ЭНЕРГО • СТУДИЯ РАСЧЁТА НАЧИСЛЕНИЙ</h1>
          <p className="subtitle">День · Ночь · ОДН&nbsp;&nbsp;|&nbsp;&nbsp;Проверка баланса&nbsp;&nbsp;|&nbsp;&nbsp;v0.2.0</p>
        </div>
        <div>
          <button className="btn ghost" onClick={() => void openHistory()}>🕘 История</button>{" "}
          <button className="btn ghost" onClick={() => setHelpOpen(true)}>ℹ️ Справка и аудит</button>
        </div>
      </header>

      <section className="card settings">
        <div className="mode-row">
          <span className="label">Режим расчёта:</span>
          <label><input type="radio" name="mode" disabled={calculating} checked={mode === "both"} onChange={() => setMode("both")} /> Пакетный расчёт (Дом + Город)</label>
          <label><input type="radio" name="mode" disabled={calculating} checked={mode === "dom"} onChange={() => setMode("dom")} /> Только ООО «Южный Дом»</label>
          <label><input type="radio" name="mode" disabled={calculating} checked={mode === "gorod"} onChange={() => setMode("gorod")} /> Только ООО «Южный Город»</label>
        </div>

        <div className="source-row">
          <span className="label">Исходные данные:</span>
          <input className="path-input" value={source} readOnly placeholder="Путь не выбран" />
          <button className="btn" disabled={calculating} onClick={() => void selectSource("folder")}>📁 Выбрать папку</button>
          <button className="btn" disabled={calculating} onClick={() => void selectSource("file")}>📄 Выбрать файл</button>
        </div>

        <div className="hint">{hint}</div>

        <div className="settings-grid">
          <div>
            <span className="label">Расчётный месяц:</span>
            <select value={month} disabled={calculating} onChange={(e) => setMonth(e.target.value)}>
              {MONTHS.map((m) => <option key={m}>{m}</option>)}
            </select>
          </div>
          <div>
            <span className="label">Год:</span>
            <select value={year} disabled={calculating} onChange={(e) => setYear(e.target.value)}>
              {YEARS.map((y) => <option key={y}>{y}</option>)}
            </select>
          </div>
          <div className="output-preview">
            Автосохранение в подпапку:<br />
            <strong>📁 Папка: {month} {year} ТНС</strong><br />
            Дом_{month}_{year}.xlsx и Город_{month}_{year}.xlsx
          </div>
          <button className="btn primary calculate" onClick={() => void calculate()} disabled={calculating}>
            {calculating ? "⏳ Расчёт..." : "⚡ ВЫПОЛНИТЬ РАСЧЁТ"}
          </button>
        </div>
      </section>

      <div className={status.startsWith("✅") ? "status success" : "status"}>{status}</div>

      <div>
        <div className="progress">
          <div className="progress-fill" style={{ width: `${clamp(progress.percent, 0, 100)}%` }} />
        </div>
        {calculating && (
          <div className="progress-label">
            <span>{progress.message} · {Math.round(progress.percent)}%</span>
            <button className="btn danger" onClick={cancelCalculation}>✕ Отменить</button>
          </div>
        )}
      </div>

      <div className="tabs">
        {visibleTabs.map((key) => (
          <button key={key} className={`tab ${activeTab === key ? "active" : ""}`} onClick={() => setTab(key)}>
            {key === "dom" ? "🏠 ООО «Южный Дом»" : "🏢 ООО «Южный Город»"}
          </button>
        ))}
      </div>

      <section className="card results">
        <div className="metrics">
          <MetricCard label="ЭНЕРГИЯ ДЕНЬ" value={energy(activeResult?.total_day)} tone="warning" />
          <MetricCard label="ЭНЕРГИЯ НОЧЬ" value={energy(activeResult?.total_night)} tone="purple" />
          <MetricCard label="ОДН" value={energy(activeResult?.total_odn)} tone="success" />
          <MetricCard label="ИТОГО НАЧИСЛЕНО" value={energy(activeResult?.total_all)} tone="accent" />
        </div>
        <ResultsTable rows={activeResult?.preview_rows ?? []} />
      </section>

      <footer className="footer">
        <button className="btn" onClick={openResultFile} disabled={!activeResult}>
          📊 Открыть рассчитанный файл в Excel
        </button>
        <button className="btn" onClick={openResultFolder} disabled={!activeResult}>
          📂 Открыть папку с файлами ТНС
        </button>
        <div className="balance">
          Баланс начислений:{" "}
          {activeResult ? (
            <span className={activeResult.balance_ok || activeResult.balance_diff === 0 ? "ok" : "bad"}>
              {activeResult.balance_ok || activeResult.balance_diff === 0
                ? "✅ сходится"
                : `⚠️ расхождение ${fmt(activeResult.balance_diff)}`}
            </span>
          ) : (
            <span>—</span>
          )}
        </div>
      </footer>

      {helpOpen && (
        <div className="modal-backdrop" onClick={() => setHelpOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h2>Справка и аудит</h2>
              <button className="btn ghost" onClick={() => setHelpOpen(false)}>✕</button>
            </div>
            <div className="modal-tabs">
              <button className={helpTab === "checks" ? "active" : ""} onClick={() => setHelpTab("checks")}>
                🔍 Как проверяются файлы и находятся счётчики
              </button>
              <button className={helpTab === "fixes" ? "active" : ""} onClick={() => setHelpTab("fixes")}>
                🛡️ Защита от будущих ошибок (Smart Fixes)
              </button>
            </div>
            <div className="modal-body">
              {helpTab === "checks" ? (
                <>
                  <p>Приложение ищет в ведомости колонку «Тип» и строки 100/101/102: дом, вводной прибор учёта и субабонент.</p>
                  <p>Колонки определяются по заголовкам, а не по жёстким номерам. Если заголовок «Начисленный объём» или «Зона тарифа» не найден, расчёт останавливается с понятной ошибкой.</p>
                  <p>Контроль сходится, когда сумма начислений по приборам совпадает с итоговой строкой ведомости.</p>
                  <p>Все операции выполняются локально через команды Tauri; данные не покидают компьютер.</p>
                </>
              ) : (
                <>
                  <p>Перед записью результата приложение делает временный файл и атомарно заменяет целевой. Если Excel держит файл открытым, создаётся копия с меткой времени.</p>
                  <p>Перед расчётом проверяются типы строк, зоны тарифа, числовые значения и итоговая строка. Ошибка в одной ячейке не приводит к молчаливой порче файла.</p>
                  <p>История расчётов сохраняется локально в SQLite; облачная синхронизация в новой версии отключена.</p>
                </>
              )}
            </div>
            <div className="modal-foot">
              <button className="btn primary" onClick={() => setHelpOpen(false)}>Закрыть</button>
            </div>
          </div>
        </div>
      )}

      {historyOpen && (
        <div className="modal-backdrop" onClick={() => setHistoryOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h2>История расчётов</h2>
              <button className="btn ghost" onClick={() => setHistoryOpen(false)}>✕</button>
            </div>
            <div className="modal-body">
              {historyLoading ? (
                <div className="history-empty">Загрузка истории...</div>
              ) : historyError ? (
                <div className="history-empty bad">{historyError}</div>
              ) : history.length === 0 ? (
                <div className="history-empty">История расчётов пуста.</div>
              ) : (
                <div className="history-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Период</th>
                        <th>Организация</th>
                        <th>Домов</th>
                        <th>Итого</th>
                        <th>Баланс</th>
                        <th>Файл</th>
                        <th>Дата</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((entry) => (
                        <tr key={entry.id}>
                          <td>{entry.period_month} {entry.period_year}</td>
                          <td>
                            {entry.org_name}
                            <br />
                            <span className="label">договор {entry.contract_number || "—"}</span>
                          </td>
                          <td>{entry.houses_count}</td>
                          <td className="strong">{fmt(entry.total_all)}</td>
                          <td className={entry.balance_diff === 0 ? "ok" : "bad"}>
                            {entry.balance_diff === 0 ? "✅" : `⚠️ ${fmt(entry.balance_diff)}`}
                          </td>
                          <td>{entry.saved_filename ?? "—"}</td>
                          <td>{entry.calculated_at}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {backupMessage && (
                <div className={backupMessage.startsWith("✅") ? "status success" : "status"}>{backupMessage}</div>
              )}
            </div>
            <div className="modal-foot">
              <button className="btn backup" onClick={() => void createBackup()}>💾 Создать бэкап БД</button>
              <button className="btn primary" onClick={() => setHistoryOpen(false)}>Закрыть</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
