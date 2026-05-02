import sqlite3
import os
from datetime import datetime
from contextlib import closing
from dataclasses import dataclass

@dataclass
class HistoryEntry:
    id: int
    timestamp: str
    iteration: int
    model_version: int
    f1_score: float
    drift_score: float
    action: str
    reason: str

class HistoryLogger:
    """
    Persistent storage for pipeline iterations. 
    Powers the 'Performance Over Time' charts and 'Event Logs' on the dashboard.
    """
    def __init__(self, db_path: str = "models/history.db"):
        self.db_path = db_path
        # Ensure the models directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Creates the history table if it doesn't exist."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT NOT NULL,
                    iteration       INTEGER NOT NULL,
                    model_version   INTEGER,
                    f1_score        REAL,
                    drift_score     REAL,
                    action          TEXT,
                    reason          TEXT
                )
            """)
            conn.commit()

    def log(self, iteration: int, version: int, f1: float, drift: float, action: str, reason: str):
        """Saves a single iteration's snapshot to the database."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO history (
                    timestamp, iteration, model_version, f1_score, drift_score, action, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), iteration, version, f1, drift, action, reason))
            conn.commit()

    def get_recent(self, limit: int = 100) -> list[HistoryEntry]:
        """Returns the most recent iterations for the dashboard charts."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM history ORDER BY iteration DESC LIMIT ?
            """, (limit,)).fetchall()
            
            # Convert to list of dataclasses for clean API usage
            return [HistoryEntry(**dict(row)) for row in rows]
