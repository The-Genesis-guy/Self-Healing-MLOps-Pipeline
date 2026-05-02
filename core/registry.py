import sqlite3
import os
import json
from datetime import datetime
from dataclasses import dataclass
from contextlib import closing
from typing import Optional

# Path to the SQLite database file
DB_PATH = "models/registry.db"

@dataclass
class ModelRecord:
    """One row in the registry — represents a single trained model version."""
    version: int
    path: str
    f1_score: float
    trained_at: str
    is_active: bool
    feature_importance: Optional[dict] = None

class ModelRegistry:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        # Make sure the models/ directory exists before we try to create the DB inside it
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Creates the models table if it doesn't exist yet."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    version     INTEGER PRIMARY KEY,
                    path        TEXT NOT NULL,
                    accuracy    REAL NOT NULL DEFAULT 0.0,
                    f1_score    REAL NOT NULL,
                    trained_at  TEXT NOT NULL,
                    is_active   INTEGER NOT NULL DEFAULT 0,
                    feature_importance TEXT
                )
            """)
            
            # Migration: Add feature_importance column if it doesn't exist
            try:
                conn.execute("ALTER TABLE models ADD COLUMN feature_importance TEXT")
            except sqlite3.OperationalError:
                pass # Already exists
                
            conn.commit()

    def register(self, path: str, f1_score: float, feature_importance: dict = None) -> ModelRecord:
        """Saves a new model to the registry with its explainability data."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute("SELECT MAX(version) FROM models").fetchone()
            next_version = (row[0] or 0) + 1
            trained_at = datetime.now().isoformat()
            
            importance_json = json.dumps(feature_importance) if feature_importance else None

            conn.execute("""
                INSERT INTO models (version, path, accuracy, f1_score, trained_at, is_active, feature_importance)
                VALUES (?, ?, 0.0, ?, ?, 0, ?)
            """, (next_version, path, f1_score, trained_at, importance_json))
            conn.commit()

        return ModelRecord(
            version=next_version,
            path=path,
            f1_score=f1_score,
            trained_at=trained_at,
            is_active=False,
            feature_importance=feature_importance
        )

    def set_active(self, version: int):
        """Marks one model as active, clears the flag on all others."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("UPDATE models SET is_active = 0")
            conn.execute("UPDATE models SET is_active = 1 WHERE version = ?", (version,))
            conn.commit()

    def _row_to_record(self, row) -> ModelRecord:
        """Helper to convert a DB row into a ModelRecord with JSON parsing."""
        if row is None: return None
        # row: (version, path, f1_score, trained_at, is_active, feature_importance)
        importance = json.loads(row[5]) if row[5] else None
        return ModelRecord(
            version=row[0],
            path=row[1],
            f1_score=row[2],
            trained_at=row[3],
            is_active=bool(row[4]),
            feature_importance=importance
        )

    def get_active(self) -> Optional[ModelRecord]:
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute("""
                SELECT version, path, f1_score, trained_at, is_active, feature_importance
                FROM models WHERE is_active = 1
            """).fetchone()
        return self._row_to_record(row)

    def get_all(self) -> list[ModelRecord]:
        with closing(sqlite3.connect(self.db_path)) as conn:
            rows = conn.execute("""
                SELECT version, path, f1_score, trained_at, is_active, feature_importance
                FROM models ORDER BY version ASC
            """).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get_by_version(self, version: int) -> Optional[ModelRecord]:
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute("""
                SELECT version, path, f1_score, trained_at, is_active, feature_importance
                FROM models WHERE version = ?
            """, (version,)).fetchone()
        return self._row_to_record(row)

    def get_next_version(self) -> int:
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute("SELECT MAX(version) FROM models").fetchone()
            return (row[0] or 0) + 1