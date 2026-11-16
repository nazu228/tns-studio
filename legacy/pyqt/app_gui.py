import os
import sys
import math

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QRadioButton, QButtonGroup,
    QFileDialog, QMessageBox, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QFrame, QScrollArea, QSizePolicy, QDialog, QTextBrowser
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QIcon

from core_engine import process_statement, detect_statement_type, MONTHS_RU
from sync_manager import (
    S3Config, DatabaseManager, DEFAULT_APP_VERSION, DEFAULT_APP_NAME,
    CheckUpdatesWorker
)
from ui_sync_components import (
    ToastManager, S3StatusBadge, CloudSyncDialog, UpdateModalDialog
)

# ==============================================================================
# ДИАЛОГ СПРАВКИ И АУДИТА АЛГОРИТМА
# ==============================================================================
class AlgorithmHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Аудит алгоритма ТНС Энерго и превентивная защита от ошибок")
        self.resize(980, 700)
        self.setMinimumSize(840, 580)
        self.init_ui()
        if parent:
            self.setStyleSheet(parent.styleSheet() + """
                QDialog {
                    background-color: #0F172A;
                }
                QTextBrowser {
                    background-color: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 8px;
                }
            """)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        tabs = QTabWidget()
        tabs.setObjectName("helpTabs")

        # Вкладка 1: Проверка файлов и нахождение счетчиков
        t1 = QTextBrowser()
        t1.setOpenExternalLinks(True)
        t1.setStyleSheet("background-color: #1E293B; color: #F1F5F9; font-family: 'Segoe UI'; font-size: 13px; padding: 16px; border: 1px solid #334155; border-radius: 8px;")
        t1.setHtml("""
        <h2 style="color: #38BDF8; margin-top: 0; font-size: 18px;">🔍 Как программа проверяет файлы и находит счетчики</h2>
        <hr style="border: 0; height: 1px; background: #334155; margin-bottom: 16px;">

        <h3 style="color: #F59E0B; margin-bottom: 4px;">1. Автоматическая идентификация ведомости и организации</h3>
        <p style="color: #CBD5E1; line-height: 1.5;">Программа <b>не привязана к имени файла</b>. Она проверяет фактические ячейки в шапке (строки 3–4):</p>
        <ul style="color: #E2E8F0; line-height: 1.6;">
            <li>По номеру договора <b>23110603789</b> или слову «Дом» → <b>ООО «Южный Дом»</b> (3 МКД).</li>
            <li>По номеру договора <b>23110604327</b> или слову «Город» → <b>ООО «Южный Город»</b> (22 МКД).</li>
        </ul>

        <h3 style="color: #F59E0B; margin-bottom: 4px;">2. Структура строк ведомости 1С ТНС (Типы строк)</h3>
        <p style="color: #CBD5E1; line-height: 1.5;">В столбце 1 (A) ТНС проставляет системные коды строк:</p>
        <ul style="color: #E2E8F0; line-height: 1.6;">
            <li><b>Тип 100</b>: Заголовок дома с адресом объекта (в столбце C). При этом в самом конце ведомости строка Тип 100 со словом <code>Итого:</code> в столбце B — это контрольный сводный итог всей ведомости.</li>
            <li><b>Тип 101</b>: Вводные приборы учета начисления электроэнергии (ВРУ / ОДПУ). Именно из этих строк берутся киловатт-часы из столбца <b>AB (Начисленный объем)</b>.</li>
            <li><b>Тип 102</b>: Субабоненты (провайдеры интернета ТКД ШПД, домофоны, арендаторы). Их объем <b>уже вычтен</b> поставщиком из домового расхода в столбце W. Они изолируются и не суммируются с начислениями дома.</li>
        </ul>

        <h3 style="color: #F59E0B; margin-bottom: 4px;">3. Классификация приборов по 3-м показателям</h3>
        <p style="color: #CBD5E1; line-height: 1.5;">Программа анализирует столбец «Зона тарифа»:</p>
        <ul style="color: #E2E8F0; line-height: 1.6;">
            <li><b style="color: #F59E0B;">⚡ Энергия День</b>: Зоны «День (2-х зонный)», «Т1», «Пик», «Полупик».</li>
            <li><b style="color: #818CF8;">🌙 Энергия Ночь</b>: Зоны «Ночь (2-х зонный)», «Т2».</li>
            <li><b style="color: #34D399;">💡 ОДН</b>: Вводы нежилых помещений (ОДПУ МКД НП), лифты, ИТП, насосные, одноставочные тарифы без деления по зонам суток, круглосуточные, метка «ЗР».</li>
        </ul>

        <h3 style="color: #F59E0B; margin-bottom: 4px;">4. Физический смысл «нулевых» счетчиков (АВР-2)</h3>
        <p style="color: #CBD5E1; line-height: 1.5;">В жилых МКД по правилам ПУЭ каждое ВРУ обязано иметь <b>два независимых ввода</b> (1-я категория надежности):</p>
        <ul style="color: #E2E8F0; line-height: 1.6;">
            <li><b>Рабочий ввод (Ввод-1 / АВР-1)</b>: несет 100% текущей нагрузки дома.</li>
            <li><b>Резервный ввод (АВР-2 / Ввод-2)</b>: находится в «холодном резерве». При штатной работе расход по нему равен <b>0 кВт*ч</b> (нач. показание = кон. показанию).</li>
        </ul>
        <p style="color: #CBD5E1; line-height: 1.5;"><b>Почему они обязательно включены в формулы <code>=SUM(...)</code>?</b><br>
        Если на кабельной линии Ввод-1 произойдет ремонт или авария и дом переключится на ввод АВР-2, киловатты начнут учитываться резервным счетчиком. Благодаря включению в формулу Excel расчет мгновенно и безошибочно учтет этот расход!</p>

        <h3 style="color: #F59E0B; margin-bottom: 4px;">5. Сквозной контроль баланса и двухстраничная модель</h3>
        <p style="color: #CBD5E1; line-height: 1.5;">Книга состоит из 2 листов для мгновенной проверки человеком:</p>
        <ul style="color: #E2E8F0; line-height: 1.6;">
            <li><b>Лист «Ведомость ЭП»</b>: полная ведомость 1С строка-в-строку. В строке каждого дома встроены формулы <code>=SUM(AB...)</code>, подсвечивающие слагаемые ячейки при клике в Excel.</li>
            <li><b>Лист «Сводка по домам» (Дашборд)</b>: содержит простые прозрачные ссылки <code>='Ведомость ЭП'!XY</code> на ячейки ведомости. Клик по названию дома переносит сразу к его счетчикам!</li>
        </ul>
        <p style="color: #CBD5E1; line-height: 1.5;">Баланс сходится с точностью до <b>0.000 кВт*ч</b>, отклонение подсвечивается мягким зеленым цветом.</p>
        """)

        # Вкладка 2: Превентивная защита от будущих ошибок
        t2 = QTextBrowser()
        t2.setOpenExternalLinks(True)
        t2.setStyleSheet("background-color: #1E293B; color: #F1F5F9; font-family: 'Segoe UI'; font-size: 13px; padding: 16px; border: 1px solid #334155; border-radius: 8px;")
        t2.setHtml("""
        <h2 style="color: #38BDF8; margin-top: 0; font-size: 18px;">🛡️ Превентивная защита от будущих ошибок (Smart Fixes)</h2>
        <hr style="border: 0; height: 1px; background: #334155; margin-bottom: 16px;">

        <table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; border-color: #334155; width: 100%; color: #E2E8F0;">
            <tr style="background-color: #0F172A; color: #38BDF8; font-weight: bold;">
                <th style="width: 32%; text-align: left;">Возможная будущая проблема</th>
                <th style="text-align: left;">Как решено в коде программы (Умное исправление)</th>
            </tr>
            <tr>
                <td><b>1. Сдвиг столбцов в 1С ТНС</b><br><span style="color: #94A3B8; font-size: 12px;">Если ТНС добавит или уберет столбец, столбец AB перестанет быть 28-м.</span></td>
                <td><b>Функция <code>resolve_columns</code>:</b> динамически сканирует шапку таблицы по ключевым словам («начисленный объем», «заводской номер», «зона тарифа»). Программа автоматически определит новый номер столбца и перестроит формулы.</td>
            </tr>
            <tr>
                <td><b>2. Файл открыт в Excel (Блокировка Windows)</b><br><span style="color: #94A3B8; font-size: 12px;">При попытке перезаписи открытого файла Windows выдает PermissionError.</span></td>
                <td><b>Функция <code>safe_save_workbook</code>:</b> перехватывает блокировку, сохраняет данные в копию <code>_(закрыт_в_Excel_HHMMSS).xlsx</code> без аварийного закрытия и вежливо предупреждает пользователя.</td>
            </tr>
            <tr>
                <td><b>3. Новые названия тарифных зон</b><br><span style="color: #94A3B8; font-size: 12px;">Появление обозначений «Т1», «Т2», «Пик», латинских букв «T1», пробелов.</span></td>
                <td><b>Устойчивый классификатор <code>classify_zone</code>:</b> нормализует регистр, заменяет латиницу, распознает сокращения и группирует 3-зонные тарифы в День/Ночь/ОДН.</td>
            </tr>
            <tr>
                <td><b>4. Нечисловые форматы ячеек</b><br><span style="color: #94A3B8; font-size: 12px;">Символы "-", пробелы, неразрывные пробелы, запятые вместо точек.</span></td>
                <td><b>Безопасный парсер <code>safe_float</code>:</b> очищает строки от скрытых символов, преобразует запятые в точки и возвращает <code>0.0</code> вместо критической ошибки.</td>
            </tr>
            <tr>
                <td><b>5. Ошибка путей и нагромождение файлов</b><br><span style="color: #94A3B8; font-size: 12px;">Файлы сохраняются в общую кучу или теряются.</span></td>
                <td><b>Автоматическая папка <code>&lt;Месяц&gt; &lt;Год&gt; ТНС</code>:</b> программа сама создает чистую отдельную папку под текущий расчетный период и сохраняет готовые файлы туда.</td>
            </tr>
            <tr>
                <td><b>6. Ошибочный выбор файлов в папке</b><br><span style="color: #94A3B8; font-size: 12px;">Пользователь указал папку с множеством сторонних таблиц.</span></td>
                <td><b>Умный детектор договоров:</b> программа сама находит нужные ведомости в папке по договорам 23110603789 и 23110604327, исключая временные файлы Excel <code>~$...</code>.</td>
            </tr>
        </table>
        """)

        tabs.addTab(t1, "🔍 Как проверяются файлы и находятся счетчики")
        tabs.addTab(t2, "🛡️ Защита от будущих ошибок (Smart Fixes)")

        layout.addWidget(tabs, stretch=1)

        bottom_box = QHBoxLayout()
        bottom_box.addStretch()
        btn_close = QPushButton("Закрыть справку")
        btn_close.setObjectName("btnPrimary")
        btn_close.setMinimumWidth(160)
        btn_close.clicked.connect(self.accept)
        bottom_box.addWidget(btn_close)
        layout.addLayout(bottom_box)


