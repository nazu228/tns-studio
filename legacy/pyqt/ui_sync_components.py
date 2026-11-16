"""
Графические компоненты синхронизации и автообновления для ТНС Энерго Студии:
- ToastNotification & ToastManager: всплывающие анимированные карточки статуса.
- S3StatusBadge: компактный индикатор в футере/шапке со статусом и кнопкой быстрой проверки.
- UpdateModalDialog: современное модальное окно релиза с описанием и прогрессом загрузки.
- CloudSyncDialog: центр управления облачной синхронизацией, настройками ключей и самодиагностикой.
- DatabaseConflictDialog: окно предупреждения о конфликтах версий баз данных.
- DatabaseViewerDialog: встроенный просмотрщик справочников и архива начислений SQLite.
"""

import os
import sys
import datetime
import html
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QProgressBar, QTextBrowser, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QScrollArea, QSizePolicy, QMessageBox, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal, Slot, QObject
from PySide6.QtGui import QFont, QColor, QCursor

from sync_manager import (
    S3Config, DatabaseManager, DiagnosticService, WindowsUpdateDeployer,
    CheckUpdatesWorker, DownloadUpdateWorker, SyncPullWorker, SyncPushWorker,
    DiagnosticWorker, DEFAULT_APP_VERSION, DEFAULT_APP_NAME
)


# ==============================================================================
# 1. TOAST NOTIFICATIONS (Всплывающие уведомления)
# ==============================================================================
class ToastNotification(QFrame):
    """Одиночное анимированное всплывающее уведомление."""
    closed = Signal()

    def __init__(self, message: str, toast_type: str = "info", duration_ms: int = 4500, parent=None):
        super().__init__(parent)
        self.toast_type = toast_type
        self.duration_ms = duration_ms
        self.init_ui(message)

    def init_ui(self, message: str):
        self.setFixedWidth(360)
        self.setFrameShape(QFrame.StyledPanel)

        # Цвета по типам (Emerald, Sky, Amber, Rose)
        type_styles = {
            "success": {
                "border": "#10B981",
                "bg": "#064E3B",
                "icon": "✅",
                "title": "УСПЕШНО"
            },
            "info": {
                "border": "#38BDF8",
                "bg": "#0C4A6E",
                "icon": "ℹ️",
                "title": "ИНФОРМАЦИЯ"
            },
            "warning": {
                "border": "#F59E0B",
                "bg": "#78350F",
                "icon": "⚠️",
                "title": "ВНИМАНИЕ"
            },
            "error": {
                "border": "#EF4444",
                "bg": "#7F1D1D",
                "icon": "❌",
                "title": "ОШИБКА"
            }
        }
        cfg = type_styles.get(self.toast_type, type_styles["info"])

        self.setStyleSheet(f"""
            ToastNotification {{
                background-color: #1E293B;
                border-left: 5px solid {cfg['border']};
                border-top: 1px solid #334155;
                border-right: 1px solid #334155;
                border-bottom: 1px solid #334155;
                border-radius: 8px;
            }}
            QLabel {{
                color: #F8FAFC;
                font-family: 'Segoe UI';
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        icon_lbl = QLabel(cfg["icon"])
        icon_lbl.setFont(QFont("Segoe UI Emoji", 15))
        layout.addWidget(icon_lbl)

        text_vbox = QVBoxLayout()
        text_vbox.setSpacing(2)

        title_lbl = QLabel(cfg["title"])
        title_lbl.setStyleSheet(f"color: {cfg['border']}; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        text_vbox.addWidget(title_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #E2E8F0; font-size: 12px; font-weight: 500;")
        text_vbox.addWidget(msg_lbl)

        layout.addLayout(text_vbox, stretch=1)

        btn_close = QPushButton("×")
        btn_close.setFixedSize(20, 20)
        btn_close.setCursor(QCursor(Qt.PointingHandCursor))
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94A3B8;
                font-size: 16px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                color: #FFFFFF;
            }
        """)
        btn_close.clicked.connect(self.fade_out)
        layout.addWidget(btn_close)

        # Анимация прозрачности
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.anim_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_in.setDuration(220)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.start()

        # Автозакрытие через таймер
        if self.duration_ms > 0:
            QTimer.singleShot(self.duration_ms, self.fade_out)

    def fade_out(self):
        self.anim_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_out.setDuration(220)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(self.on_fade_finished)
        self.anim_out.start()

    def on_fade_finished(self):
        self.closed.emit()
        self.deleteLater()


class ToastManager(QObject):
    """Менеджер плавающих уведомлений в правом верхнем углу окна."""

    def __init__(self, parent_widget: QWidget):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self.active_toasts = []

    def show_toast(self, message: str, toast_type: str = "info", duration_ms: int = 4500):
        toast = ToastNotification(message, toast_type=toast_type, duration_ms=duration_ms, parent=self.parent_widget)
        toast.closed.connect(lambda: self.on_toast_closed(toast))
        self.active_toasts.append(toast)
        toast.show()
        self.reposition_toasts()

    def on_toast_closed(self, toast):
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
        self.reposition_toasts()

    def reposition_toasts(self):
        margin_right = 24
        margin_top = 24
        spacing = 10
        cur_y = margin_top

        for toast in self.active_toasts:
            toast_w = toast.width()
            x = self.parent_widget.width() - toast_w - margin_right
            toast.move(x, cur_y)
            cur_y += toast.height() + spacing


