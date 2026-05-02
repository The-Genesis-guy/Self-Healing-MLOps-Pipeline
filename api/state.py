# thread-safe shared state

import threading
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PipelineState:
    """Thread-safe container for live pipeline state."""
    running: bool = False
    iteration: int = 0
    last_action: str = "none"
    last_reason: str = ""
    last_drifted_features: list = field(default_factory=list)
    active_model_version: Optional[int] = None
    active_model_f1: Optional[float] = None
    shadow_model_version: Optional[int] = None
    health: str = "healthy"  # "healthy" | "warning" | "critical"
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def update(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "running": self.running,
                "iteration": self.iteration,
                "last_action": self.last_action,
                "last_reason": self.last_reason,
                "last_drifted_features": self.last_drifted_features,
                "active_model_version": self.active_model_version,
                "active_model_f1": self.active_model_f1,
                "health": self.health,
            }

# Single global instance — imported by routes and runner
pipeline_state = PipelineState()
