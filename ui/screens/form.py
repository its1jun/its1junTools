"""도구 화면: 필드 폼 + 상태줄 + 안내줄. 실행/취소/로그/출력폴더를 여기서 연결한다."""
import os
import threading

from textual import events
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Label, Static

from core import Field, JobEvent, JobState, LogBuffer
from runner import Runner
from ui.defaults import (
    DEFAULT_BUTTON_LABEL, DEFAULT_STATUS_CANCELLED_TEXT, DEFAULT_STATUS_CANCELLING_TEXT,
    DEFAULT_STATUS_DONE_TEXT, DEFAULT_STATUS_ERROR_PREFIX, DEFAULT_STATUS_READY_TEXT,
    DEFAULT_STATUS_RUNNING_TEXT, DEFAULT_STATUS_TEXT_MAX_LEN, text,
)
from ui.fields import FieldWidget, create_field
from ui.keymap import (
    ACTION_OPEN_LOGS, ACTION_OPEN_OUTPUT_DIR, ACTION_QUIT, ACTION_TAB, DIRECTION_ACTIONS, DIRECTION_DELTA, action_for_key, is_key_for,
)
from ui.platform_utils import get_project_subdir, open_in_explorer, pick_files_native
from ui.widgets.controls_bar import ControlsBar
from ui.widgets.status_bar import StatusBar

MAX_FIELDS_PER_ROW = 2


class FieldsScroll(VerticalScroll, can_focus=False):
    """필드 영역 스크롤 컨테이너. 포커스는 필드가 갖고, 스크롤은 필드 포커스를 따라간다."""


class FieldLabel(Label):
    """필드 이름. 좌클릭하면 해당 필드를 누른 것(포커스 + ENTER)과 같다."""

    def __init__(self, target: FieldWidget):
        super().__init__(target.spec.label, classes="field-label", markup=False)
        self._target = target

    def on_click(self, event: events.Click) -> None:
        if event.button == 1:
            event.stop()
            self._target.focus()
            self._target.press()


