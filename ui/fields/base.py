"""필드 위젯 공통 베이스. 새 필드 = 이 클래스를 상속 + fields/__init__.py 에 1줄 등록."""
from rich.cells import cell_len, set_cell_size
from rich.text import Text
from textual import events
from textual.message import Message
from textual.widget import Widget

from ui.keymap import ACTION_ENTER, is_key_for


def center_cells(s: str, width: int) -> str:
    """터미널 셀 폭(한글=2칸) 기준으로 자르고 가운데 정렬."""
    if cell_len(s) > width:
        s = set_cell_size(s, width).rstrip()
    pad = width - cell_len(s)
    left = pad // 2
    return " " * left + s + " " * (pad - left)


class FieldWidget(Widget, can_focus=True):
    TYPE = ""
    IS_VALUE = True    # False 이면 config 값에 포함되지 않음 (버튼)

    class Changed(Message):
        def __init__(self, field: "FieldWidget"):
            super().__init__()
            self.field = field

    class Submit(Message):
        def __init__(self, field: "FieldWidget"):
            super().__init__()
            self.field = field

    class Browse(Message):
        def __init__(self, field: "FieldWidget"):
            super().__init__()
            self.field = field

    def __init__(self, spec):
        super().__init__(classes="field-box")
        self.spec = spec

    @property
    def key(self) -> str:
        return self.spec.key

    @property
    def value(self) -> str:
        return ""

    def on_focus(self) -> None:
        self.refresh()
        if self.parent is not None:
            self.parent.scroll_visible(animate=False)   # 라벨까지 포함해서 화면에 보이게

    def on_blur(self) -> None:
        self.refresh()

    def boxed(self, content: str, hot: bool = False, dim: bool = False) -> Text:
        """'[ 내용 ]' 형태. 포커스(hot)이면 내용 부분만 black on white."""
        inner = max(1, self.size.width - 4)
        body = center_cells(content, inner)
        style = "black on white" if (self.has_focus or hot) else ("grey58" if dim else None)
        t = Text("[ ")
        t.append(body, style=style)
        t.append(" ]")
        return t

    def on_key(self, event) -> None:
        if is_key_for(event.key, ACTION_ENTER):
            event.stop()
            self.activate()

    def on_click(self, event: events.Click) -> None:
        """마우스 좌클릭 = 포커스 + ENTER. (우클릭/휠클릭은 무시)"""
        if event.button != 1:
            return
        event.stop()
        self.focus()
        self.press()

    def press(self) -> None:
        """ENTER 또는 좌클릭에 해당하는 동작. 기본은 activate()."""
        self.activate()

    def activate(self) -> None:
        """Enter 가 눌렸을 때의 동작. 서브클래스에서 구현."""
