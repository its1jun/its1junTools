"""로그 화면 (모달). 스크롤(↑/↓, 마우스 휠) / 저장 / 로그 폴더 열기."""
import os
from datetime import datetime

from textual import events
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Static

from core import LogBuffer
from ui.keymap import (
    ACTION_CLOSE, ACTION_DOWN, ACTION_OPEN_OUTPUT_DIR, ACTION_SAVE_LOG, ACTION_UP,
    action_label, is_key_for, key_label, keys_for,
)
from ui.platform_utils import get_project_subdir, open_in_explorer
from ui.widgets.flash_line import FlashLine

VISIBLE_ROWS = 16
WHEEL_STEP = 3   # 마우스 휠 한 칸당 이동 줄 수
LOG_DIR_NAME = "Logs"


class LogScreen(Screen[None]):
    def __init__(self, log_buffer: LogBuffer):
        super().__init__()
        self.log_buffer = log_buffer
        self._offset = 0          # 화면 맨 위에 보이는 로그 줄 번호
        self._last_count = 0
        self._last_len = 0
        self._last_body = None

    def compose(self):
        with Container(id="log-box"):
            yield Static("", id="log-content", markup=False)
        yield FlashLine("", id="log-controls")   # 박스 밖(아래)

    def on_mount(self) -> None:
        self.query_one("#log-box").border_title = "SYSTEM DEBUG LOGS"
        self._offset = self._max_offset()   # 처음엔 맨 아래(최신 로그)
        self._last_count = self.log_buffer.total_logged
        self._last_len = len(self.log_buffer.lines)
        self._render_page()
        self.set_interval(0.3, self._check_new_logs)

    def _max_offset(self) -> int:
        return max(0, len(self.log_buffer.lines) - VISIBLE_ROWS)

    def _scroll(self, delta: int) -> None:
        self._offset += delta
        self._render_page()

    def _controls_text(self) -> str:
        close_keys = tuple(k for k in keys_for(ACTION_CLOSE) if k != "slash")
        total = len(self.log_buffer.lines)
        first = min(self._offset + 1, total)
        last = min(self._offset + VISIBLE_ROWS, total)
        return (
            f"Controls: [{action_label(ACTION_UP, ACTION_DOWN)}/Wheel] Scroll "
            f"({first}-{last}/{total}) | [{key_label(close_keys)}] Close\n"
            f"          [{action_label(ACTION_SAVE_LOG)}] Save Log | "
            f"[{action_label(ACTION_OPEN_OUTPUT_DIR)}] Open Log Dir"
        )

    def _render_page(self) -> None:
        self._offset = max(0, min(self._offset, self._max_offset()))
        if not self.log_buffer.lines:
            rows = ["No log entries yet."]
        else:
            rows = self.log_buffer.slice(self._offset, self._offset + VISIBLE_ROWS)
        body = "\n".join(rows + [""] * (VISIBLE_ROWS - len(rows)))
        if body != self._last_body:
            self._last_body = body
            self.query_one("#log-content", Static).update(body)
        self.query_one("#log-controls", FlashLine).set_base(self._controls_text())

    def _check_new_logs(self) -> None:
        count = self.log_buffer.total_logged
        if count == self._last_count:
            return
        length = len(self.log_buffer.lines)
        was_bottom = self._offset >= max(0, self._last_len - VISIBLE_ROWS)
        dropped = (count - self._last_count) - (length - self._last_len)   # 보관 한도(500)를 넘어 밀려난 줄 수
        self._last_count, self._last_len = count, length
        if was_bottom:
            self._offset = self._max_offset()      # 맨 아래를 보고 있었으면 새 로그를 따라간다
        else:
            self._offset -= max(0, dropped)        # 위쪽을 보고 있으면 같은 내용을 계속 보여준다
        self._render_page()

    def _flash(self, msg: str) -> None:
        self.query_one("#log-controls", FlashLine).flash(msg)

    def _save(self) -> None:
        if not self.log_buffer.lines:
            self._flash("Nothing to save: log is empty")
            return
        log_dir = get_project_subdir(LOG_DIR_NAME)
        os.makedirs(log_dir, exist_ok=True)
        name = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = os.path.join(log_dir, name)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log_buffer.as_text())
        except Exception as e:
            self._flash(f"Save failed: {e}")
            return
        self.log_buffer.log(f"[INFO] Log saved: {path}")
        self._flash(f"Saved: {name}")

    def _open_log_dir(self) -> None:
        log_dir = get_project_subdir(LOG_DIR_NAME)
        if not os.path.isdir(log_dir):
            self._flash("Error: log folder not found (nothing saved yet)")
            return
        ok = open_in_explorer(log_dir)
        self._flash(f"Opened: {log_dir}" if ok else f"Could not open file explorer. Path: {log_dir}")

    def on_key(self, event: events.Key) -> None:
        key = event.key
        event.stop()
        event.prevent_default()
        if is_key_for(key, ACTION_UP):
            self._scroll(-1)
        elif is_key_for(key, ACTION_DOWN):
            self._scroll(1)
        elif is_key_for(key, ACTION_CLOSE):
            self.dismiss(None)
        elif is_key_for(key, ACTION_SAVE_LOG):
            self._save()
        elif is_key_for(key, ACTION_OPEN_OUTPUT_DIR):
            self._open_log_dir()

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        event.stop()
        self._scroll(-WHEEL_STEP)

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        event.stop()
        self._scroll(WHEEL_STEP)
