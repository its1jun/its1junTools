from rich.cells import cell_len
from textual import events

from ui.keymap import ACTION_ENTER, is_key_for
from ui.platform_utils import force_ime_english
from .base import FieldWidget

MAX_EDIT_LEN = 500


class InputField(FieldWidget):
    TYPE = "input"

    def __init__(self, spec):
        super().__init__(spec)
        self._value = spec.default or ""
        self.editing = False
        self._buf: list = []
        self._cursor = True

    @property
    def value(self) -> str:
        return self._value

    def on_mount(self) -> None:
        self.set_interval(0.5, self._blink)

    def _blink(self) -> None:
        if self.editing:
            self._cursor = not self._cursor
            self.refresh()

    def render(self):
        if self.editing:
            raw = "".join(self._buf)
            inner = max(1, self.size.width - 4)
            while cell_len(raw) > inner - 1 and raw:   # 길면 끝부분만 보여줌
                raw = raw[1:]
            return self.boxed(raw + ("|" if self._cursor else " "), hot=True)
        if self._value:
            return self.boxed(self._value)
        return self.boxed(self.spec.placeholder, dim=bool(self.spec.placeholder))

    def activate(self) -> None:
        self.editing = True
        self._buf = []
        self._cursor = True
        self.refresh()

    def press(self) -> None:
        """ENTER 와 동일: 편집 중이면 확정, 아니면 편집 시작."""
        if self.editing:
            self._stop(True)
        else:
            self.activate()

    def on_blur(self) -> None:
        super().on_blur()
        if self.editing:   # 마우스로 다른 필드를 누르면 입력 중인 값을 확정
            self._stop(True)

    def _stop(self, commit: bool) -> None:
        if commit:
            self._value = "".join(self._buf).strip()
        else:
            self._value = ""   # 기존 동작 유지: ESC 는 값을 비운다
        self.editing = False
        self._buf = []
        self.refresh()
        force_ime_english()   # 편집이 끝나는 순간 1회: 한글 입력 상태를 영문으로 복귀 (타이머 폴링 대신)
        self.post_message(self.Changed(self))

    def on_key(self, event: events.Key) -> None:
        if not self.editing:
            super().on_key(event)
            return
        event.stop()
        event.prevent_default()
        if is_key_for(event.key, ACTION_ENTER):
            self._stop(True)
        elif event.key == "escape":
            self._stop(False)
        elif event.key == "backspace":
            if self._buf:
                self._buf.pop()
            self._cursor = True
            self.refresh()
        elif event.character and event.character.isprintable() and len(self._buf) < MAX_EDIT_LEN:
            self._buf.append(event.character)
            self._cursor = True
            self.refresh()

    def on_paste(self, event: events.Paste) -> None:
        if not self.editing:
            return
        event.stop()
        pasted = "".join(ch for ch in event.text if ch.isprintable())
        room = MAX_EDIT_LEN - len(self._buf)
        if room > 0 and pasted:
            self._buf.extend(pasted[:room])
            self.refresh()