# ==============================================================================
# WORKER THREAD ДЛЯ РАСЧЕТА БЕЗ ЗАВИСАНИЯ ИНТЕРФЕЙСА
# ==============================================================================
class CalculationWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, mode, folder_or_file, month, year, output_dir):
        super().__init__()
        self.mode = mode  # 'dom', 'gorod', 'both'
        self.folder_or_file = folder_or_file
        self.month = month
        self.year = year
        self.output_dir = output_dir

    def run(self):
        try:
            results = {}
            if self.mode == "both":
                folder = self.folder_or_file if os.path.isdir(self.folder_or_file) else os.path.dirname(self.folder_or_file)
                files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".xlsx") and not f.startswith("~$")]
                
                dom_file = None
                gorod_file = None
                recognized={"dom":[],"gorod":[]}
                for candidate in files:
                    kind,_,_=detect_statement_type(candidate)
                    if kind in recognized:recognized[kind].append(candidate)
                if any(len(paths)>1 for paths in recognized.values()):
                    raise ValueError("В папке несколько исходных ведомостей одной организации. Оставьте по одной ведомости нужного периода, чтобы не выбрать неверный файл.")
                for f in sorted(files):
                    st_type, _, _ = detect_statement_type(f)
                    if st_type == "dom" and not dom_file:
                        dom_file = f
                    elif st_type == "gorod" and not gorod_file:
                        gorod_file = f

                if not dom_file and not gorod_file:
                    raise Exception(f"В папке {folder} не найдены ведомости ТНС Энерго (Южный Дом / Южный Город).")

                if dom_file:
                    self.progress.emit(10, f"Расчет Южный Дом: {os.path.basename(dom_file)}")
                    def prog_dom(val, msg):
                        self.progress.emit(int(val * 0.45), f"Дом: {msg}")
                    r_dom = process_statement(dom_file, self.output_dir, month=self.month, year=self.year, progress_callback=prog_dom, cancel_callback=self.isInterruptionRequested)
                    results["dom"] = r_dom

                if gorod_file:
                    self.progress.emit(50, f"Расчет Южный Город: {os.path.basename(gorod_file)}")
                    def prog_gor(val, msg):
                        self.progress.emit(int(50 + val * 0.45), f"Город: {msg}")
                    r_gor = process_statement(gorod_file, self.output_dir, month=self.month, year=self.year, progress_callback=prog_gor, cancel_callback=self.isInterruptionRequested)
                    results["gorod"] = r_gor

                self.progress.emit(100, "Пакетный расчет успешно завершен!")

            else:
                filepath = self.folder_or_file
                if os.path.isdir(filepath):
                    target_type = self.mode
                    files = [os.path.join(filepath, f) for f in os.listdir(filepath) if f.lower().endswith(".xlsx") and not f.startswith("~$")]
                    matching=[f for f in files if detect_statement_type(f)[0]==target_type]
                    if len(matching)>1:raise ValueError("В папке несколько ведомостей нужной организации; выберите конкретный исходный файл.")
                    found = None
                    for f in sorted(files):
                        st_type, _, _ = detect_statement_type(f)
                        if st_type == target_type:
                            found = f
                            break
                    if not found:
                        org_name = "Южный Дом" if self.mode == "dom" else "Южный Город"
                        raise Exception(f"В папке не найден файл ведомости для {org_name}.")
                    filepath = found

                kind,_,_=detect_statement_type(filepath)
                if kind!=self.mode:
                    raise ValueError("Выбранный файл не соответствует организации или не является исходной ведомостью ТНС.")
                def prog(val, msg):
                    self.progress.emit(val, msg)

                r = process_statement(filepath, self.output_dir, month=self.month, year=self.year, progress_callback=prog, cancel_callback=self.isInterruptionRequested)
                results[self.mode] = r

            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))