# ==============================================================================
# 2. STATUS BADGE (Виджет статуса S3 для футера / шапки)
# ==============================================================================
class S3StatusBadge(QFrame):
    """Компактный индикатор статуса облака S3 с кнопкой быстрой проверки."""
    clicked = Signal()
    quick_check_requested = Signal()

    def __init__(self, bucket_name: str = "ajeftdaam8hhmrujr94k", parent=None):
        super().__init__(parent)
        self.bucket_name = bucket_name
        self.state = "offline"  # 'synced', 'update_available', 'offline', 'checking'
        self.init_ui()

    def init_ui(self):
        self.setObjectName("s3StatusBadge")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 8, 4)
        layout.setSpacing(8)

        # Точка статуса
        self.dot = QLabel("●")
        self.dot.setObjectName("statusDot")
        layout.addWidget(self.dot)

        # Текст
        self.lbl_text = QLabel(f"☁️ S3: {self.bucket_name}")
        self.lbl_text.setObjectName("badgeText")
        layout.addWidget(self.lbl_text)

        # Кнопка быстрой проверки
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setObjectName("btnQuickCheck")
        self.btn_refresh.setToolTip("Быстрая проверка обновлений и связи с облаком")
        self.btn_refresh.setFixedSize(22, 22)
        self.btn_refresh.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_refresh.clicked.connect(self.on_refresh_clicked)
        layout.addWidget(self.btn_refresh)

        self.set_state("offline", "Связь не проверялась")
        self.apply_style()

    def set_state(self, state: str, tooltip: str = ""):
        self.state = state
        if state == "synced":
            self.dot.setStyleSheet("color: #10B981; font-size: 11px;")
            self.lbl_text.setText(f"☁️ S3: Синхронизировано")
        elif state == "update_available":
            self.dot.setStyleSheet("color: #F59E0B; font-size: 11px;")
            self.lbl_text.setText(f"☁️ S3: Есть различия")
        elif state == "checking":
            self.dot.setStyleSheet("color: #38BDF8; font-size: 11px;")
            self.lbl_text.setText(f"☁️ S3: Проверка...")
        else:
            self.dot.setStyleSheet("color: #94A3B8; font-size: 11px;")
            self.lbl_text.setText(f"☁️ S3: {self.bucket_name}")

        if tooltip:
            self.setToolTip(tooltip)

    def on_refresh_clicked(self):
        self.set_state("checking", "Выполняется опрос облачного хранилища...")
        self.quick_check_requested.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def apply_style(self):
        self.setStyleSheet("""
            #s3StatusBadge {
                background-color: rgba(30, 41, 59, 0.7);
                border: 1px solid #334155;
                border-radius: 16px;
            }
            #s3StatusBadge:hover {
                background-color: rgba(51, 65, 85, 0.9);
                border-color: #38BDF8;
            }
            #badgeText {
                color: #CBD5E1;
                font-size: 12px;
                font-weight: 600;
            }
            #btnQuickCheck {
                background: transparent;
                border: none;
                color: #38BDF8;
                font-size: 12px;
                border-radius: 11px;
            }
            #btnQuickCheck:hover {
                background-color: rgba(56, 189, 248, 0.2);
            }
        """)


