import { useState } from "react";
import { domRows, gorodRows, totals, MONTHS, YEARS, type ResultRow } from "./data";
import "./styles.css";

type Mode = "both" | "dom" | "gorod";
type Tab = "dom" | "gorod";
type HelpTab = "checks" | "fixes";

const fmt = (value: number) => value.toFixed(3);

function MetricCard({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${tone}`}>{value}</div>
    </div>
  );
}

function ResultsTable({ rows }: { rows: ResultRow[] }) {
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
          {rows.map((row) => (
            <tr key={row.num}>
              <td>{row.num}</td>
              <td>{row.name}</td>
              <td>{fmt(row.day)}</td>
              <td>{fmt(row.night)}</td>
              <td>{fmt(row.odn)}</td>
              <td className="strong">{fmt(row.total)}</td>
              <td>{fmt(row.control)}</td>
              <td className={row.diff === 0 ? "ok" : "bad"}>{fmt(row.diff)}</td>
              <td>{row.meters}</td>
            </tr>
          ))}
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
  const [source, setSource] = useState("C:\\Users\\admin\\AppData\\Local\\Programs\\TNS_Studio");
  const [status, setStatus] = useState("Готов к работе");
  const [calculating, setCalculating] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [helpTab, setHelpTab] = useState<HelpTab>("checks");

  const visibleTabs: Tab[] = mode === "both" ? ["dom", "gorod"] : [mode];
  const activeTab: Tab = visibleTabs.includes(tab) ? tab : visibleTabs[0];
  const rows = activeTab === "dom" ? domRows : gorodRows;
  const t = totals[activeTab];

  const calculate = () => {
    setCalculating(true);
    setStatus("Идёт расчёт...");
    window.setTimeout(() => {
      setCalculating(false);
      setStatus(`✅ Расчёт завершён! Папка: ${month} ${year} ТНС`);
    }, 700);
  };

  return (
    <div className="app">
      <header className="header card">
        <div>
          <h1>ТНС ЭНЕРГО • СТУДИЯ РАСЧЁТА НАЧИСЛЕНИЙ</h1>
          <p className="subtitle">День · Ночь · ОДН&nbsp;&nbsp;|&nbsp;&nbsp;Проверка баланса&nbsp;&nbsp;|&nbsp;&nbsp;v2.2.4</p>
        </div>
        <button className="btn ghost" onClick={() => setHelpOpen(true)}>ℹ️ Справка и аудит</button>
      </header>

      <section className="card settings">
        <div className="mode-row">
          <span className="label">Режим расчёта:</span>
          <label><input type="radio" name="mode" checked={mode === "both"} onChange={() => setMode("both")} /> Пакетный расчёт (Дом + Город)</label>
          <label><input type="radio" name="mode" checked={mode === "dom"} onChange={() => setMode("dom")} /> Только ООО «Южный Дом»</label>
          <label><input type="radio" name="mode" checked={mode === "gorod"} onChange={() => setMode("gorod")} /> Только ООО «Южный Город»</label>
        </div>

        <div className="source-row">
          <span className="label">Исходные данные:</span>
          <input className="path-input" value={source} readOnly onChange={(e) => setSource(e.target.value)} />
          <button className="btn">📁 Выбрать папку</button>
          <button className="btn">📄 Выбрать файл</button>
        </div>

        <div className="hint">ℹ️ В папке найдено 0 файлов .xlsx. Ведомости ТНС определяются при расчёте.</div>

        <div className="settings-grid">
          <div>
            <span className="label">Расчётный месяц:</span>
            <select value={month} onChange={(e) => setMonth(e.target.value)}>
              {MONTHS.map((m) => <option key={m}>{m}</option>)}
            </select>
          </div>
          <div>
            <span className="label">Год:</span>
            <select value={year} onChange={(e) => setYear(e.target.value)}>
              {YEARS.map((y) => <option key={y}>{y}</option>)}
            </select>
          </div>
          <div className="output-preview">
            Автосохранение в подпапку:<br />
            <strong>📁 Папка: {month} {year} ТНС</strong><br />
            Дом_{month}_{year}.xlsx и Город_{month}_{year}.xlsx
          </div>
          <button className="btn primary calculate" onClick={calculate} disabled={calculating}>
            {calculating ? "⏳ Расчёт..." : "⚡ ВЫПОЛНИТЬ РАСЧЁТ"}
          </button>
        </div>
      </section>

      <div className={status.startsWith("✅") ? "status success" : "status"}>{status}</div>

      <div className="tabs">
        {visibleTabs.map((key) => (
          <button key={key} className={`tab ${activeTab === key ? "active" : ""}`} onClick={() => setTab(key)}>
            {key === "dom" ? "🏠 ООО «Южный Дом»" : "🏢 ООО «Южный Город»"}
          </button>
        ))}
      </div>

      <section className="card results">
        <div className="metrics">
          <MetricCard label="ЭНЕРГИЯ ДЕНЬ" value={`${fmt(t.day)} кВт*ч`} tone="warning" />
          <MetricCard label="ЭНЕРГИЯ НОЧЬ" value={`${fmt(t.night)} кВт*ч`} tone="purple" />
          <MetricCard label="ОДН" value={`${fmt(t.odn)} кВт*ч`} tone="success" />
          <MetricCard label="ИТОГО НАЧИСЛЕНО" value={`${fmt(t.total)} кВт*ч`} tone="accent" />
        </div>
        <ResultsTable rows={rows} />
      </section>

      <footer className="footer">
        <button className="btn">📊 Открыть рассчитанный файл в Excel</button>
        <button className="btn">📂 Открыть папку с файлами ТНС</button>
        <div className="balance">Баланс начислений: <span className="ok">✅ сходится</span></div>
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
    </div>
  );
}
