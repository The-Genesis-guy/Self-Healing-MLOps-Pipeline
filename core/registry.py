import sqlite3
import os
from datetime import datetime
from dataclasses import dataclass
from contextlib import closing

# Path to the SQLite database file
# This file gets created automatically on first run
DB_PATH = "models/registry.db"

@dataclass
class ModelRecord:
    """One row in the registry — represents a single trained model version."""
    version: int
    path: str
    accuracy: float
    f1_score: float
    trained_at: str
    is_active: bool


class ModelRegistry:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        # Make sure the models/ directory exists before we try to create the DB inside it
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """
        Creates the models table if it doesn't exist yet.
        SQLite creates the .db file on first connection automatically.
        This method is safe to call multiple times — IF NOT EXISTS means it won't
        wipe existing data on restart.
        """
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    version     INTEGER PRIMARY KEY,
                    path        TEXT NOT NULL,
                    accuracy    REAL NOT NULL,
                    f1_score    REAL NOT NULL,
                    trained_at  TEXT NOT NULL,
                    is_active   INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.commit()

    def register(self, path: str, accuracy: float, f1_score: float) -> ModelRecord:
        """
        Saves a new model to the registry.
        Version is auto-incremented — max(version) + 1.
        The new model is NOT set as active automatically. 
        You have to explicitly call set_active() after evaluating it.
        """
        with closing(sqlite3.connect(self.db_path)) as conn:
            # Find the next version number
            row = conn.execute("SELECT MAX(version) FROM models").fetchone()
            next_version = (row[0] or 0) + 1

            trained_at = datetime.now().isoformat()

            conn.execute("""
                INSERT INTO models (version, path, accuracy, f1_score, trained_at, is_active)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (next_version, path, accuracy, f1_score, trained_at))
            conn.commit()

        return ModelRecord(
            version=next_version,
            path=path,
            accuracy=accuracy,
            f1_score=f1_score,
            trained_at=trained_at,
            is_active=False
        )

    def set_active(self, version: int):
        """
        Marks one model as active, clears the flag on all others.
        Only one model can be active at a time — this is the one the pipeline uses.
        """
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("UPDATE models SET is_active = 0")           # clear everyone
            conn.execute("UPDATE models SET is_active = 1 WHERE version = ?", (version,))
            conn.commit()

    def get_active(self) -> ModelRecord | None:
        """
        Returns the currently active model, or None if nothing is active yet.
        """
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute("""
                SELECT version, path, accuracy, f1_score, trained_at, is_active
                FROM models WHERE is_active = 1
            """).fetchone()

        if row is None:
            return None
        return ModelRecord(*row)

    def get_all(self) -> list[ModelRecord]:
        """
        Returns every model ever registered, ordered by version ascending.
        Useful for seeing the full history.
        """
        with closing(sqlite3.connect(self.db_path)) as conn:
            rows = conn.execute("""
                SELECT version, path, accuracy, f1_score, trained_at, is_active
                FROM models ORDER BY version ASC
            """).fetchall()
        return [ModelRecord(*row) for row in rows]

    def get_by_version(self, version: int) -> ModelRecord | None:
        """
        Fetch a specific version by number. Used during rollback.
        """
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute("""
                SELECT version, path, accuracy, f1_score, trained_at, is_active
                FROM models WHERE version = ?
            """, (version,)).fetchone()
        if row is None:
            return None
        return ModelRecord(*row)

    def get_next_version(self) -> int:
        """
        Returns the version number that the NEXT register() call will assign.
        Used by Retrainer to compute the correct file path BEFORE registering,
        so every model — promoted or rejected — gets a unique file on disk.
        """
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute("SELECT MAX(version) FROM models").fetchone()
            return (row[0] or 0) + 1