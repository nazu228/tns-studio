"""
Модуль синхронизации баз данных и автообновления через Yandex Cloud Object Storage (S3).
Обеспечивает:
- Асинхронное получение манифестов и релизов по прямому HTTPS GET.
- HTTPS с обязательной проверкой сертификатов.
- Локальную базу SQLite (database/tns_database.sqlite) со справочниками домов, тарифов и историей расчетов.
- Создание резервных копий в backups/ перед Pull-синхронизацией.
- Загрузку в S3 с ACL public-read через boto3 (Push) с контролем конфликтов версий.
- Автономное развертывание обновлений под Windows через самоликвидирующийся BAT-скрипт с контролем PID.
- 4-этапную самодиагностику соединения и целостности БД.
- QThread-воркеры для неблокирующего интерфейса PySide6.
"""

from cloud_sync import (CloudDatabaseSync, PublicHttp, SyncError, SyncConflict, atomic_json, credentials, save_credentials, scoped_url, validate_hash, validate_manifest, database_differs)
import os
import sys
import json
import time
import socket
import ssl
import shutil
import hashlib
import sqlite3
from contextlib import closing
from database_safety import validate_database, stage_database
import datetime
import tempfile
import zipfile
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple, List, Callable

from PySide6.QtCore import QThread, Signal, QObject

# Константы приложения по умолчанию
DEFAULT_APP_SLUG = "tns_studio"
DEFAULT_APP_NAME = "ТНС Энерго — Студия начислений по домам"
DEFAULT_APP_VERSION = "2.2.4"
DEFAULT_S3_ENDPOINT = "https://storage.yandexcloud.net"
DEFAULT_S3_BUCKET = "ajeftdaam8hhmrujr94k"
DEFAULT_S3_REGION = "ru-central1"