# ==============================================================================
# 3. UPDATE MODAL DIALOG (Модальное окно обновления ПО)
# ==============================================================================
class UpdateModalDialog(QDialog):
    """Модальное окно информирования о новом релизе и загрузки."""

    def __init__(self, current_ver: str, update_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.current_ver = current_ver
        self.update_info = update_info
        self.download_worker: Optional[DownloadUpdateWorker] = None
        self.verified_package_path: Optional[str] = None

        self.setWindowTitle("Доступно обновление ТНС Энерго Студии")
        self.resize(580, 520)
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
                font-family: 'Segoe UI';
            }
            #modalHeader {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 16px;
            }
            #notesView {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #CBD5E1;
                font-size: 13px;
                padding: 12px;
            }
            #btnInstall {
                background-color: #2563EB;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
            }
            #btnInstall:hover {
                background-color: #1D4ED8;
            }
            #btnCancel {
                background-color: #334155;
                color: #CBD5E1;
                font-size: 13px;
                font-weight: 500;
                border: 1px solid #475569;
                border-radius: 8px;
                padding: 10px 18px;
            }
            #btnCancel:hover {
                background-color: #475569;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Шапка релиза
        header_frame = QFrame()
        header_frame.setObjectName("modalHeader")
        h_layout = QVBoxLayout(header_frame)
        h_layout.setSpacing(6)

        cloud_ver = self.update_info.get("cloud_app_version", "2.3.0")
        rel_date = self.update_info.get("release_date", datetime.date.today().isoformat())

        title_lbl = QLabel(f"🚀 Доступна новая версия: v{cloud_ver}")
        title_lbl.setStyleSheet("color: #38BDF8; font-size: 17px; font-weight: bold;")
        h_layout.addWidget(title_lbl)

        ver_diff = QLabel(f"Текущая версия: v{self.current_ver}  →  Новая версия: v{cloud_ver}  •  Дата: {rel_date}")
        ver_diff.setStyleSheet("color: #94A3B8; font-size: 12px;")
        h_layout.addWidget(ver_diff)

        layout.addWidget(header_frame)

        # Блок Release Notes
        notes_lbl = QLabel("Что нового в этой версии:")
        notes_lbl.setStyleSheet("color: #CBD5E1; font-weight: 600; font-size: 13px;")
        layout.addWidget(notes_lbl)

        self.notes_browser = QTextBrowser()
        self.notes_browser.setObjectName("notesView")
        notes_md = self.update_info.get("release_notes", "### Обновление ТНС Энерго\n- Улучшена стабильность и алгоритмы расчета.")
        # Преобразуем простой Markdown в HTML
        html_notes = self._format_markdown_notes(notes_md)
        self.notes_browser.setHtml(html_notes)
        layout.addWidget(self.notes_browser, stretch=1)

        # Блок прогресса скачивания (скрыт по умолчанию)
        self.progress_frame = QFrame()
        p_layout = QVBoxLayout(self.progress_frame)
        p_layout.setContentsMargins(0, 4, 0, 4)
        p_layout.setSpacing(6)

        self.lbl_stage = QLabel("Подготовка к скачиванию...")
        self.lbl_stage.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 500;")
        p_layout.addWidget(self.lbl_stage)

        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(10)
        self.pbar.setValue(0)
        self.pbar.setTextVisible(False)
        self.pbar.setStyleSheet("""
            QProgressBar {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #38BDF8;
                border-radius: 4px;
            }
        """)
        p_layout.addWidget(self.pbar)

        self.progress_frame.setVisible(False)
        layout.addWidget(self.progress_frame)

        # Кнопки действий
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_cancel = QPushButton("Отложить")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        btn_layout.addStretch()

        self.btn_install = QPushButton("⚡ Скачать и установить")
        self.btn_install.setObjectName("btnInstall")
        self.btn_install.clicked.connect(self.start_download)
        btn_layout.addWidget(self.btn_install)

        layout.addLayout(btn_layout)

    def done(self,result):
        worker=getattr(self,'download_worker',None)
        if worker and worker.isRunning():
            self.lbl_stage.setText('Дождитесь завершения загрузки и проверки SHA-256.')
            return
        super().done(result)

    def closeEvent(self,event):
        worker=getattr(self,'download_worker',None)
        if worker and worker.isRunning():event.ignore()
        else:event.accept()

    def _format_markdown_notes(self, md_text: str) -> str:
        content = html.escape(str(md_text)).replace("\n", "<br>")
        return f"<div style='font-family: Segoe UI; line-height: 1.5;'>{content}</div>"

    def start_download(self):
        if self.verified_package_path:
            self.deploy_and_restart()
            return
        pkg = self.update_info.get("package_info", {})
        url = pkg.get("url")
        sha256 = pkg.get("sha256", "")
        filename = pkg.get("filename", f"tns_studio_v{self.update_info.get('cloud_app_version', 'update')}.zip")

        if not url:
            QMessageBox.warning(self, "Ошибка", "Ссылка на файл дистрибутива в манифесте отсутствует.")
            return

        self.btn_install.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress_frame.setVisible(True)

        self.download_worker = DownloadUpdateWorker(url, sha256, filename)
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.error.connect(self.on_download_error)
        self.download_worker.start()

    def on_download_progress(self, percent: int, bytes_down: int, speed: float, stage: str):
        self.pbar.setValue(percent)
        self.lbl_stage.setText(stage)

    def on_download_finished(self, verified_filepath: str):
        self.verified_package_path = verified_filepath
        self.lbl_stage.setText("✅ Целостность подтверждена! Запуск обновления...")
        self.pbar.setValue(100)

        msg = QMessageBox.question(
            self,
            "Готово к развертыванию",
            "Дистрибутив обновления успешно загружен и проверен по SHA-256.\n\n"
            "Сейчас откроется отдельное окно автономного установщика и программа будет перезапущена.\n\n"
            "Продолжить обновление сейчас?",
            QMessageBox.Yes | QMessageBox.No
        )
        if msg == QMessageBox.Yes:
            self.deploy_and_restart()
        else:
            self.btn_cancel.setEnabled(True)
            self.btn_install.setEnabled(True)
            self.btn_install.setText("🚀 Применить сейчас")

    def deploy_and_restart(self):
        if not self.verified_package_path:
            return
        from cloud_sync import sha256,validate_hash
        expected=validate_hash((self.update_info.get('package_info') or {}).get('sha256'))
        if sha256(self.verified_package_path)!=expected:
            QMessageBox.critical(self,"Обновление отменено","Архив изменился после загрузки. Скачайте его повторно.")
            return
        self.lbl_stage.setText("🚀 Запуск автономного установщика обновления...")
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        ok, err = WindowsUpdateDeployer.deploy_zip_update(self.verified_package_path)
        if not ok:
            QMessageBox.critical(self, "Ошибка обновления", f"Сбой развертывания: {err}")
            return
        
        # Корректно закрываем приложение Qt и немедленно завершаем процесс на уровне ядра ОС
        QApplication.closeAllWindows()

    def on_download_error(self, err_msg: str):
        self.btn_install.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.lbl_stage.setText(f"❌ Ошибка: {err_msg}")
        QMessageBox.critical(self, "Сбой скачивания", err_msg)


