"""작업 실행/취소/이벤트 전달. Textual을 모른다.

dispatch(fn, *args): 워커 스레드 -> UI 스레드로 호출을 넘기는 함수
                     (UI에서는 app.call_from_thread 를 넘긴다)
"""
import threading
import time
import traceback
from typing import Callable, Optional

from core import CancelledError, Context, JobEvent, JobState, Tool

PROGRESS_INTERVAL = 0.05   # progress 이벤트는 최대 20Hz, 최신값만 유지


class Runner:
    def __init__(self, dispatch: Callable):
        self._dispatch = dispatch
        self._on_event: Optional[Callable[[JobEvent], None]] = None
        self._thread: Optional[threading.Thread] = None
        self._cancel = threading.Event()
        self._running = False
        self._lock = threading.Lock()
        self._pending: Optional[JobEvent] = None
        self._flush_scheduled = False
        self._last_sent = 0.0

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, tool: Tool, config: dict,
              on_event: Callable[[JobEvent], None],
              confirm_handler: Callable[[str], bool]) -> bool:
        """UI 스레드에서 호출. 이미 실행 중이면 False."""
        if self._running:
            return False
        self._cancel = threading.Event()
        self._on_event = on_event
        self._running = True
        self._pending = None
        self._flush_scheduled = False
        ctx = Context(self._emit, self._cancel, confirm_handler)
        on_event(JobEvent("state", JobState.RUNNING))
        self._thread = threading.Thread(target=self._work, args=(tool, config, ctx), daemon=True)
        self._thread.start()
        return True

    def cancel(self) -> None:
        self._cancel.set()

    # ---- 워커 스레드 ----
    def _work(self, tool: Tool, config: dict, ctx: Context) -> None:
        final = JobState.COMPLETED
        try:
            if tool.run is None:
                raise RuntimeError("This tool has no run() function")
            tool.run(config, ctx)
            if self._cancel.is_set():
                final = JobState.CANCELLED
        except CancelledError:
            final = JobState.CANCELLED
        except Exception as e:
            final = JobState.FAILED
            self._send(JobEvent("log", f"[ERROR] {type(e).__name__}: {e}"))
            self._send(JobEvent("log", traceback.format_exc()))
            self._send(JobEvent("error", str(e) or type(e).__name__))
        finally:
            self._running = False
            self._flush()   # 마지막 progress가 지연 대기 중이면 먼저 내보낸다
            self._send(JobEvent("state", final))

    def _emit(self, event: JobEvent) -> None:
        if event.kind != "progress":
            self._send(event)
            return
        now = time.monotonic()
        action, to_send, delay = None, None, 0.0
        with self._lock:
            self._pending = event
            elapsed = now - self._last_sent
            if elapsed >= PROGRESS_INTERVAL:
                self._last_sent = now
                to_send, self._pending = self._pending, None
                action = "send"
            elif not self._flush_scheduled:
                self._flush_scheduled = True
                delay = PROGRESS_INTERVAL - elapsed
                action = "schedule"
        if action == "send":
            self._send(to_send)
        elif action == "schedule":
            t = threading.Timer(delay, self._flush)
            t.daemon = True
            t.start()

    def _flush(self) -> None:
        with self._lock:
            self._flush_scheduled = False
            ev, self._pending = self._pending, None
            if ev is not None:
                self._last_sent = time.monotonic()
        if ev is not None:
            self._send(ev)

    def _send(self, event: JobEvent) -> None:
        try:
            self._dispatch(self._on_event, event)
        except Exception:
            pass   # 앱이 이미 종료된 경우