def get_app_dir() -> str:
    """
    Возвращает надежный корневой путь к приложению.
    Корректно работает как в режиме исходного кода Python, так и в PyInstaller frozen exe.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_executable_path() -> str:
    """Возвращает путь к текущему исполняемому файлу или скрипту запуска."""
    if getattr(sys, 'frozen', False):
        return os.path.abspath(sys.executable)
    return os.path.abspath(sys.argv[0])


def calculate_file_sha256(filepath: str) -> str:
    """Вычисляет SHA-256 хэш файла."""
    if not os.path.exists(filepath):
        return ""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# ==============================================================================
# 1. КОНФИГУРАЦИЯ СИНХРОНИЗАЦИИ (S3Config)
# ==============================================================================
class S3Config:
    """Управление настройками S3 и синхронизации."""

    def __init__(self, config_path: Optional[str] = None):
        self.app_dir = get_app_dir()
        self.config_path = config_path or os.path.join(self.app_dir, "sync_config.json")
        self.data: Dict[str, Any] = {
            "app_slug": DEFAULT_APP_SLUG,
            "app_name": DEFAULT_APP_NAME,
            "s3_endpoint": DEFAULT_S3_ENDPOINT,
            "s3_bucket": DEFAULT_S3_BUCKET,
            "s3_region": DEFAULT_S3_REGION,
            "auto_check_updates": True,
            "access_key_id": "",
            "secret_access_key": "",
            "last_check_timestamp": "",
            "last_sync_timestamp": "",
            "cloud_manifest_cache": {}
        }
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
            except Exception as e:
                print(f"[S3Config] Ошибка чтения конфига: {e}")

    def save(self):
        atomic_json(self.config_path,self.data)

    @property
    def app_slug(self) -> str:
        return self.data.get("app_slug", DEFAULT_APP_SLUG)

    @property
    def s3_endpoint(self) -> str:
        return self.data.get("s3_endpoint", DEFAULT_S3_ENDPOINT)

    @property
    def s3_bucket(self) -> str:
        return self.data.get("s3_bucket", DEFAULT_S3_BUCKET)

    @property
    def s3_region(self) -> str:
        return self.data.get("s3_region", DEFAULT_S3_REGION)

    @property
    def auto_check_updates(self) -> bool:
        return bool(self.data.get("auto_check_updates", True))

    @auto_check_updates.setter
    def auto_check_updates(self, val: bool):
        self.data["auto_check_updates"] = bool(val)
        self.save()

    def get_credentials(self):
        return credentials(self)

    def set_credentials(self, acc_key, sec_key):
        save_credentials(self, acc_key, sec_key)

    def get_manifest_url(self) -> str:
        endpoint = self.s3_endpoint.rstrip("/")
        bucket = self.s3_bucket
        slug = self.app_slug
        return f"{endpoint}/{bucket}/{slug}/latest.json"

    def get_database_url(self) -> str:
        endpoint = self.s3_endpoint.rstrip("/")
        bucket = self.s3_bucket
        slug = self.app_slug
        return f"{endpoint}/{bucket}/{slug}/database/tns_database.sqlite"

    def get_database_meta_url(self) -> str:
        endpoint = self.s3_endpoint.rstrip("/")
        bucket = self.s3_bucket
        slug = self.app_slug
        return f"{endpoint}/{bucket}/{slug}/database/database_meta.json"


# ==============================================================================
# 2. УСТОЙЧИВЫЙ СЕТЕВОЙ КЛИЕНТ (HTTP Client with SSL Resilience)
# ==============================================================================
class ResilientHttpClient:
    """
    HTTP-клиент для публичных GET-запросов к S3 Yandex Cloud.
    Предусматривает fallback при повреждении системных корневых сертификатов Windows
    или проверке корпоративными фаерволами.
    """

    @staticmethod
    def _create_ssl_context(verify=True):
        if not verify:raise ValueError("Проверку сертификата HTTPS отключать нельзя.")
        return ssl.create_default_context()


    @classmethod
    def get_json(cls, url: str, timeout: int = 10) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Выполняет HTTPS GET и парсит JSON ответ."""
        data, err = cls.get_bytes(url, timeout=timeout)
        if err or not data:
            return None, err
        try:
            parsed = json.loads(data.decode("utf-8"))
            return parsed, None
        except Exception as e:
            return None, f"Ошибка парсинга JSON ответа: {e}"

    @classmethod
    def get_bytes(cls,url,timeout=10):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":f"TNSStudio-Sync/{DEFAULT_APP_VERSION}"})
            with urllib.request.urlopen(req,timeout=timeout,context=cls._create_ssl_context()) as response:
                return response.read(),None
        except Exception as error:return None,f"Ошибка HTTPS: {error}"


    @classmethod
    def download_file_with_progress(
        cls,
        url: str,
        dest_path: str,
        progress_callback: Optional[Callable[[int, int, float, str], None]] = None,
        timeout: int = 25
    ) -> Tuple[bool, Optional[str]]:
        """
        Потоковое скачивание файла с расчетом процентов, скачанных байт и скорости (МБ/с).
        progress_callback(percent, downloaded_bytes, speed_mbps, stage_text)
        """
        headers = {
            "User-Agent": f"TNSStudio-Sync/{DEFAULT_APP_VERSION} (Windows; x64)",
            "Accept": "*/*"
        }
        req = urllib.request.Request(url, headers=headers)

        ctx = cls._create_ssl_context(verify=True)
        try:
            response = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        except Exception as e:
            return False, f"Ошибка подключения: {e}"

        total_size = response.getheader('Content-Length')
        total_bytes = int(total_size) if total_size and total_size.isdigit() else 0

        downloaded = 0
        start_time = time.time()
        last_update = 0.0

        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        part_path = dest_path + ".part"

        try:
            with open(part_path, "wb") as f:
                while True:
                    chunk = response.read(65536)  # 64 KB
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    now = time.time()
                    elapsed = max(now - start_time, 0.001)
                    speed_mbps = (downloaded / (1024 * 1024)) / elapsed

                    # Обновляем UI с частотой ~10 раз в сек
                    if now - last_update > 0.08 or downloaded == total_bytes:
                        last_update = now
                        percent = int((downloaded / total_bytes) * 100) if total_bytes > 0 else 0
                        if progress_callback:
                            down_mb = downloaded / (1024 * 1024)
                            tot_mb = total_bytes / (1024 * 1024) if total_bytes > 0 else 0
                            progress_callback(percent, downloaded, speed_mbps, f"Загрузка: {down_mb:.1f} / {tot_mb:.1f} МБ ({speed_mbps:.2f} МБ/с)")

            # Атомарно переименовываем из .part
            os.replace(part_path, dest_path)
            return True, None

        except Exception as e:
            if os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except Exception:
                    pass
            return False, f"Ошибка в процессе скачивания файла: {e}"
        finally:
            response.close()


