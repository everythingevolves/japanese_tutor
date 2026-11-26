"""One local learner per database. All schema changes run inside a transaction."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .curriculum import SCENES, dump

MIGRATIONS = Path(__file__).with_name("migrations")


def default_path():
    checkout = Path(__file__).resolve().parents[2]
    if (checkout / "japanese-tutor").is_file() and (checkout / "pyproject.toml").is_file():
        directory = checkout / ".local"
    else:
        directory = Path.home() / ".local/share/japanese-tutor"
    return Path(os.environ.get("JAPANESE_TUTOR_DB", directory / "learner.sqlite3")).expanduser()


@contextmanager
def transaction(db):
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.commit()
    except BaseException:
        db.rollback()
        raise


def connect(path=None):
    path = Path(path) if path else default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, isolation_level=None, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys = ON")
        with transaction(db):
            version = db.execute("PRAGMA user_version").fetchone()[0]
            files = sorted(MIGRATIONS.glob("*.sql"))
            if version > len(files):
                raise ValueError("This database needs a newer Japanese tutor.")
            for number, migration in enumerate(files, 1):
                if number <= version:
                    continue
                statement = ""
                for line in migration.read_text().splitlines(True):
                    statement += line
                    if sqlite3.complete_statement(statement):
                        db.execute(statement)
                        statement = ""
                if statement.strip():
                    raise ValueError("Incomplete migration")
                db.execute(f"PRAGMA user_version = {number}")
            scene = SCENES["cafe.first"]
            db.execute("INSERT OR IGNORE INTO lesson(id, revision, scene, prompt, support) VALUES (1, 0, ?, ?, 1)",
                       ("cafe.first", dump(scene["opening"])))
        return db
    except BaseException:
        db.close()
        raise


def copy_database(source, target):
    """Copy a consistent snapshot. Publish only a complete copy, to a new path."""
    import tempfile
    source, target = Path(source), Path(target)
    if not source.is_file():
        raise ValueError("Source database does not exist")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=target.parent)
    os.close(fd)
    try:
        from contextlib import closing
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src:
            if not src.execute("SELECT 1 FROM lesson WHERE id=1").fetchone():
                raise ValueError("Missing lesson")
            with closing(sqlite3.connect(name)) as dest:
                src.backup(dest)
                if dest.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Invalid backup")
        os.link(name, target)
    finally:
        os.unlink(name)