class FormScreen(Screen):
    def __init__(self, tool, standalone: bool = False):
        super().__init__()
        self.tool = tool
        self.standalone = standalone   # True: 전용 새 창 (ESC/Q 가 '뒤로'가 아니라 '창 닫기')
        self.log_buffer = LogBuffer()
        self.runner = None
        self._browsing = False     # 파일 대화상자가 열려 있는 동안 True

        self._ready_text = text(tool, "STATUS_READY_TEXT", DEFAULT_STATUS_READY_TEXT)
        self.status_bar = StatusBar(self._ready_text, id="status-line")
        self.controls_bar = ControlsBar(tool, tool.output_dir_name is not None, standalone, id="controls-line")

        self._grid: list = []      # [[FieldWidget, ...], ...]  줄 단위
        self._flat: list = []
        self._pos: dict = {}       # widget -> (row, col)
        for r, specs in enumerate(self._normalize_rows(tool)):
            row = [create_field(s) for s in specs]
            for c, w in enumerate(row):
                self._pos[w] = (r, c)
                self._flat.append(w)
            self._grid.append(row)

    @staticmethod
    def _normalize_rows(tool) -> list:
        rows = []
        for item in tool.fields:
            items = item if isinstance(item, list) else [item]
            for i in range(0, len(items), MAX_FIELDS_PER_ROW):
                rows.append(items[i:i + MAX_FIELDS_PER_ROW])
        if not any(f.type == "button" for row in rows for f in row):
            rows.append([Field("run", "button", tool.run_label or DEFAULT_BUTTON_LABEL)])
        return rows

    # ------------------------------------------------------------------ 구성
    def compose(self):
        # 제목 / 상태줄 / 안내줄은 고정, 필드 영역(fields-slot)만 스크롤
        with Container(id="main-panel", classes="pinned"):
            yield Static(self.tool.name.upper(), id="title-bar", markup=False)
            with FieldsScroll(id="fields-slot"):
                for row in self._grid:
                    yield from self._compose_row(row)
            yield self.status_bar
            yield self.controls_bar

    @staticmethod
    def _compose_row(row):
        if len(row) == 1:
            w = row[0]
            if w.IS_VALUE:
                # 라벨+필드를 한 덩어리로 묶는다 (스크롤 시 라벨이 같이 보이게)
                yield Vertical(FieldLabel(w), w, classes="inline-field")
            else:
                yield Horizontal(w, classes="run-row")
        else:
            cols = [
                Vertical(FieldLabel(w) if w.IS_VALUE else Label("", classes="field-label"),
                         w, classes="inline-field")
                for w in row
            ]
            yield Horizontal(*cols, classes="inline-row")

    def on_mount(self) -> None:
        self.runner = Runner(dispatch=self.app.call_from_thread)
        self._sync_dependents(None)
        if self._flat:
            self._flat[0].focus()

    def on_unmount(self) -> None:
        if self.runner is not None:
            self.runner.cancel()

    # ------------------------------------------------------------------ 동적 옵션
    def _values(self) -> dict:
        return {w.key: w.value for w in self._flat if w.IS_VALUE}

    def _sync_dependents(self, source_key, _depth: int = 0) -> None:
        if _depth > 5:
            return
        values = self._values()
        for w in self._flat:
            dep = w.spec.depends_on
            if dep and (source_key is None or dep == source_key) and hasattr(w, "apply_dependency"):
                if w.apply_dependency(values.get(dep)):
                    self._sync_dependents(w.key, _depth + 1)

    # ------------------------------------------------------------------ 필드 메시지
    def on_field_widget_changed(self, event: FieldWidget.Changed) -> None:
        event.stop()
        self._sync_dependents(event.field.key)
        if event.field.TYPE == "cycle":
            self.status_bar.flash(f"Option set to {event.field.value}")

    def on_field_widget_browse(self, event: FieldWidget.Browse) -> None:
        event.stop()
        if self._browsing:
            return
        widget = event.field
        multi = widget.spec.multi
        current = widget.paths
        start = os.path.dirname(current[0]) if current else os.path.expanduser("~")
        allowed_ext = self.tool.allowed_ext

        def work() -> None:   # 워커 스레드: 대화상자가 닫힐 때까지 대기
            ok, paths = pick_files_native(start, allowed_ext, multi)
            self.app.call_from_thread(done, ok, paths)

        def done(ok: bool, paths: list) -> None:   # UI 스레드
            self._browsing = False
            self.status_bar.reset()   # busy 해제 (busy 중에는 flash 가 무시됨)
            if not ok:
                self.status_bar.flash("Could not open file dialog (tkinter required)", duration=4.0)
            elif paths:   # 취소하면 기존 선택 유지
                widget.set_value(paths)
                if multi:
                    self.log_buffer.log(f"[INFO] Files selected ({len(paths)})")
                    for p in paths:
                        self.log_buffer.log(f"[INFO]   {p}")
                else:
                    self.log_buffer.log(f"[INFO] File selected: {paths[0]}")

        self._browsing = True
        self.status_bar.show("Waiting for file dialog", busy=True)
        self.run_worker(work, thread=True)

    def on_field_widget_submit(self, event: FieldWidget.Submit) -> None:
        event.stop()
        self._run(event.field.key)

    # ------------------------------------------------------------------ 실행
    def _run(self, pressed: str) -> None:
        if self.runner.is_running:
            return
        if self.tool.run is None:
            self.status_bar.flash("This tool has no run action")
            return
        config = self._values()
        config["_pressed"] = pressed
        self.log_buffer.log(f"[INFO] Run: {pressed}")
        self.runner.start(self.tool, config, self._on_job_event, self._confirm)

    def _confirm(self, message: str) -> bool:
        """워커 스레드에서 호출됨. UI 스레드에서 모달을 띄우고 답이 올 때까지 대기."""
        done = threading.Event()
        box = [False]

        def ask():
            def answered(result):
                box[0] = bool(result)
                done.set()
            self.app.open_screen("confirm", message, callback=answered)

        self.app.call_from_thread(ask)
        done.wait()
        return box[0]

    def _short(self, s: str) -> str:
        s = s.strip()
        limit = text(self.tool, "STATUS_TEXT_MAX_LEN", DEFAULT_STATUS_TEXT_MAX_LEN)
        return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"

    def _on_job_event(self, ev: JobEvent) -> None:
        """UI 스레드에서 실행됨."""
        if ev.kind == "log":
            self.log_buffer.log(ev.data)
        elif ev.kind == "progress":
            percent, msg = ev.data
            if percent is not None:
                self.log_buffer.log(f"[PROGRESS] {percent}% - {msg}" if msg else f"[PROGRESS] {percent}%")
            else:
                self.log_buffer.log(f"[PROGRESS] {msg}")
            running = text(self.tool, "STATUS_RUNNING_TEXT", DEFAULT_STATUS_RUNNING_TEXT)
            self.status_bar.show(self._short(msg) if msg else running, percent=percent, busy=True)
        elif ev.kind == "error":
            prefix = text(self.tool, "STATUS_ERROR_PREFIX", DEFAULT_STATUS_ERROR_PREFIX)
            self.status_bar.show(f"{prefix}{self._short(ev.data)}")
        elif ev.kind == "state":
            state = ev.data
            if state == JobState.RUNNING:
                self.status_bar.show(text(self.tool, "STATUS_RUNNING_TEXT", DEFAULT_STATUS_RUNNING_TEXT), busy=True)
                self.controls_bar.set_running(True)
            else:
                self.controls_bar.set_running(False)
                if state == JobState.COMPLETED:
                    self.status_bar.show(text(self.tool, "STATUS_DONE_TEXT", DEFAULT_STATUS_DONE_TEXT))
                elif state == JobState.CANCELLED:
                    self.status_bar.show(text(self.tool, "STATUS_CANCELLED_TEXT", DEFAULT_STATUS_CANCELLED_TEXT))
                # FAILED 는 직전 "error" 이벤트가 만든 상태줄을 그대로 둔다

    # ------------------------------------------------------------------ 키 입력
    def on_key(self, event: events.Key) -> None:
        key = event.key

        if is_key_for(key, ACTION_QUIT):
            event.stop()
            if self.runner.is_running:
                self.runner.cancel()
                self.status_bar.show(
                    text(self.tool, "STATUS_CANCELLING_TEXT", DEFAULT_STATUS_CANCELLING_TEXT), busy=True)
            else:
                self.app.go_back()
            return

        if is_key_for(key, ACTION_OPEN_LOGS):
            event.stop()
            self.app.open_screen("log", self.log_buffer)
            return

        if is_key_for(key, ACTION_OPEN_OUTPUT_DIR):
            event.stop()
            self._open_output_dir()
            return

        if is_key_for(key, ACTION_TAB):
            event.stop()
            self._focus_index((self._flat.index(self.focused) + 1) % len(self._flat)
                              if self.focused in self._pos else 0)
            return

        direction = action_for_key(key, DIRECTION_ACTIONS)
        if direction is not None:
            event.stop()
            self._move_focus(direction)

    def _focus_index(self, idx: int) -> None:
        if self._flat:
            self._flat[idx].focus()

    def _move_focus(self, direction: str) -> None:
        cur = self.focused
        if cur not in self._pos:
            self._focus_index(0)
            return
        r, c = self._pos[cur]
        dr, dc = DIRECTION_DELTA[direction]
        tr, tc = r + dr, c + dc
        if not (0 <= tr < len(self._grid)):
            return
        row = self._grid[tr]
        if dc != 0 and not (0 <= tc < len(row)):
            return
        if not (0 <= tc < len(row)):   # 위/아래 이동 시 칸이 없으면 첫 칸
            tc = 0
        row[tc].focus()

    def _open_output_dir(self) -> None:
        name = self.tool.output_dir_name
        if not name:
            return
        path = get_project_subdir(name)
        os.makedirs(path, exist_ok=True)
        ok = open_in_explorer(path)
        self.log_buffer.log(f"[INFO] Output dir: {path}")
        self.status_bar.flash(f"Opened {path}" if ok else f"Could not open file explorer. Path {path}",
                              duration=2.0 if ok else 4.0)
