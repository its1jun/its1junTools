from collections import deque
from itertools import islice

MAX_LOG_RETENTION = 500


class LogBuffer:
    def __init__(self):
        self.lines = deque(maxlen=MAX_LOG_RETENTION)
        self.total_logged = 0   # maxlen을 넘어도 계속 증가

    def log(self, msg: str) -> None:
        self.lines.append(msg)
        self.total_logged += 1

    def clear(self) -> None:
        self.lines.clear()
        self.total_logged = 0

    def as_text(self) -> str:
        return "\n".join(self.lines) if self.lines else "No log entries yet."

    def slice(self, start: int, end: int) -> list:
        if start >= len(self.lines):
            return []
        return list(islice(self.lines, start, end))