# ==============================================================================
# 3. ЛОКАЛЬНЫЙ ДВИЖОК SQLITE (DatabaseManager)
# ==============================================================================
class DatabaseManager:
    """
    Управление локальной базой SQLite:
    - Справочник организаций и домов
    - Справочник тарифов ТНС
    - История выполненных расчетов начислений
    - Бэкапирование перед заменой
    - Хэширование SHA-256
    """

    def __init__(self, db_path: Optional[str] = None):
        self.app_dir = get_app_dir()
        self.db_dir = os.path.join(self.app_dir, "database")
        self.backup_dir = os.path.join(self.app_dir, "backups")
        os.makedirs(self.db_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)

        self.db_path = db_path or os.path.join(self.db_dir, "tns_database.sqlite")
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Создает таблицы и наполняет начальными справочниками, если база пустая."""
        with closing(self.get_connection()) as conn, conn:
            cursor = conn.cursor()

            # 1. Организации (УК)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS organizations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    contract_number TEXT NOT NULL UNIQUE,
                    slug TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Справочник домов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS houses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_contract TEXT NOT NULL,
                    address TEXT NOT NULL UNIQUE,
                    meters_count_active INTEGER DEFAULT 0,
                    meters_count_reserve INTEGER DEFAULT 0,
                    note TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Справочник тарифов ТНС
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tariffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    zone_code TEXT NOT NULL UNIQUE,
                    zone_name TEXT NOT NULL,
                    rate_rub REAL DEFAULT 0.0,
                    note TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 4. История и архив расчетов
            cursor.execute("""
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
            """)

            # 5. Метаданные синхронизации
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Начальное наполнение организаций
            cursor.execute("SELECT COUNT(*) FROM organizations;")
            if cursor.fetchone()[0] == 0:
                cursor.executemany("""
                    INSERT INTO organizations (name, contract_number, slug)
                    VALUES (?, ?, ?);
                """, [
                    ("ООО «Южный Дом»", "23110603789", "dom"),
                    ("ООО «Южный Город»", "23110604327", "gorod")
                ])

            # Начальное наполнение тарифов
            cursor.execute("SELECT COUNT(*) FROM tariffs;")
            if cursor.fetchone()[0] == 0:
                cursor.executemany("""
                    INSERT INTO tariffs (zone_code, zone_name, rate_rub, note)
                    VALUES (?, ?, ?, ?);
                """, [
                    ("day", "Энергия День (Пик / Полупик / Т1)", 7.15, "Дневная зона суток 07:00-23:00"),
                    ("night", "Энергия Ночь (Т2)", 4.22, "Ночная зона суток 23:00-07:00"),
                    ("odn", "ОДН (Общедомовые нужды / ЗР / Одноставочный)", 6.45, "Вводы нежилых, лифты, ИТП, насосные")
                ])

            # Начальная фиксация версии БД в метаданных
            cursor.execute("""
                INSERT OR IGNORE INTO sync_metadata (key, value) VALUES ('db_version', '1');
            """)
            cursor.execute("""
                INSERT OR IGNORE INTO sync_metadata (key, value) VALUES ('last_sync_timestamp', '');
            """)
            conn.commit()

    def create_backup(self) -> Tuple[bool, str]:
        """Создает бэкап базы данных в папку backups/ с временной меткой."""
        if not os.path.exists(self.db_path):
            return False, "Файл базы данных не существует."
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_filename = f"tns_database_backup_{ts}.sqlite"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        try:
            # Используем SQLite backup API для консистентного горячего бэкапа
            with closing(self.get_connection()) as src_conn, src_conn:
                dst_conn = sqlite3.connect(backup_path)
                src_conn.backup(dst_conn)
                dst_conn.close()
            return True, backup_path
        except Exception as e:
            return False,f"Ошибка создания консистентной резервной копии: {e}"

    def calculate_sha256(self) -> str:
        return calculate_file_sha256(self.db_path)

    def safe_replace(self,new_db_filepath):
        staged=None
        backup=None
        swapped=False
        try:
            required=("organizations","houses","calculation_history","sync_metadata")
            staged=stage_database(new_db_filepath,os.path.dirname(self.db_path),required)
            success,backup=self.create_backup()
            if not success:return False,f"Не удалось создать бэкап: {backup}"
            os.replace(staged,self.db_path)
            staged=None
            swapped=True
            self.init_db()
            validate_database(self.db_path,required)
            return True,None
        except Exception as error:
            if swapped and backup:
                restore=stage_database(backup,os.path.dirname(self.db_path))
                os.replace(restore,self.db_path)
            return False,f"База не обновлена, прежние данные сохранены: {error}"
        finally:
            if staged and os.path.exists(staged):os.remove(staged)


    def record_calculation(self, month: str, year: str, org_type: str, org_name: str,
                           contract_number: str, houses_count: int,
                           total_day: float, total_night: float, total_odn: float,
                           total_all: float, balance_diff: float, filename: str):
        """Автоматическая запись результата расчета в базу данных."""
        try:
            with closing(self.get_connection()) as conn, conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO calculation_history (
                        period_month, period_year, org_type, org_name, contract_number,
                        houses_count, total_day, total_night, total_odn, total_all,
                        balance_diff, saved_filename, calculated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    month, year, org_type, org_name, contract_number,
                    houses_count, total_day, total_night, total_odn, total_all,
                    balance_diff, filename, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
                # Обновляем timestamp изменения локальной базы
                cursor.execute("""
                    INSERT OR REPLACE INTO sync_metadata (key, value, updated_at)
                    VALUES ('local_modified_timestamp', ?, CURRENT_TIMESTAMP);
                """, (datetime.datetime.now().isoformat(),))
                conn.commit()
        except Exception as e:
            print(f"[DatabaseManager] Ошибка записи истории расчетов: {e}")

    def register_or_update_house(self, contract_number: str, address: str, meters_active: int = 0, meters_res: int = 0):
        """Регистрирует или обновляет данные дома в справочнике."""
        try:
            with closing(self.get_connection()) as conn, conn:
                conn.execute("""
                    INSERT INTO houses (org_contract, address, meters_count_active, meters_count_reserve, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(address) DO UPDATE SET
                        org_contract=excluded.org_contract,
                        meters_count_active=excluded.meters_count_active,
                        meters_count_reserve=excluded.meters_count_reserve,
                        updated_at=CURRENT_TIMESTAMP;
                """, (contract_number, address, meters_active, meters_res))
                conn.commit()
        except Exception as e:
            print(f"[DatabaseManager] Ошибка обновления реестра домов: {e}")

    def get_summary(self) -> Dict[str, Any]:
        """Возвращает общую статистику по базе данных."""
        try:
            with closing(self.get_connection()) as conn, conn:
                c = conn.cursor()
                houses_cnt = c.execute("SELECT COUNT(*) FROM houses;").fetchone()[0]
                history_cnt = c.execute("SELECT COUNT(*) FROM calculation_history;").fetchone()[0]
                last_calc = c.execute("SELECT period_month, period_year, calculated_at FROM calculation_history ORDER BY id DESC LIMIT 1;").fetchone()
                last_calc_str = f"{last_calc[0]} {last_calc[1]} ({last_calc[2]})" if last_calc else "Нет расчетов"
                return {
                    "houses_count": houses_cnt,
                    "calculations_count": history_cnt,
                    "last_calculation": last_calc_str,
                    "sha256": self.calculate_sha256(),
                    "file_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                }
        except Exception as e:
            return {"error": str(e), "houses_count": 0, "calculations_count": 0, "sha256": ""}


# ==============================================================================
# 4. WINDOWS UPDATE DEPLOYER (Автономное развертывание)
# ==============================================================================
class WindowsUpdateDeployer:
    @classmethod
    def deploy_zip_update(cls,zip_filepath,restart_target=None):
        from windows_update import prepare_update
        if getattr(sys,'frozen',False):exe=sys.executable;args=[]
        elif restart_target and restart_target.lower().endswith('.exe'):exe=restart_target;args=[]
        else:exe=sys.executable;args=[restart_target or os.path.join(get_app_dir(),'app_gui.py')]
        return prepare_update(zip_filepath,get_app_dir(),DEFAULT_APP_SLUG,exe,args)


# ==============================================================================
# 5. СЕРВИС САМОДИАГНОСТИКИ (DiagnosticService)
# ==============================================================================
class DiagnosticService:
    """
    4-этапная диагностика облачной инфраструктуры:
    1. DNS резолвинг хоста S3 Yandex Cloud.
    2. Доступность бакета по HTTPS.
    3. Валидация манифеста latest.json и структуры схемы.
    4. Целостность и контрольная сумма локальной базы данных SQLite.
    """

    def __init__(self, config: S3Config, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager

    def run_diagnostics(self):
        from cloud_sync import run_diagnostics
        return run_diagnostics(self.config,self.db_manager)


# ==============================================================================
# 6. S3 PUSH ENGINE (Загрузка в Yandex Cloud через boto3)
# ==============================================================================
class S3PushEngine:
    """
    Загрузка баз данных и манифестов в Yandex Cloud Object Storage по протоколу S3.
    Использует библиотеку boto3 с выставлением ACL 'public-read'.
    """

    @classmethod
    def upload_file(cls, config: S3Config, local_filepath: str, s3_key: str, content_type: str = "application/octet-stream") -> Tuple[bool, Optional[str]]:
        acc_key, sec_key = config.get_credentials()
        if not acc_key or not sec_key:
            return False, "Не указаны ключи доступа S3 (Access Key ID / Secret Key). Задайте их в Настройках или переменных окружения."

        try:
            import boto3
            from botocore.config import Config as BotoConfig

            session = boto3.session.Session()
            s3 = session.client(
                service_name='s3',
                endpoint_url=config.s3_endpoint,
                aws_access_key_id=acc_key,
                aws_secret_access_key=sec_key,
                region_name=config.s3_region,
                config=BotoConfig(signature_version='s3v4', connect_timeout=15, read_timeout=30)
            )

            extra_args = {
                'ACL': 'public-read',
                'ContentType': content_type
            }

            s3.upload_file(
                Filename=local_filepath,
                Bucket=config.s3_bucket,
                Key=s3_key,
                ExtraArgs=extra_args
            )
            return True, None

        except ImportError:
            return False, "Библиотека boto3 не установлена. Установите её: pip install boto3"
        except Exception as e:
            return False, f"Ошибка выгрузки в S3: {e}"

    @classmethod
    def upload_json(cls, config: S3Config, data: Dict[str, Any], s3_key: str) -> Tuple[bool, Optional[str]]:
        temp_file = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, suffix=".json")
        try:
            json.dump(data, temp_file, ensure_ascii=False, indent=2)
            temp_file.close()
            return cls.upload_file(config, temp_file.name, s3_key, content_type="application/json; charset=utf-8")
        finally:
            if os.path.exists(temp_file.name):
                try:
                    os.remove(temp_file.name)
                except Exception:
                    pass


# ==============================================================================
# 7. ФОНОВЫЕ ПОТОКИ ДЛЯ PySide6 GUI (QThread Workers)
# ==============================================================================
class CheckUpdatesWorker(QThread):
    """Фоновая проверка манифеста latest.json без подвисания GUI."""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, config: S3Config, current_version: str = DEFAULT_APP_VERSION):
        super().__init__()
        self.config = config
        self.current_version = current_version

    def run(self):
        try:
            service=CloudDatabaseSync(self.config,DatabaseManager(),self.current_version,DEFAULT_APP_NAME)
            manifest=service.manifest()
            cloud_ver=manifest['app_version']
            has_app_update=self._compare_versions(cloud_ver,self.current_version)>0
            if has_app_update:
                package=manifest.get('package') or {}
                validate_hash(package.get('sha256'))
                scoped_url(package.get('url'),self.config,'releases')
            cloud_hash=(manifest.get('database') or {}).get('sha256','')
            local_hash=service.fingerprint()
            self.finished.emit({'manifest':manifest,'current_app_version':self.current_version,'cloud_app_version':cloud_ver,'has_app_update':has_app_update,'has_db_update':database_differs(self.config,cloud_hash,local_hash),'cloud_db_sha256':cloud_hash,'local_db_sha256':local_hash,'release_notes':manifest.get('release_notes',''),'release_date':manifest.get('release_date',''),'package_info':manifest.get('package',{})})
        except Exception as error:self.error.emit(str(error))

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """Сравнение версий SemVer (1 если v1 > v2, -1 если v1 < v2, 0 если равны)."""
        def parse_v(s):
            clean = s.lower().replace("v", "").strip()
            parts = []
            for p in clean.split("."):
                try:
                    parts.append(int(p))
                except ValueError:
                    parts.append(0)
            while len(parts) < 3:
                parts.append(0)
            return parts[:3]

        p1 = parse_v(v1)
        p2 = parse_v(v2)
        if p1 > p2:
            return 1
        elif p1 < p2:
            return -1
        return 0


class DownloadUpdateWorker(QThread):
    """Фоновое скачивание дистрибутива обновления с проверкой SHA-256."""
    progress = Signal(int, int, float, str)  # percent, bytes, speed_mbps, stage_text
    finished = Signal(str)                   # local filepath of verified download
    error = Signal(str)

    def __init__(self, package_url: str, expected_sha256: str, target_filename: str):
        super().__init__()
        self.package_url = package_url
        self.expected_sha256 = str(expected_sha256 or "").lower().strip()
        self.target_filename = target_filename

    def run(self):
        path=None
        try:
            expected=validate_hash(self.expected_sha256)
            fd,path=tempfile.mkstemp(prefix='tns-update-',suffix='.zip');os.close(fd)
            PublicHttp().download(self.package_url,path,expected,lambda percent,stage:self.progress.emit(percent,os.path.getsize(path) if os.path.exists(path) else 0,0.0,stage))
            self.finished.emit(path)
        except Exception as error:
            if path and os.path.exists(path):os.unlink(path)
            self.error.emit(str(error))


class SyncPullWorker(QThread):
    """Фоновое скачивание и горячая замена базы SQLite из облака."""
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, config: S3Config, db_manager: DatabaseManager):
        super().__init__()
        self.config = config
        self.db_manager = db_manager

    def run(self):
        try:
            service=CloudDatabaseSync(self.config,self.db_manager,DEFAULT_APP_VERSION,DEFAULT_APP_NAME)
            info=service.pull(lambda percent,stage:self.progress.emit(percent,stage))
            self.finished.emit(info)
        except Exception as error:self.error.emit(str(error))


class SyncPushWorker(QThread):
    """Фоновая выгрузка локальной базы SQLite в облако с проверкой конфликтов."""
    progress = Signal(int, str)
    conflict_detected = Signal(dict)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self,config,db_manager,force_overwrite=False,expected_cloud=None):
        super().__init__()
        self.config=config;self.db_manager=db_manager;self.force_overwrite=force_overwrite;self.expected_cloud=expected_cloud

    def run(self):
        try:
            service=CloudDatabaseSync(self.config,self.db_manager,DEFAULT_APP_VERSION,DEFAULT_APP_NAME)
            info=service.push(self.force_overwrite,self.expected_cloud,lambda percent,stage:self.progress.emit(percent,stage))
            self.finished.emit(info)
        except SyncConflict as conflict:self.conflict_detected.emit(conflict.details)
        except Exception as error:self.error.emit(str(error))


class DiagnosticWorker(QThread):
    """Фоновый запуск 4-этапной самодиагностики."""
    finished = Signal(dict)

    def __init__(self, diagnostic_service: DiagnosticService):
        super().__init__()
        self.service = diagnostic_service

    def run(self):
        res = self.service.run_diagnostics()
        self.finished.emit(res)
