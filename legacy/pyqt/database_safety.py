"""Read-only validation and consistent SQLite snapshots for database replacement."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile

def validate_database(path,required_tables=()):
    uri=Path(path).resolve().as_uri()+"?mode=ro"
    with closing(sqlite3.connect(uri,uri=True,timeout=5)) as conn:
        result=conn.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0]!="ok":raise ValueError("Поврежденная база SQLite.")
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing=set(required_tables)-tables
        if missing:raise ValueError("Неподходящая структура базы: отсутствуют таблицы "+", ".join(sorted(missing)))

def stage_database(source,target_dir,required_tables=()):
    validate_database(source,required_tables)
    fd,path=tempfile.mkstemp(prefix=".db-update-",suffix=".sqlite",dir=target_dir)
    os.close(fd)
    try:
        with closing(sqlite3.connect(Path(source).resolve().as_uri()+"?mode=ro",uri=True)) as src, closing(sqlite3.connect(path)) as dst:
            src.backup(dst)
        validate_database(path,required_tables)
        return path
    except Exception:
        if os.path.exists(path):os.remove(path)
        raise
