import threading
from typing import Callable, Optional

from .errors import CancelledError
from .events import JobEvent


class Context:
    """도구가 UI/러너와 통신하는 유일한 통로."""

    def __init__(self, emit: Callable[[JobEvent], None],
                 cancel_event: threading.Event,
                 confirm_handler: Callable[[str], bool]):
        self._emit = emit
        self._cancel = cancel_event
        self._confirm = confirm_handler

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def check_cancel(self) -> None:
        if self._cancel.is_set():
            raise CancelledError()

    def sleep(self, seconds: float) -> None:
        """취소되면 즉시 깨어나 CancelledError를 던지는 sleep."""
        if self._cancel.wait(seconds):
            raise CancelledError()

    def log(self, message: str) -> None:
        self._emit(JobEvent("log", message))

    def progress(self, percent: Optional[int] = None, text: str = "") -> None:
        """percent: 0~100, 알 수 없으면 None."""
        self._emit(JobEvent("progress", (percent, text)))

    def confirm(self, message: str) -> bool:
        """작업 중 사용자 확인(예/아니오). 유일하게 허용되는 중간 입력."""
        return self._confirm(message)