# ==============================================================================
# 4. DATABASE VIEWER DIALOG (Встроенный просмотрщик SQLite)
# ==============================================================================
class DatabaseViewerDialog(QDialog):
    """Диалог просмотра таблиц SQLite (Дома, История начислений, Тарифы)."""

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("База данных и справочники ТНС Энерго (SQLite)")
        self.resize(920, 620)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
                font-family: 'Segoe UI';
            }
            QTabWidget::pane {
                border: 1px solid #334155;
                border-radius: 8px;
                background-color: #1E293B;
            }
            QTabBar::tab {
                background-color: #0F172A;
                color: #94A3B8;
                padding: 8px 16px;
                border: 1px solid #334155;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #1E293B;
                color: #38BDF8;
                border-bottom: 2px solid #1E293B;
            }
            QTableWidget {
                background-color: #0F172A;
                alternate-background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #F8FAFC;
                gridline-color: #334155;
            }
            QHeaderView::section {
                background-color: #1E293B;
                color: #94A3B8;
                font-size: 11px;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #334155;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Краткая статистика
        stats = self.db_manager.get_summary()
        stats_lbl = QLabel(
            f"📁 База данных: {os.path.basename(self.db_manager.db_path)}  •  "
            f"Размер: {stats.get('file_size', 0) / 1024:.1f} КБ  •  "
            f"SHA-256: {stats.get('sha256', '')[:16]}..."
        )
        stats_lbl.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 600;")
        layout.addWidget(stats_lbl)

        tabs = QTabWidget()

        # Вкладка 1: Реестр домов
        self.tbl_houses = QTableWidget()
        self.load_houses_table()
        tabs.addTab(self.tbl_houses, "🏠 Реестр домов (МКД)")

        # Вкладка 2: История расчетов
        self.tbl_history = QTableWidget()
        self.load_history_table()
        tabs.addTab(self.tbl_history, "📊 Журнал расчетов")

        # Вкладка 3: Тарифы
        self.tbl_tariffs = QTableWidget()
        self.load_tariffs_table()
        tabs.addTab(self.tbl_tariffs, "⚡ Тарифы и зоны")

        layout.addWidget(tabs, stretch=1)

        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_close = QPushButton("Закрыть")
        btn_close.setStyleSheet("""
            background-color: #334155;
            color: #FFFFFF;
            border-radius: 6px;
            padding: 8px 18px;
            font-weight: 600;
        """)
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)
        layout.addLayout(bottom)

    def load_houses_table(self):
        headers = ["ID", "Договор ТНС", "Адрес МКД", "Рабочих приборов", "Резервных (АВР)", "Обновлено"]
        self.tbl_houses.setColumnCount(len(headers))
        self.tbl_houses.setHorizontalHeaderLabels(headers)
        self.tbl_houses.horizontalHeader().setStretchLastSection(True)
        self.tbl_houses.setAlternatingRowColors(True)
        self.tbl_houses.setEditTriggers(QTableWidget.NoEditTriggers)

        with self.db_manager.get_connection() as conn:
            rows = conn.execute("SELECT id, org_contract, address, meters_count_active, meters_count_reserve, updated_at FROM houses ORDER BY id;").fetchall()
            self.tbl_houses.setRowCount(len(rows))
            for r_idx, r in enumerate(rows):
                for c_idx in range(len(headers)):
                    self.tbl_houses.setItem(r_idx, c_idx, QTableWidgetItem(str(r[c_idx] or "")))

    def load_history_table(self):
        headers = ["ID", "Период", "Организация", "Договор", "Домов", "День (кВт*ч)", "Ночь (кВт*ч)", "ОДН (кВт*ч)", "Всего (кВт*ч)", "Дата расчета"]
        self.tbl_history.setColumnCount(len(headers))
        self.tbl_history.setHorizontalHeaderLabels(headers)
        self.tbl_history.horizontalHeader().setStretchLastSection(True)
        self.tbl_history.setAlternatingRowColors(True)
        self.tbl_history.setEditTriggers(QTableWidget.NoEditTriggers)

        with self.db_manager.get_connection() as conn:
            rows = conn.execute("""
                SELECT id, period_month || ' ' || period_year, org_name, contract_number,
                       houses_count, total_day, total_night, total_odn, total_all, calculated_at
                FROM calculation_history ORDER BY id DESC;
            """).fetchall()
            self.tbl_history.setRowCount(len(rows))
            for r_idx, r in enumerate(rows):
                for c_idx in range(len(headers)):
                    val = r[c_idx]
                    if isinstance(val, float):
                        val_str = f"{val:,.3f}"
                    else:
                        val_str = str(val or "")
                    self.tbl_history.setItem(r_idx, c_idx, QTableWidgetItem(val_str))

    def load_tariffs_table(self):
        headers = ["ID", "Код зоны", "Наименование зоны тарифа", "Ставка (руб/кВт*ч)", "Примечание"]
        self.tbl_tariffs.setColumnCount(len(headers))
        self.tbl_tariffs.setHorizontalHeaderLabels(headers)
        self.tbl_tariffs.horizontalHeader().setStretchLastSection(True)
        self.tbl_tariffs.setAlternatingRowColors(True)
        self.tbl_tariffs.setEditTriggers(QTableWidget.NoEditTriggers)

        with self.db_manager.get_connection() as conn:
            rows = conn.execute("SELECT id, zone_code, zone_name, rate_rub, note FROM tariffs ORDER BY id;").fetchall()
            self.tbl_tariffs.setRowCount(len(rows))
            for r_idx, r in enumerate(rows):
                for c_idx in range(len(headers)):
                    self.tbl_tariffs.setItem(r_idx, c_idx, QTableWidgetItem(str(r[c_idx] or "")))


