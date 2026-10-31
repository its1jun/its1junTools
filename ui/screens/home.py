"""Home 화면: 도구 목록 선택."""
from rich.text import Text
from textual import events
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from ui.defaults import DEFAULT_STATUS_READY_TEXT, DEFAULT_TOOL_SELECTOR_TITLE
from ui.keymap import (
    ACTION_DOWN, ACTION_ENTER, ACTION_QUIT, ACTION_UP, action_label, is_key_for,
)
from ui.widgets.flash_line import FlashLine
from ui.widgets.status_bar import StatusBar

LIST_PAD = "  "        # 목록 왼쪽 여백
DESC_SEP = " - "         # 도구 이름과 설명 사이 구분
DESC_STYLE = "grey70"       # 설명 색 (회백색)
DESC_STYLE_HL = "grey35"    # 하이라이트된 줄 위의 설명 색 (밝은 배경 위라 어둡게)

CONTROLS = (
    f"Controls: [{action_label(ACTION_UP, ACTION_DOWN)}] Navigate | "
    f"[{action_label(ACTION_ENTER)}] Select | [{action_label(ACTION_QUIT)}] Exit"
)


def _option_prompt(index: int, tool, highlighted: bool) -> Text:
    """'1. 도구 이름 - 도구 설명' 한 줄. 이름은 기본 글자색, 설명(구분 포함)은 회백색. 설명이 없으면 이름만."""
    t = Text(f"{LIST_PAD}{index + 1}. {tool.name}")
    if tool.description:
        t.append(f"{DESC_SEP}{tool.description}", style=DESC_STYLE_HL if highlighted else DESC_STYLE)
    return t


class HomeScreen(Screen):
    def __init__(self):
        super().__init__()
        self._hl = None   # 현재 하이라이트된 인덱스

    def compose(self):
        # 도구 화면(ui/screens/form.py)과 같은 구조: 제목(위) / 상태줄(이중선) / 안내줄(아래)은 고정,
        # 도구 목록만 남는 공간에서 스크롤된다
        with Container(id="main-panel", classes="pinned"):
            yield Static(DEFAULT_TOOL_SELECTOR_TITLE, id="title-bar", markup=False)
            yield OptionList(id="tool-list")
            yield StatusBar(DEFAULT_STATUS_READY_TEXT, id="status-line")
            yield FlashLine(CONTROLS, id="controls-line")

    def on_mount(self) -> None:
        tools = self.app.tools
        lst = self.query_one("#tool-list", OptionList)
        if tools:
            lst.add_options([Option(_option_prompt(i, t, False), id=str(i)) for i, t in enumerate(tools)])
            lst.highlighted = 0
        else:
            lst.add_option(Option(Text("  No tools found in tools/"), disabled=True))
        lst.focus()

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """설명 줄 색은 Text 자체 색이라 CSS 하이라이트가 못 바꾼다 -> 하이라이트가 옮겨질 때 줄을 다시 그린다."""
        event.stop()
        tools = self.app.tools
        lst = self.query_one("#tool-list", OptionList)
        for idx, hl in ((self._hl, False), (event.option_index, True)):
            if idx is not None and 0 <= idx < len(tools):
                lst.replace_option_prompt(str(idx), _option_prompt(idx, tools[idx], hl))
        self._hl = event.option_index

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        tools = self.app.tools
        if 0 <= event.option_index < len(tools):
            tool = tools[event.option_index]
            if self.app.select_tool(tool):   # 새 창으로 열렸으면 홈에 안내만 잠깐 표시
                self.query_one("#status-line", StatusBar).flash(f"Opened in new window: {tool.name}")

    def on_key(self, event: events.Key) -> None:
        if is_key_for(event.key, ACTION_QUIT):
            event.stop()
            self.app.exit()