# ==============================================================================
# ГЛАВНОЕ ОКНО ПРИЛОЖЕНИЯ (LUXURY COBALT ТЕМА)
# ==============================================================================
class TNSEnergyStudioWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.s3_config = S3Config()
        self.db_manager = DatabaseManager()
        self.toast_manager = ToastManager(self)

        self.setWindowTitle(f"ТНС Энерго — Студия начислений по домам v{DEFAULT_APP_VERSION}")
        self.resize(1280, 880)
        self.setMinimumSize(1060, 720)

        # Текущая рабочая папка
        if getattr(sys, 'frozen', False):
            self.default_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            self.default_dir = os.path.abspath(os.path.dirname(__file__))
        self.current_results = {}
        self.current_target_dir = None

        self.init_ui()
        self.apply_theme()
        self.auto_detect_in_folder(self.default_dir)

        # Фоновая проверка обновлений при запуске
        if self.s3_config.auto_check_updates:
            QTimer.singleShot(1500, self.silent_check_updates)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # =====================================================================
        # 1. ШАПКА ПРИЛОЖЕНИЯ (HEADER)
        # =====================================================================
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 14, 20, 14)
        header_layout.setSpacing(12)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(4)
        
        app_title = QLabel("ТНС ЭНЕРГО • СТУДИЯ РАСЧЕТА НАЧИСЛЕНИЙ")
        app_title.setObjectName("appTitle")
        
        app_subtitle = QLabel(f"День · Ночь · ОДН   |   Проверка баланса   |   v{DEFAULT_APP_VERSION}")
        app_subtitle.setWordWrap(True)
        app_title.setWordWrap(True)
        app_subtitle.setObjectName("appSubtitle")
        
        title_vbox.addWidget(app_title)
        title_vbox.addWidget(app_subtitle)

        header_layout.addLayout(title_vbox, stretch=1)
        header_actions=QHBoxLayout()

        # Виджет статуса S3 Yandex Cloud
        self.s3_badge = S3StatusBadge(self.s3_config.s3_bucket, self)
        self.s3_badge.clicked.connect(self.show_cloud_sync_dialog)
        self.s3_badge.quick_check_requested.connect(self.quick_check_updates)
        header_actions.addWidget(self.s3_badge)

        # Кнопка центра управления облаком
        self.btn_cloud = QPushButton("☁️ Облако и синхронизация")
        self.btn_cloud.setObjectName("btnCloud")
        self.btn_cloud.setToolTip("Центр управления облачной базой S3, версиями и самодиагностикой")
        self.btn_cloud.clicked.connect(self.show_cloud_sync_dialog)
        header_actions.addWidget(self.btn_cloud)

        # Кнопка справки и аудита
        self.btn_help = QPushButton("ℹ️ Справка и аудит")
        self.btn_help.setObjectName("btnInfo")
        self.btn_help.clicked.connect(self.show_algorithm_help)
        header_actions.addWidget(self.btn_help)
        header_actions.addStretch()
        header_layout.addLayout(header_actions)

        main_layout.addWidget(header_frame)

        # =====================================================================
        # 2. ПАНЕЛЬ НАСТРОЕК (SETTINGS CARD)
        # =====================================================================
        settings_frame = QFrame()
        settings_frame.setObjectName("settingsCard")
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(20, 16, 20, 16)
        settings_layout.setSpacing(14)

        # Строка 1: Выбор режима расчета
        mode_row = QHBoxLayout()
        mode_row.setSpacing(16)
        lbl_mode = QLabel("Режим расчета:")
        lbl_mode.setObjectName("fieldLabel")
        mode_row.addWidget(lbl_mode)

        self.rb_both = QRadioButton("Пакетный расчет (Дом + Город)")
        self.rb_both.setChecked(True)
        self.rb_dom = QRadioButton("Только ООО «Южный Дом»")
        self.rb_gorod = QRadioButton("Только ООО «Южный Город»")

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.rb_both)
        self.mode_group.addButton(self.rb_dom)
        self.mode_group.addButton(self.rb_gorod)

        mode_row.addWidget(self.rb_both)
        mode_row.addWidget(self.rb_dom)
        mode_row.addWidget(self.rb_gorod)
        mode_row.addStretch()
        settings_layout.addLayout(mode_row)

        # Строка 2: Выбор папки или файла
        path_row = QHBoxLayout()
        path_row.setSpacing(10)
        lbl_path = QLabel("Исходные данные:")
        lbl_path.setObjectName("fieldLabel")
        path_row.addWidget(lbl_path)

        self.edit_source = QLineEdit(self.default_dir)
        self.edit_source.setObjectName("pathInput")
        self.edit_source.textChanged.connect(self.on_source_path_changed)
        path_row.addWidget(self.edit_source, stretch=1)

        btn_browse_folder = QPushButton("📁 Выбрать папку")
        btn_browse_folder.setObjectName("btnSecondary")
        btn_browse_folder.clicked.connect(self.choose_folder)
        path_row.addWidget(btn_browse_folder)

        btn_browse_file = QPushButton("📄 Выбрать файл")
        btn_browse_file.setObjectName("btnSecondary")
        btn_browse_file.clicked.connect(self.choose_file)
        path_row.addWidget(btn_browse_file)

        settings_layout.addLayout(path_row)

        # Индикатор обнаружения ведомостей
        self.lbl_detect_info = QLabel("Поиск ведомостей в папке...")
        self.lbl_detect_info.setObjectName("detectLabel")
        settings_layout.addWidget(self.lbl_detect_info)

        # Строка 3: Период начисления (Месяц и Год) + Папка сохранения
        param_row = QHBoxLayout()
        param_row.setSpacing(20)

        month_vbox = QVBoxLayout()
        month_vbox.setSpacing(4)
        lbl_m = QLabel("Расчетный месяц:")
        lbl_m.setObjectName("smallLabel")
        self.cb_month = QComboBox()
        self.cb_month.addItems(MONTHS_RU)
        self.cb_month.setCurrentText("Август")
        self.cb_month.currentTextChanged.connect(self.update_template_label)
        month_vbox.addWidget(lbl_m)
        month_vbox.addWidget(self.cb_month)
        param_row.addLayout(month_vbox)

        year_vbox = QVBoxLayout()
        year_vbox.setSpacing(4)
        lbl_y = QLabel("Год:")
        lbl_y.setObjectName("smallLabel")
        self.cb_year = QComboBox()
        self.cb_year.addItems(["2025", "2026", "2027", "2028", "2029", "2030"])
        self.cb_year.setCurrentText("2026")
        self.cb_year.currentTextChanged.connect(self.update_template_label)
        year_vbox.addWidget(lbl_y)
        year_vbox.addWidget(self.cb_year)
        param_row.addLayout(year_vbox)

        out_vbox = QVBoxLayout()
        out_vbox.setSpacing(4)
        lbl_out = QLabel("Автосохранение в подпапку:")
        lbl_out.setObjectName("smallLabel")
        self.lbl_out_template = QLabel("📁 Папка: [Август 2026 ТНС]  •  Файлы: Дом_Август_2026.xlsx  и  Город_Август_2026.xlsx")
        self.lbl_out_template.setObjectName("templateLabel")
        self.lbl_out_template.setWordWrap(True)
        self.lbl_out_template.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
        out_vbox.addWidget(lbl_out)
        out_vbox.addWidget(self.lbl_out_template)
        param_row.addLayout(out_vbox)

        param_row.addStretch()

        # Кнопка запуска расчета
        self.btn_calculate = QPushButton("⚡ ВЫПОЛНИТЬ РАСЧЕТ")
        self.btn_calculate.setObjectName("btnPrimary")
        self.btn_calculate.setMinimumHeight(44)
        self.btn_calculate.setMinimumWidth(240)
        self.btn_calculate.clicked.connect(self.start_calculation)
        param_row.addWidget(self.btn_calculate)

        settings_layout.addLayout(param_row)
        main_layout.addWidget(settings_frame)

        # =====================================================================
        # 3. СТАТУС-БАР И ПРОГРЕСС
        # =====================================================================
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(6)

        progress_top = QHBoxLayout()
        self.lbl_status = QLabel("Готов к работе")
        self.lbl_status.setObjectName("statusLabel")
        self.lbl_status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        progress_top.addWidget(self.lbl_status)
        progress_layout.addLayout(progress_top)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        progress_layout.addWidget(self.progress_bar)

        main_layout.addLayout(progress_layout)

        # =====================================================================
        # 4. РЕЗУЛЬТАТЫ РАСЧЕТА (ПРЕВЬЮ ТАБЛИЦ)
        # =====================================================================
        self.tabs = QTabWidget()
        self.tabs.setObjectName("resultsTabs")

        # Вкладка Южный Дом
        self.tab_dom = QWidget()
        self.layout_tab_dom = QVBoxLayout(self.tab_dom)
        self.layout_tab_dom.setContentsMargins(12, 14, 12, 12)
        self.layout_tab_dom.setSpacing(12)
        self.init_dom_tab()
        self.tabs.addTab(self.tab_dom, "🏠 ООО «Южный Дом»")

        # Вкладка Южный Город
        self.tab_gorod = QWidget()
        self.layout_tab_gorod = QVBoxLayout(self.tab_gorod)
        self.layout_tab_gorod.setContentsMargins(12, 14, 12, 12)
        self.layout_tab_gorod.setSpacing(12)
        self.init_gorod_tab()
        self.tabs.addTab(self.tab_gorod, "🏢 ООО «Южный Город»")

        main_layout.addWidget(self.tabs, stretch=1)

        # =====================================================================
        # 5. НИЖНЯЯ ПАНЕЛЬ ДЕЙСТВИЙ (FOOTER ACTIONS)
        # =====================================================================
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(14)

        self.btn_open_excel = QPushButton("📊 Открыть рассчитанный файл в Excel")
        self.btn_open_excel.setObjectName("btnAction")
        self.btn_open_excel.setEnabled(False)
        self.btn_open_excel.clicked.connect(self.open_current_excel)
        bottom_row.addWidget(self.btn_open_excel)

        self.btn_open_folder = QPushButton("📂 Открыть папку с файлами ТНС")
        self.btn_open_folder.setObjectName("btnAction")
        self.btn_open_folder.clicked.connect(self.open_current_folder)
        bottom_row.addWidget(self.btn_open_folder)

        bottom_row.addStretch()

        self.lbl_balance_summary = QLabel("Баланс начислений: —")
        self.lbl_balance_summary.setObjectName("balanceSummary")
        self.lbl_balance_summary.setMinimumWidth(180)
        self.lbl_balance_summary.setWordWrap(True)
        self.lbl_balance_summary.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lbl_balance_summary.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bottom_row.addWidget(self.lbl_balance_summary)

        main_layout.addLayout(bottom_row)
        self.update_template_label()

    def update_template_label(self):
        m = self.cb_month.currentText()
        y = self.cb_year.currentText()
        self.lbl_out_template.setText(f"📁 Папка: [{m} {y} ТНС]  •  Файлы: Дом_{m}_{y}.xlsx  и  Город_{m}_{y}.xlsx")

    def show_algorithm_help(self):
        dlg = AlgorithmHelpDialog(self)
        dlg.exec()

    def init_dom_tab(self):
        # Метрики
        self.cards_dom_layout = QHBoxLayout()
        self.cards_dom_layout.setSpacing(12)
        self.card_dom_day = self.create_metric_card("Энергия День", "0.000 кВт*ч", "#F59E0B")
        self.card_dom_night = self.create_metric_card("Энергия Ночь", "0.000 кВт*ч", "#818CF8")
        self.card_dom_odn = self.create_metric_card("ОДН", "0.000 кВт*ч", "#34D399")
        self.card_dom_total = self.create_metric_card("ИТОГО НАЧИСЛЕНО", "0.000 кВт*ч", "#38BDF8")
        self.cards_dom_layout.addWidget(self.card_dom_day)
        self.cards_dom_layout.addWidget(self.card_dom_night)
        self.cards_dom_layout.addWidget(self.card_dom_odn)
        self.cards_dom_layout.addWidget(self.card_dom_total)
        self.layout_tab_dom.addLayout(self.cards_dom_layout)

        # Таблица домов
        self.tbl_dom = self.create_results_table()
        self.layout_tab_dom.addWidget(self.tbl_dom, stretch=1)

    def init_gorod_tab(self):
        # Метрики
        self.cards_gor_layout = QHBoxLayout()
        self.cards_gor_layout.setSpacing(12)
        self.card_gor_day = self.create_metric_card("Энергия День", "0.000 кВт*ч", "#F59E0B")
        self.card_gor_night = self.create_metric_card("Энергия Ночь", "0.000 кВт*ч", "#818CF8")
        self.card_gor_odn = self.create_metric_card("ОДН", "0.000 кВт*ч", "#34D399")
        self.card_gor_total = self.create_metric_card("ИТОГО НАЧИСЛЕНО", "0.000 кВт*ч", "#38BDF8")
        self.cards_gor_layout.addWidget(self.card_gor_day)
        self.cards_gor_layout.addWidget(self.card_gor_night)
        self.cards_gor_layout.addWidget(self.card_gor_odn)
        self.cards_gor_layout.addWidget(self.card_gor_total)
        self.layout_tab_gorod.addLayout(self.cards_gor_layout)

        # Таблица домов
        self.tbl_gorod = self.create_results_table()
        self.layout_tab_gorod.addWidget(self.tbl_gorod, stretch=1)

    def create_metric_card(self, title, initial_val, accent_color):
        card = QFrame()
        card.setObjectName("metricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setObjectName("cardTitle")
        v_lbl = QLabel(initial_val)
        v_lbl.setObjectName("cardValue")
        v_lbl.setStyleSheet(f"color: {accent_color}; font-size: 16px; font-weight: bold;")

        layout.addWidget(t_lbl)
        layout.addWidget(v_lbl)
        card.value_label = v_lbl
        return card

    def create_results_table(self):
        tbl = QTableWidget()
        tbl.setObjectName("dataTable")
        headers = [
            "№", "Адрес дома (Объект)",
            "Энергия День", "Энергия Ночь", "ОДН",
            "ИТОГО начислено", "Контроль (ст. AB)", "Отклонение", "Приборы (раб/рез)"
        ]
        tbl.setColumnCount(len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setAlternatingRowColors(True)
        tbl.setSelectionBehavior(QTableWidget.SelectRows)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)

        widths = [35, 230, 120, 120, 120, 135, 135, 110, 130]
        for idx, w in enumerate(widths):
            tbl.setColumnWidth(idx, w)

        return tbl

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с ведомостями ТНС Энерго", self.edit_source.text())
        if folder:
            self.edit_source.setText(folder)

    def choose_file(self):
        start_dir = self.edit_source.text() if os.path.isdir(self.edit_source.text()) else os.path.dirname(self.edit_source.text())
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл ведомости ТНС", start_dir, "Таблицы Excel (*.xlsx)")
        if file_path:
            self.edit_source.setText(file_path)

    def on_source_path_changed(self, text):
        self.auto_detect_in_folder(text)

    def auto_detect_in_folder(self, path):
        if not os.path.exists(path):
            self.lbl_detect_info.setText("❌ Указанный путь не существует")
            return

        if os.path.isfile(path):
            st_type, name, contract = detect_statement_type(path)
            if st_type == "dom":
                self.lbl_detect_info.setText(f"✅ Обнаружен файл: Южный Дом (договор {contract})")
                self.rb_dom.setChecked(True)
            elif st_type == "gorod":
                self.lbl_detect_info.setText(f"✅ Обнаружен файл: Южный Город (договор {contract})")
                self.rb_gorod.setChecked(True)
            else:
                self.lbl_detect_info.setText(f"📄 Выбран файл: {os.path.basename(path)}")
            return

        # Папка
        files = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith(".xlsx") and not f.startswith("~$")]
        dom_f = None
        gor_f = None
        for f in files:
            st_type, _, _ = detect_statement_type(f)
            if st_type == "dom" and not dom_f:
                dom_f = f
            elif st_type == "gorod" and not gor_f:
                gor_f = f

        info_parts = []
        if dom_f:
            info_parts.append(f"Южный Дом: {os.path.basename(dom_f)}")
        if gor_f:
            info_parts.append(f"Южный Город: {os.path.basename(gor_f)}")

        if dom_f and gor_f:
            self.lbl_detect_info.setText(f"✅ Найдено 2 ведомости:  {os.path.basename(dom_f)}  и  {os.path.basename(gor_f)}")
            self.rb_both.setChecked(True)
        elif dom_f:
            self.lbl_detect_info.setText(f"✅ Найдена ведомость Южный Дом: {os.path.basename(dom_f)}")
            self.rb_dom.setChecked(True)
        elif gor_f:
            self.lbl_detect_info.setText(f"✅ Найдена ведомость Южный Город: {os.path.basename(gor_f)}")
            self.rb_gorod.setChecked(True)
        else:
            self.lbl_detect_info.setText(f"ℹ️ В папке найдено {len(files)} файлов .xlsx. Ведомости ТНС определятся при расчете.")

    def start_calculation(self):
        source_path = self.edit_source.text().strip()
        if not os.path.exists(source_path):
            QMessageBox.warning(self, "Ошибка", "Указанная папка или файл не существует!")
            return

        if self.rb_both.isChecked():
            mode = "both"
        elif self.rb_dom.isChecked():
            mode = "dom"
        else:
            mode = "gorod"

        month = self.cb_month.currentText()
        year = self.cb_year.currentText()
        output_dir = source_path if os.path.isdir(source_path) else os.path.dirname(source_path)

        if getattr(self,"worker",None) and self.worker.isRunning():return
        self.btn_calculate.setEnabled(False)
        self.progress_bar.setValue(5)
        self.lbl_status.setText("Запуск расчета...")

        self.worker = CalculationWorker(mode, source_path, month, year, output_dir)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_progress(self, val, msg):
        self.progress_bar.setValue(val)
        self.lbl_status.setText(msg)

    def on_finished(self, results):
        if getattr(self,"_closing_pending",False):return
        self.btn_calculate.setEnabled(True)
        self.progress_bar.setValue(100)
        self.current_results = results

        total_houses_all = 0
        total_kwh_all = 0.0
        warnings_list = []
        self.current_target_dir = None
        subfolder_name = ""

        for k, r in results.items():
            if "target_dir" in r:
                self.current_target_dir = r["target_dir"]
                subfolder_name = r.get("subfolder_name", "")
            if r.get("warning"):
                warnings_list.append(r["warning"])

        if "dom" in results:
            r = results["dom"]
            total_houses_all += r["houses_count"]
            total_kwh_all += r["total_all"]
            self.populate_table(self.tbl_dom, r["preview_rows"])
            self.card_dom_day.value_label.setText(f"{r['total_day']:,.3f} кВт*ч")
            self.card_dom_night.value_label.setText(f"{r['total_night']:,.3f} кВт*ч")
            self.card_dom_odn.value_label.setText(f"{r.get('total_odn', r.get('total_simple', 0)):,.3f} кВт*ч")
            self.card_dom_total.value_label.setText(f"{r['total_all']:,.3f} кВт*ч")
            self.tabs.setCurrentIndex(0)

        if "gorod" in results:
            r = results["gorod"]
            total_houses_all += r["houses_count"]
            total_kwh_all += r["total_all"]
            self.populate_table(self.tbl_gorod, r["preview_rows"])
            self.card_gor_day.value_label.setText(f"{r['total_day']:,.3f} кВт*ч")
            self.card_gor_night.value_label.setText(f"{r['total_night']:,.3f} кВт*ч")
            self.card_gor_odn.value_label.setText(f"{r.get('total_odn', r.get('total_simple', 0)):,.3f} кВт*ч")
            self.card_gor_total.value_label.setText(f"{r['total_all']:,.3f} кВт*ч")
            if "dom" not in results:
                self.tabs.setCurrentIndex(1)

        self.btn_open_excel.setEnabled(True)
        self.lbl_status.setText(f"✅ Расчет завершен! Сохранено в: {subfolder_name} (домов: {total_houses_all})")
        balance_details = "; ".join(f"{'Дом' if k=='dom' else 'Город'}: {r.get('balance_diff',0):+.3f} кВт*ч" for k,r in results.items())
        balance_ok = all(bool(r.get('balance_ok',False)) for r in results.values())
        self.lbl_balance_summary.setText(f"{'✅' if balance_ok else '⚠️'} Баланс: {total_kwh_all:,.3f} кВт*ч | {balance_details}")

        # Автоматическая фиксация в локальной базе данных SQLite
        month = self.cb_month.currentText()
        year = self.cb_year.currentText()
        for k, r in results.items():
            org_name = "ООО «Южный Дом»" if k == "dom" else "ООО «Южный Город»"
            contract_num = "23110603789" if k == "dom" else "23110604327"
            target_fname = os.path.basename(r.get("target_path", ""))

            # Регистрация / обновление домов
            for h_row in r.get("preview_rows", []):
                act_m = int(h_row.get("meters_active",0))
                res_m = int(h_row.get("meters_res",0))
                self.db_manager.register_or_update_house(
                    contract_num, str(h_row.get("name", "")),
                    meters_active=act_m, meters_res=res_m
                )

            # Регистрация расчета
            self.db_manager.record_calculation(
                month=month, year=year, org_type=k, org_name=org_name,
                contract_number=contract_num, houses_count=r.get("houses_count", 0),
                total_day=r.get("total_day", 0.0), total_night=r.get("total_night", 0.0),
                total_odn=r.get("total_odn", r.get("total_simple", 0.0)),
                total_all=r.get("total_all", 0.0), balance_diff=r.get("balance_diff", 0.0),
                filename=target_fname
            )

        self.toast_manager.show_toast(
            f"Расчет {subfolder_name} зафиксирован в локальной базе SQLite!",
            toast_type="success"
        )

        if warnings_list:
            QMessageBox.warning(self, "Предупреждение сохранения Excel", "\n\n".join(warnings_list))

        if not os.environ.get("TEST_MODE"):
            saved_files = [os.path.basename(r["target_path"]) for r in results.values()]
            QMessageBox.information(
                self, "Расчет завершен",
                f"Расчет успешно выполнен!\n\n"
                f"📁 Создана папка:\n{self.current_target_dir}\n\n"
                f"📄 Файлы расчетов:\n• " + "\n• ".join(saved_files) + f"\n\n"
                f"Баланс: {total_kwh_all:,.3f} кВт*ч. {balance_details}. "
                + ("Проверка пройдена." if balance_ok else "Есть расхождение — проверьте исходную ведомость.")
            )

    def on_error(self, err_msg):
        if getattr(self,"_closing_pending",False):return
        self.btn_calculate.setEnabled(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("❌ Ошибка при расчете")
        QMessageBox.critical(self, "Ошибка расчета", f"Произошла ошибка при обработке ведомости:\n\n{err_msg}")

    def populate_table(self, tbl, rows):
        tbl.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            tbl.setItem(r_idx, 0, QTableWidgetItem(str(row["num"])))
            tbl.setItem(r_idx, 1, QTableWidgetItem(str(row["name"])))
            tbl.setItem(r_idx, 2, QTableWidgetItem(f"{row['day']:,.3f}"))
            tbl.setItem(r_idx, 3, QTableWidgetItem(f"{row['night']:,.3f}"))
            
            odn_val = row.get('odn', row.get('simple', 0.0))
            tbl.setItem(r_idx, 4, QTableWidgetItem(f"{odn_val:,.3f}"))
            
            tot_item = QTableWidgetItem(f"{row['total']:,.3f}")
            tot_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            tbl.setItem(r_idx, 5, tot_item)

            tbl.setItem(r_idx, 6, QTableWidgetItem(f"{row['control']:,.3f}"))
            
            # Столбец Отклонение с условным форматированием
            diff_val = row['diff']
            diff_item = QTableWidgetItem(f"{diff_val:,.3f}")
            diff_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            if abs(diff_val) < 0.001:
                diff_item.setForeground(QColor("#10B981"))
            else:
                diff_item.setForeground(QColor("#EF4444"))
                diff_item.setBackground(QColor("#7F1D1D"))
            tbl.setItem(r_idx, 7, diff_item)

            tbl.setItem(r_idx, 8, QTableWidgetItem(str(row["meters"])))

            # Выравнивание чисел вправо
            for c in [0, 2, 3, 4, 5, 6, 7]:
                it = tbl.item(r_idx, c)
                if it:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tbl.item(r_idx, 1).setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            tbl.item(r_idx, 8).setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)

    def open_current_excel(self):
        cur_idx = self.tabs.currentIndex()
        key = "dom" if cur_idx == 0 else "gorod"
        if key not in self.current_results and len(self.current_results) > 0:
            key = list(self.current_results.keys())[0]

        if key in self.current_results:
            fpath = self.current_results[key]["target_path"]
            if os.path.exists(fpath):
                os.startfile(fpath)
            else:
                QMessageBox.warning(self, "Внимание", f"Файл не найден:\n{fpath}")

    def open_current_folder(self):
        folder_to_open = getattr(self, 'current_target_dir', None)
        if not folder_to_open or not os.path.exists(folder_to_open):
            source = self.edit_source.text().strip()
            folder_to_open = source if os.path.isdir(source) else os.path.dirname(source)
        
        if os.path.exists(folder_to_open):
            os.startfile(folder_to_open)
        else:
            QMessageBox.warning(self, "Внимание", "Папка не найдена!")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'toast_manager'):
            self.toast_manager.reposition_toasts()

    def show_cloud_sync_dialog(self):
        if getattr(self,"worker",None) and self.worker.isRunning():
            self.toast_manager.show_toast("Дождитесь завершения расчёта перед синхронизацией.","info")
            return
        dlg = CloudSyncDialog(self.s3_config, self.db_manager, self)
        dlg.exec()
        self.quick_check_updates()

    def quick_check_updates(self):
        if getattr(self,"quick_worker",None) and self.quick_worker.isRunning():return
        self.s3_badge.set_state("checking", "Опрос S3 Yandex Cloud...")
        self.quick_worker = CheckUpdatesWorker(self.s3_config, DEFAULT_APP_VERSION)
        self.quick_worker.finished.connect(self.on_quick_check_finished)
        self.quick_worker.error.connect(self.on_quick_check_error)
        self.quick_worker.start()

    def on_quick_check_finished(self, res: dict):
        if getattr(self,"_closing_pending",False):return
        if res.get("has_app_update"):
            self.s3_badge.set_state("update_available", f"Доступна новая версия v{res.get('cloud_app_version')}!")
            self.toast_manager.show_toast(f"Доступна новая версия программы: v{res.get('cloud_app_version')}!", "warning")
            dlg = UpdateModalDialog(DEFAULT_APP_VERSION, res, self)
            dlg.exec()
        elif res.get("has_db_update"):
            self.s3_badge.set_state("update_available", "Облачная база отличается от локальной.")
            self.toast_manager.show_toast("Локальная и облачная базы различаются. Проверьте нужную ревизию перед загрузкой.", "info")
        else:
            self.s3_badge.set_state("synced", "Программа и база данных актуальны")
            self.toast_manager.show_toast("Облачное хранилище S3: версия и базы актуальны!", "success")

    def on_quick_check_error(self, err: str):
        if getattr(self,"_closing_pending",False):return
        self.s3_badge.set_state("offline", f"Ошибка проверки: {err}")
        self.toast_manager.show_toast(f"Не удалось связаться с облаком S3: {err}", "error")

    def silent_check_updates(self):
        if getattr(self,"silent_worker",None) and self.silent_worker.isRunning():return
        self.silent_worker = CheckUpdatesWorker(self.s3_config, DEFAULT_APP_VERSION)
        self.silent_worker.finished.connect(self.on_silent_check_finished)
        self.silent_worker.error.connect(lambda error:self.s3_badge.set_state("offline",error))
        self.silent_worker.start()

    def on_silent_check_finished(self, res: dict):
        if getattr(self,"_closing_pending",False):return
        if res.get("has_app_update"):
            self.s3_badge.set_state("update_available", f"Доступна версия v{res.get('cloud_app_version')}")
            self.toast_manager.show_toast(
                f"Доступно обновление программы v{res.get('cloud_app_version')}!\nНажмите «Облако» для установки.",
                "info", duration_ms=6000
            )
        elif res.get("has_db_update"):
            self.s3_badge.set_state("update_available", "Облачная база отличается от локальной")
            self.toast_manager.show_toast("Локальная и облачная базы различаются. Загрузка выполняется вручную с резервной копией.", "info")
        else:
            self.s3_badge.set_state("synced", "Синхронизировано с Yandex Cloud S3")

    def apply_theme(self):
        # Luxury Cobalt Dark Theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0F172A;
            }
            QWidget {
                color: #F8FAFC;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
                font-size: 13px;
            }
            #headerFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            #appTitle {
                color: #F8FAFC;
                font-size: 17px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }
            #appSubtitle {
                color: #94A3B8;
                font-size: 12px;
            }
            #btnInfo {
                background-color: rgba(56, 189, 248, 0.12);
                color: #38BDF8;
                border: 1px solid #0284C7;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            #btnInfo:hover {
                background-color: rgba(56, 189, 248, 0.25);
                color: #BAE6FD;
            }
            #btnCloud {
                background-color: rgba(37, 99, 235, 0.18);
                color: #60A5FA;
                border: 1px solid #2563EB;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            #btnCloud:hover {
                background-color: rgba(37, 99, 235, 0.35);
                color: #93C5FD;
            }
            #settingsCard {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            #fieldLabel {
                color: #CBD5E1;
                font-weight: 600;
                font-size: 13px;
            }
            #smallLabel {
                color: #94A3B8;
                font-size: 11px;
                font-weight: 600;
            }
            #templateLabel {
                color: #38BDF8;
                font-size: 12px;
                font-weight: 600;
            }
            #detectLabel {
                color: #10B981;
                font-size: 12px;
                font-weight: 500;
                padding-left: 2px;
            }
            QLineEdit#pathInput {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 12px;
                color: #F8FAFC;
                font-size: 13px;
            }
            QLineEdit#pathInput:focus {
                border: 1px solid #38BDF8;
            }
            QComboBox {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 12px;
                color: #F8FAFC;
                min-width: 110px;
            }
            QComboBox:hover {
                border-color: #475569;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #1E293B;
                border: 1px solid #334155;
                selection-background-color: #2563EB;
                color: #F8FAFC;
                padding: 4px;
            }
            QRadioButton {
                color: #E2E8F0;
                font-weight: 500;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QPushButton#btnPrimary {
                background-color: #2563EB;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
            }
            QPushButton#btnPrimary:hover {
                background-color: #1D4ED8;
            }
            QPushButton#btnPrimary:pressed {
                background-color: #1E40AF;
            }
            QPushButton#btnPrimary:disabled {
                background-color: #475569;
                color: #94A3B8;
            }
            QPushButton#btnSecondary {
                background-color: #334155;
                color: #F8FAFC;
                border: 1px solid #475569;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 500;
            }
            QPushButton#btnSecondary:hover {
                background-color: #475569;
            }
            QPushButton#btnAction {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: 600;
            }
            QPushButton#btnAction:hover {
                background-color: #334155;
                border-color: #475569;
            }
            QPushButton#btnAction:disabled {
                color: #64748B;
                border-color: #1E293B;
            }
            QProgressBar#progressBar {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 4px;
            }
            QProgressBar#progressBar::chunk {
                background-color: #38BDF8;
                border-radius: 4px;
            }
            #statusLabel {
                color: #94A3B8;
                font-size: 12px;
                font-weight: 500;
            }
            #balanceSummary {
                color: #10B981;
                font-size: 13px;
                font-weight: bold;
            }
            #resultsTabs::pane, #helpTabs::pane {
                border: 1px solid #334155;
                border-radius: 12px;
                background-color: #1E293B;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #0F172A;
                color: #94A3B8;
                padding: 10px 20px;
                border: 1px solid #334155;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #1E293B;
                color: #38BDF8;
                border: 1px solid #334155;
                border-bottom: 2px solid #1E293B;
            }
            #metricCard {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            #cardTitle {
                color: #94A3B8;
                font-size: 11px;
                font-weight: bold;
                text-transform: uppercase;
            }
            #dataTable {
                background-color: #0F172A;
                alternate-background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                gridline-color: #334155;
                color: #F8FAFC;
                selection-background-color: #2563EB;
                selection-color: #FFFFFF;
            }
            #dataTable::item {
                color: #F8FAFC;
                padding: 4px 8px;
            }
            #dataTable::item:alternate {
                background-color: #1E293B;
                color: #F8FAFC;
            }
            #dataTable QHeaderView::section {
                background-color: #1E293B;
                color: #94A3B8;
                font-size: 11px;
                font-weight: bold;
                padding: 8px 6px;
                border: 1px solid #334155;
            }
            #dataTable::item:selected {
                background-color: #2563EB;
                color: #FFFFFF;
            }
        """)

    def closeEvent(self,event):
        active=[]
        for attr in ("worker","quick_worker","silent_worker"):
            worker=getattr(self,attr,None)
            if worker is not None and worker.isRunning():
                worker.requestInterruption()
                active.append(worker)
        if active:
            self._closing_pending=True
            self.lbl_status.setText("Завершение фоновых задач...")
            event.ignore()
            QTimer.singleShot(200,self.close)
            return
        event.accept()


def main():
    if "--self-test" in sys.argv:
        from app_self_test import run
        index=sys.argv.index("--self-test")
        report=sys.argv[index+1] if index+1<len(sys.argv) else None
        sys.exit(run(report))
    app = QApplication(sys.argv)
    window = TNSEnergyStudioWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
