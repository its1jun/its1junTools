from typing import Optional

from rich.cells import cell_len, set_cell_size
from rich.text import Text
from textual.widget import Widget

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
RULE = "═"
RULE_LEAD = 3   # 줄 앞쪽 이중선 개수 (고정)
RULE_TAIL = 3   # 줄 맨 끝 이중선 개수 (고정, 메시지가 길어도 항상 남는다)
PAD = 1         # 상태 문구 양옆 공백 개수


class StatusBar(Widget):
    """이중선 줄 자체가 상태줄이다: '═══ 메시지 ⠋ (50%) ═════…'.

    busy 이면 스피너가 돈다. 메시지가 길면 메시지만 '…' 로 줄이고 스피너/퍼센트는 남긴다.
    """

    def __init__(self, ready_text: str, **kwargs):
        super().__init__(**kwargs)
        self.ready_text = ready_text
        self.msg = ready_text
        self.percent: Optional[int] = None
        self.busy = False
        self._spin = 0
        self._flash_timer = None

    def on_mount(self) -> None:
        self.set_interval(0.5, self._tick)

    def _tick(self) -> None:
        if self.busy:
            self._spin = (self._spin + 1) % len(SPINNER_FRAMES)
            self.refresh()

    def render(self) -> Text:
        width = self.size.width
        suffix = ""
        if self.busy:
            suffix += f" {SPINNER_FRAMES[self._spin]}"
        if self.percent is not None:
            suffix += f" ({self.percent}%)"
        pad = " " * PAD
        msg = self.msg
        room = width - RULE_LEAD - RULE_TAIL - 2 * PAD - cell_len(suffix)
        if room < 1:
            msg = ""
        elif cell_len(msg) > room:
            msg = set_cell_size(msg, max(0, room - 1)).rstrip() + "…"
        label = pad + msg + suffix + pad
        fill = max(0, width - RULE_LEAD - RULE_TAIL - cell_len(label))
        return Text(RULE * RULE_LEAD + label + RULE * (fill + RULE_TAIL), no_wrap=True, overflow="crop")

    def show(self, msg: str, percent: Optional[int] = None, busy: bool = False) -> None:
        self._stop_flash()
        self.msg, self.percent, self.busy = msg, percent, busy
        self.refresh()

    def reset(self) -> None:
        self.show(self.ready_text)

    def flash(self, msg: str, duration: float = 2.0) -> None:
        """잠깐 msg를 보여주고 Ready로 되돌린다 (busy 중에는 무시)."""
        if self.busy:
            return
        self._stop_flash()
        self.msg, self.percent = msg, None
        self.refresh()
        self._flash_timer = self.set_timer(duration, self._end_flash)

    def _end_flash(self) -> None:
        self._flash_timer = None
        if not self.busy:
            self.msg, self.percent = self.ready_text, None
            self.refresh()

    def _stop_flash(self) -> None:
        if self._flash_timer is not None:
            self._flash_timer.stop()
            self._flash_timer = None
