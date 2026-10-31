from dataclasses import dataclass
from enum import Enum
from typing import Any


class JobState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobEvent:
    kind: str        # "log" | "progress" | "error" | "state"
    data: Any = None  # log: str / progress: (percent|None, str) / error: str / state: JobState