# ==============================================================================
# 5. CLOUD SYNC & SETTINGS DIALOG (Центр управления облачной синхронизацией)
# ==============================================================================
class CloudSyncDialog(QDialog):
    """
    Главный центр управления синхронизацией S3:
    - Проверка и сравнение версий ПО и БД
    - Ручной Pull (скачивание с созданием бэкапа)
    - Ручной Push (выгрузка в облако)
    - Настройки подключения и ключей S3
    - Блок самодиагностики с журналом
    """

    def __init__(self, config: S3Config, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.db_manager = db_manager
        self.diag_service = DiagnosticService(config, db_manager)

        self.setWindowTitle("Облачная синхронизация Yandex S3 и автообновление")
        self.resize(760, 680)
        self.setMinimumSize(680, 580)
        self.init_ui()

    def _active_workers(self):
        return [worker for name in ('check_worker','pull_worker','push_worker','force_push_worker','diag_worker')
                if (worker:=getattr(self,name,None)) is not None and worker.isRunning()]

    def done(self,result):
        if self._active_workers():
            self.lbl_operation.setText("Дождитесь завершения операции. База и соединения ещё используются.")
            return
        super().done(result)

    def closeEvent(self,event):
        if self._active_workers():
            self.lbl_operation.setText("Дождитесь завершения фоновой операции.")
            event.ignore()
        else:event.accept()

    def set_busy(self,busy,stage="Готово"):
        for button in (self.btn_check_now,self.btn_pull,self.btn_push,self.btn_run_diag,self.btn_save_settings):
            button.setEnabled(not busy)
        self.lbl_operation.setText(stage)
        if not busy:self.operation_progress.setValue(0)

    def show_progress(self,percent,stage):
        self.operation_progress.setValue(percent)
        self.lbl_operation.setText(stage)

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
                font-family: 'Segoe UI';
            }
            QFrame#cardFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 14px;
            }
            QLabel#sectionTitle {
                color: #38BDF8;
                font-size: 14px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 10px;
                color: #F8FAFC;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #38BDF8;
            }
            QPushButton#btnPrimary {
                background-color: #2563EB;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                border: none;
            }
            QPushButton#btnPrimary:hover {
                background-color: #1D4ED8;
            }
            QPushButton#btnSecondary {
                background-color: #334155;
                color: #F8FAFC;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 8px 14px;
                font-weight: 500;
            }
            QPushButton#btnSecondary:hover {
                background-color: #475569;
            }
            QTextBrowser#logView {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #CBD5E1;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
        """)

        scroll = QScrollArea(self)
        scroll.setStyleSheet("QScrollArea {background: #0F172A; border: none;}")
        scroll.viewport().setStyleSheet("background: #0F172A;")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        container.setObjectName("syncContent")
        container.setStyleSheet("QWidget#syncContent {background: #0F172A;}")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # -------------------------------------------------------------
        # 1. СТАТУС ВЕРСИЙ И БАЗЫ
        # -------------------------------------------------------------
        card_status = QFrame()
        card_status.setObjectName("cardFrame")
        c_layout = QVBoxLayout(card_status)
        c_layout.setSpacing(10)

        t1 = QLabel("📦 Статус приложения и базы данных")
        t1.setObjectName("sectionTitle")
        c_layout.addWidget(t1)

        v_grid = QVBoxLayout()
        self.lbl_app_ver = QLabel(f"Версия программы: v{DEFAULT_APP_VERSION}")
        self.lbl_app_ver.setStyleSheet("color: #E2E8F0; font-size: 13px; font-weight: 600;")
        v_grid.addWidget(self.lbl_app_ver)

        stats = self.db_manager.get_summary()
        self.lbl_db_ver = QLabel(f"Локальная БД: {stats.get('houses_count', 0)} домов  •  SHA: {stats.get('sha256', '')[:12]}...")
        self.lbl_db_ver.setWordWrap(True)
        self.lbl_db_ver.setStyleSheet("color: #94A3B8; font-size: 12px;")
        v_grid.addWidget(self.lbl_db_ver)
        v_grid.addStretch()

        c_layout.addLayout(v_grid)

        # Кнопки действий
        btn_actions = QHBoxLayout()
        btn_actions.setSpacing(10)

        self.btn_check_now = QPushButton("🔄 Проверить сейчас")
        self.btn_check_now.setObjectName("btnPrimary")
        self.btn_check_now.clicked.connect(self.run_check_updates)
        btn_actions.addWidget(self.btn_check_now)

        self.btn_pull = QPushButton("⬇️ Загрузить базу из облака (Pull)")
        self.btn_pull.setObjectName("btnSecondary")
        self.btn_pull.setToolTip("Скачивает актуальную базу из S3 с созданием страховочного бэкапа в backups/")
        self.btn_pull.clicked.connect(self.run_pull)
        btn_actions.addWidget(self.btn_pull)

        self.btn_push = QPushButton("⬆️ Выгрузить базу в облако (Push)")
        self.btn_push.setObjectName("btnSecondary")
        self.btn_push.setToolTip("Выгружает локальную базу SQLite в Yandex Cloud S3")
        self.btn_push.clicked.connect(self.run_push)
        btn_actions.addWidget(self.btn_push)

        self.btn_view_db = QPushButton("🔍 Просмотр БД")
        self.btn_view_db.setObjectName("btnSecondary")
        self.btn_view_db.clicked.connect(self.open_db_viewer)
        btn_actions.addWidget(self.btn_view_db)

        # Two rows keep actions readable on laptop screens and at 125–150% DPI.
        btn_actions.setDirection(QHBoxLayout.Direction.TopToBottom)
        c_layout.addLayout(btn_actions)
        self.lbl_operation=QLabel("Готово к проверке. Pull заменяет локальную базу с резервной копией; Push публикует её в S3.")
        self.lbl_operation.setWordWrap(True)
        self.lbl_operation.setStyleSheet("color: #94A3B8; padding: 4px 0;")
        c_layout.addWidget(self.lbl_operation)
        self.operation_progress=QProgressBar()
        self.operation_progress.setRange(0,100)
        self.operation_progress.setFixedHeight(16)
        self.operation_progress.setStyleSheet("QProgressBar {background: #0F172A; border: 1px solid #334155; border-radius: 6px; color: #CBD5E1; text-align: center;} QProgressBar::chunk {background: #2563EB; border-radius: 5px;}")
        c_layout.addWidget(self.operation_progress)
        layout.addWidget(card_status)

        # -------------------------------------------------------------
        # 2. НАСТРОЙКИ ОБЛАЧНОГО ХРАНИЛИЩА (S3 PARAMETERS)
        # -------------------------------------------------------------
        card_settings = QFrame()
        card_settings.setObjectName("cardFrame")
        s_layout = QVBoxLayout(card_settings)
        s_layout.setSpacing(10)

        t2 = QLabel("⚙️ Параметры подключения к Yandex Cloud S3")
        t2.setObjectName("sectionTitle")
        s_layout.addWidget(t2)

        # Тоггл автопроверки
        self.chk_auto = QCheckBox("Автоматически проверять обновления при запуске программы")
        self.chk_auto.setChecked(self.config.auto_check_updates)
        self.chk_auto.setStyleSheet("color: #E2E8F0; font-size: 13px;")
        s_layout.addWidget(self.chk_auto)

        # Поля S3
        row1 = QHBoxLayout()
        lbl_ep = QLabel("S3 Endpoint:")
        lbl_ep.setFixedWidth(100)
        self.edit_ep = QLineEdit(self.config.s3_endpoint)
        row1.addWidget(lbl_ep)
        row1.addWidget(self.edit_ep)
        s_layout.addLayout(row1)

        row2 = QHBoxLayout()
        lbl_b = QLabel("Целевой бакет:")
        lbl_b.setFixedWidth(100)
        self.edit_bucket = QLineEdit(self.config.s3_bucket)
        row2.addWidget(lbl_b)
        row2.addWidget(self.edit_bucket)
        s_layout.addLayout(row2)

        # Ключи для Push
        acc_k, sec_k = self.config.get_credentials()
        row3 = QHBoxLayout()
        lbl_ak = QLabel("Access Key ID:")
        lbl_ak.setFixedWidth(100)
        self.edit_acc_key = QLineEdit(acc_k)
        self.edit_acc_key.setPlaceholderText("Не требуется для чтения манифестов; нужен для Push")
        row3.addWidget(lbl_ak)
        row3.addWidget(self.edit_acc_key)
        s_layout.addLayout(row3)

        row4 = QHBoxLayout()
        lbl_sk = QLabel("Secret Key:")
        lbl_sk.setFixedWidth(100)
        self.edit_sec_key = QLineEdit(sec_k)
        self.edit_sec_key.setEchoMode(QLineEdit.Password)
        self.edit_sec_key.setPlaceholderText("Секретный ключ S3 для выгрузки")
        row4.addWidget(lbl_sk)
        row4.addWidget(self.edit_sec_key)

        btn_show_sec = QPushButton("👁️")
        btn_show_sec.setFixedSize(32, 28)
        btn_show_sec.setObjectName("btnSecondary")
        btn_show_sec.clicked.connect(self.toggle_sec_key_echo)
        row4.addWidget(btn_show_sec)
        s_layout.addLayout(row4)

        btn_save = QPushButton("💾 Сохранить настройки")
        self.btn_save_settings=btn_save
        btn_save.setObjectName("btnSecondary")
        btn_save.clicked.connect(self.save_settings)
        s_layout.addWidget(btn_save)

        layout.addWidget(card_settings)

        # -------------------------------------------------------------
        # 3. БЛОК САМОДИАГНОСТИКИ (Self-Diagnostic Block)
        # -------------------------------------------------------------
        card_diag = QFrame()
        card_diag.setObjectName("cardFrame")
        d_layout = QVBoxLayout(card_diag)
        d_layout.setSpacing(10)

        t3_row = QHBoxLayout()
        t3 = QLabel("🛡️ Диагностика связи с S3 и целостности")
        t3.setObjectName("sectionTitle")
        t3_row.addWidget(t3)
        t3_row.addStretch()

        self.btn_run_diag = QPushButton("⚡ Запустить диагностику")
        self.btn_run_diag.setObjectName("btnPrimary")
        self.btn_run_diag.clicked.connect(self.run_diagnostics)
        t3_row.addWidget(self.btn_run_diag)
        d_layout.addLayout(t3_row)

        self.diag_log = QTextBrowser()
        self.diag_log.setObjectName("logView")
        self.diag_log.setFixedHeight(140)
        self.diag_log.setPlainText("Нажмите «Запустить диагностику» для тестирования связи с сервером Yandex Cloud...")
        d_layout.addWidget(self.diag_log)

        layout.addWidget(card_diag)

        # Кнопка закрытия
        btn_close = QPushButton("Закрыть окно")
        btn_close.setObjectName("btnSecondary")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        scroll.setWidget(container)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def toggle_sec_key_echo(self):
        if self.edit_sec_key.echoMode() == QLineEdit.Password:
            self.edit_sec_key.setEchoMode(QLineEdit.Normal)
        else:
            self.edit_sec_key.setEchoMode(QLineEdit.Password)

    def save_settings(self):
        from cloud_sync import scoped_url
        old=dict(self.config.data)
        try:
            self.config.data["s3_endpoint"]=self.edit_ep.text().strip()
            self.config.data["s3_bucket"]=self.edit_bucket.text().strip()
            scoped_url(self.config.get_manifest_url(),self.config)
            self.config.data["auto_check_updates"]=self.chk_auto.isChecked()
            self.config.set_credentials(self.edit_acc_key.text(),self.edit_sec_key.text())
            self.config.save()
            self.lbl_operation.setText("Настройки сохранены. Ключи защищены Windows для текущего пользователя.")
        except Exception as error:
            self.config.data=old
            QMessageBox.warning(self,"Настройки не сохранены",str(error))

    def run_check_updates(self):
        if self._active_workers():return
        self.set_busy(True,"Проверка версии и облачной ревизии…")
        self.btn_check_now.setEnabled(False)
        self.btn_check_now.setText("⏳ Проверка...")

        self.check_worker = CheckUpdatesWorker(self.config, DEFAULT_APP_VERSION)
        self.check_worker.finished.connect(self.on_check_finished)
        self.check_worker.error.connect(self.on_check_error)
        self.check_worker.start()

    def on_check_finished(self, res: dict):
        self.set_busy(False,"Связь с S3 подтверждена.")
        self.lbl_app_ver.setText(f"Установлено: v{DEFAULT_APP_VERSION}   •   В облаке: v{res.get('cloud_app_version')}")
        self.btn_check_now.setEnabled(True)
        self.btn_check_now.setText("🔄 Проверить сейчас")

        has_app = res.get("has_app_update", False)
        has_db = res.get("has_db_update", False)
        cloud_v = res.get("cloud_app_version", DEFAULT_APP_VERSION)

        if has_app:
            dlg = UpdateModalDialog(DEFAULT_APP_VERSION, res, self)
            dlg.exec()
        elif has_db:
            msg = QMessageBox.question(
                self,
                "Обновление базы данных",
                f"Облачная база отличается от локальной.\n"
                f"Хэш в облаке: {res.get('cloud_db_sha256', '')[:16]}...\n\n"
                f"Заменить локальную базу облачной копией?",
                QMessageBox.Yes | QMessageBox.No
            )
            if msg == QMessageBox.Yes:
                self.run_pull()
        else:
            QMessageBox.information(
                self,
                "Актуальная версия",
                f"Программа и база данных полностью обновлены!\n"
                f"Версия программы: v{DEFAULT_APP_VERSION}\n"
                f"Облачная версия: v{cloud_v}"
            )

    def on_check_error(self, err: str):
        self.set_busy(False,"Офлайн: "+err)
        self.btn_check_now.setEnabled(True)
        self.btn_check_now.setText("🔄 Проверить сейчас")
        QMessageBox.warning(self, "Ошибка проверки", f"Не удалось опросить сервер обновления:\n{err}")

    def run_pull(self):
        if self._active_workers():return
        if QMessageBox.question(self,"Загрузка базы","Локальная база будет заменена облачной. Резервная копия сохранится в backups. Продолжить?",QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
        self.set_busy(True,"Запрос облачной базы…")
        self.btn_pull.setEnabled(False)
        self.pull_worker = SyncPullWorker(self.config, self.db_manager)
        self.pull_worker.finished.connect(self.on_pull_finished)
        self.pull_worker.error.connect(self.on_pull_error)
        self.pull_worker.progress.connect(self.show_progress)
        self.pull_worker.start()

    def on_pull_finished(self, res: dict):
        self.set_busy(False,"База загружена, SHA-256 проверена. Резервная копия сохранена.")
        self.btn_pull.setEnabled(True)
        stats = self.db_manager.get_summary()
        self.lbl_db_ver.setText(f"Локальная БД: {stats.get('houses_count', 0)} домов  •  SHA: {stats.get('sha256', '')[:12]}...")
        QMessageBox.information(
            self,
            "База данных обновлена",
            f"База данных успешно получена из облака!\n"
            f"Версия: v{res.get('version')}\n"
            f"SHA-256: {res.get('sha256')[:16]}...\n\n"
            f"Страховочная резервная копия создана в папке backups/."
        )

    def on_pull_error(self, err: str):
        self.set_busy(False,"База не заменена: "+err)
        self.btn_pull.setEnabled(True)
        QMessageBox.critical(self, "Ошибка загрузки базы", f"Сбой при загрузке базы:\n{err}")

    def run_push(self):
        if self._active_workers():return
        acc, sec = self.config.get_credentials()
        if not acc or not sec:
            QMessageBox.warning(
                self,
                "Требуются ключи доступа",
                "Для выгрузки в облако необходимо указать Access Key ID и Secret Key в блоке настроек ниже."
            )
            return

        self.set_busy(True,"Подготовка согласованного снимка базы…")
        self.push_worker = SyncPushWorker(self.config, self.db_manager, force_overwrite=False)
        self.push_worker.conflict_detected.connect(self.on_push_conflict)
        self.push_worker.finished.connect(self.on_push_finished)
        self.push_worker.error.connect(self.on_push_error)
        self.push_worker.progress.connect(self.show_progress)
        self.push_worker.start()

    def on_push_conflict(self, conf_info: dict):
        msg = QMessageBox.warning(
            self,
            "Конфликт версий базы данных",
            f"Облачная база отличается от последней синхронизированной ревизии.\n\n"
            f"Дата в облаке: {conf_info.get('cloud_last_modified')}\n"
            f"Хэш в облаке: {conf_info.get('cloud_sha256')[:16]}...\n"
            f"Локальный хэш: {conf_info.get('local_sha256')[:16]}...\n\n"
            f"Перезаписать облачную копию вашими локальными данными?",
            QMessageBox.Yes | QMessageBox.No
        )
        if msg == QMessageBox.Yes:
            # Принудительная перезапись
            self.force_push_worker = SyncPushWorker(self.config, self.db_manager, force_overwrite=True, expected_cloud=conf_info.get('cloud_sha256'))
            self.force_push_worker.finished.connect(self.on_push_finished)
            self.force_push_worker.error.connect(self.on_push_error)
            self.force_push_worker.conflict_detected.connect(self.on_push_conflict)
            self.force_push_worker.progress.connect(self.show_progress)
            self.force_push_worker.start()
        else:
            self.set_busy(False,"Выгрузка отменена: облачная база сохранена.")

    def on_push_finished(self, res: dict):
        self.set_busy(False,"Ревизия опубликована. SHA-256: "+str(res.get('sha256',''))[:16])
        self.btn_push.setEnabled(True)
        QMessageBox.information(
            self,
            "Выгрузка завершена",
            f"Локальная база успешно опубликована в бакет Yandex Cloud!\n"
            f"Новая облачная версия: v{res.get('version')}\n"
            f"SHA-256: {res.get('sha256')[:16]}..."
        )

    def on_push_error(self, err: str):
        self.set_busy(False,"Выгрузка не завершена: "+err)
        self.btn_push.setEnabled(True)
        QMessageBox.critical(self, "Ошибка выгрузки", f"Не удалось выгрузить базу:\n{err}")

    def run_diagnostics(self):
        if self._active_workers():return
        self.set_busy(True,"Проверка DNS, доступа к S3, манифеста и SQLite…")
        self.btn_run_diag.setEnabled(False)
        self.diag_log.setPlainText("Запуск 4-этапной проверки инфраструктуры...\n")

        self.diag_worker = DiagnosticWorker(self.diag_service)
        self.diag_worker.finished.connect(self.on_diag_finished)
        self.diag_worker.start()

    def on_diag_finished(self, res: dict):
        self.set_busy(False,"Диагностика завершена.")
        self.btn_run_diag.setEnabled(True)
        lines = res.get("report_lines", [])
        text = "\n".join(lines)
        if res.get("overall_ok"):
            text += "\n\n🎉 Все тесты пройдены! Инфраструктура готова к работе."
        else:
            text += "\n\n⚠️ Обнаружены предупреждения или ошибки соединения."
        self.diag_log.setPlainText(text)

    def open_db_viewer(self):
        dlg = DatabaseViewerDialog(self.db_manager, self)
        dlg.exec()
