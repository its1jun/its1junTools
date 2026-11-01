"""Home 화면: 카테고리를 펼치고 접는 도구 목록. 화면은 1개, 목록도 1개.

  1. Converter+                  <- ENTER: 펼치기 (+) / 접기 (-)
  2. Editor-
    1. Image Edit - ...          <- ENTER: 도구를 새 창으로 열기
    2. Video Edit - ...
──────────────────────────────  <- 카테고리 사이 구분선 (전체 폭, 선택 불가)
  3. Etc                         <- 항상 펼쳐져 있다 (표시 없음, ENTER 로 접히지 않음)
    1. Debug - ...

- 시작할 때 Etc 를 뺀 카테고리는 접혀 있고, 카테고리는 서로 독립적으로 펼치고 접는다.
- ESC/Q: 종료 (홈은 한 단계뿐이다).
"""
from rich.rule import Rule
from rich.text import Text
from textual import events
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from core import CATEGORY_ETC
from registry import group_by_category
from ui.defaults import DEFAULT_STATUS_READY_TEXT, DEFAULT_TOOL_SELECTOR_TITLE
from ui.keymap import (
    ACTION_DOWN, ACTION_ENTER, ACTION_QUIT, ACTION_UP, action_label, is_key_for,
)
from ui.widgets.flash_line import FlashLine
from ui.widgets.status_bar import StatusBar

LIST_PAD = "  "          # 목록 왼쪽 여백
TOOL_PAD = "    "        # 도구 줄 들여쓰기 (카테고리 줄 아래)
MARK_CLOSED = "+"        # 접힌 카테고리 (ASCII: 한글 터미널에서 폭이 흔들리는 기호는 피한다)
MARK_OPEN = "-"          # 펼쳐진 카테고리
DIVIDER_CHAR = "─"       # 카테고리 사이 구분선 (목록 전체 폭, 들여쓰기 없음)
DIVIDER_STYLE = "grey50"
DIVIDER = "divider"      # 줄 종류 표시 (rows 의 두 번째 값)
DESC_SEP = " - "         # 이름과 설명 사이 구분
DESC_STYLE = "grey70"       # 설명 색 (회백색)
DESC_STYLE_HL = "grey35"    # 하이라이트된 줄 위의 설명 색 (밝은 배경 위라 어둡게)

CONTROLS = (
    f"[{action_label(ACTION_UP, ACTION_DOWN)}] Navigate | "
    f"[{action_label(ACTION_ENTER)}] Open/Select | [{action_label(ACTION_QUIT)}] Exit"
)


def _line(pad: str, label: str, extra: str, highlighted: bool) -> Text:
    """'라벨 - 설명' 한 줄. 라벨은 기본 글자색, 설명(구분 포함)은 회백색. 설명이 없으면 라벨만."""
    t = Text(f"{pad}{label}")
    if extra:
        t.append(f"{DESC_SEP}{extra}", style=DESC_STYLE_HL if highlighted else DESC_STYLE)
    return t


def _always_open(name: str) -> bool:
    """Etc 는 항상 펼쳐져 있다 (접기 없음)."""
    return name.strip().casefold() == CATEGORY_ETC.casefold()


class HomeScreen(Screen):
    def __init__(self):
        super().__init__()
        self._groups = []    # [(카테고리 이름, [Tool, ...])] — registry.group_by_category 결과
        self._open = set()   # 사용자가 펼친 카테고리 번호 (항상 펼쳐진 Etc 는 포함하지 않음)
        self._rows = []      # 화면의 줄 목록: (카테고리 번호, None) = 카테고리 줄 / (카테고리 번호, 도구 번호) = 도구 줄
        #                      / (카테고리 번호, DIVIDER) = 그 카테고리 위의 구분선 (선택 불가)
        self._hl = None      # 현재 하이라이트된 줄 번호

    def compose(self):
        # 도구 화면(ui/screens/form.py)과 같은 구조: 제목(위) / 상태줄(이중선) / 안내줄(아래)은 고정,
        # 목록만 남는 공간에서 스크롤된다
        with Container(id="main-panel", classes="pinned"):
            yield Static(DEFAULT_TOOL_SELECTOR_TITLE, id="title-bar", markup=False)
            yield OptionList(id="tool-list")
            yield StatusBar(DEFAULT_STATUS_READY_TEXT, id="status-line")
            yield FlashLine(CONTROLS, id="controls-line")

    def on_mount(self) -> None:
        self._groups = group_by_category(self.app.tools)
        self._rebuild(0)
        self.query_one("#tool-list", OptionList).focus()

    # ---------------------------------------------------------------- 목록 구성
    def _is_open(self, ci: int) -> bool:
        return ci in self._open or _always_open(self._groups[ci][0])

    def _build_rows(self) -> list:
        rows = []
        for ci, (_, tools) in enumerate(self._groups):
            if ci > 0:
                rows.append((ci, DIVIDER))   # 카테고리 사이에만 (맨 위에는 없음)
            rows.append((ci, None))
            if self._is_open(ci):
                rows.extend((ci, ti) for ti in range(len(tools)))
        return rows

    def _prompt(self, row: int, highlighted: bool):
        ci, ti = self._rows[row]
        name, tools = self._groups[ci]
        if ti == DIVIDER:
            return Rule(characters=DIVIDER_CHAR, style=DIVIDER_STYLE)
        if ti is None:
            t = Text(f"{LIST_PAD}{ci + 1}. {name}", style="white")
            if not _always_open(name):   # Etc 는 표시 없이 "n. Etc" 만
                mark = MARK_OPEN if ci in self._open else MARK_CLOSED
                t.append(mark, style=DESC_STYLE_HL if highlighted else DESC_STYLE)
            return t
        tool = tools[ti]
        return _line(TOOL_PAD, f"{ti + 1}. {tool.name}", tool.description, highlighted)

    def _rebuild(self, selected: int) -> None:
        """줄 목록을 처음부터 다시 만들고 selected 번 줄을 하이라이트한다."""
        lst = self.query_one("#tool-list", OptionList)
        lst.clear_options()
        self._hl = None
        self._rows = self._build_rows()
        n = len(self._rows)
        if n:
            lst.add_options([
                Option(self._prompt(i, False), id=str(i), disabled=self._is_static(i))
                for i in range(n)
            ])
            lst.highlighted = min(max(selected, 0), n - 1)
        else:
            lst.add_option(Option(Text("  No tools found in tools/"), disabled=True))

    def _is_static(self, row: int) -> bool:
        """선택할 수 없는 줄: 구분선, 항상 펼쳐진 Etc 카테고리 줄."""
        ci, ti = self._rows[row]
        return ti == DIVIDER or (ti is None and _always_open(self._groups[ci][0]))
    
    def _toggle(self, ci: int, row: int) -> None:
        self._open.symmetric_difference_update({ci})
        self._rebuild(row)   # 카테고리 줄 위치는 그대로이므로 같은 줄에 하이라이트를 둔다

    # ---------------------------------------------------------------- 이벤트
    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """설명 줄 색은 Text 자체 색이라 CSS 하이라이트가 못 바꾼다 -> 하이라이트가 옮겨질 때 줄을 다시 그린다."""
        event.stop()
        lst = self.query_one("#tool-list", OptionList)
        n = len(self._rows)
        for idx, hl in ((self._hl, False), (event.option_index, True)):
            if idx is not None and 0 <= idx < n:
                lst.replace_option_prompt(str(idx), self._prompt(idx, hl))
        self._hl = event.option_index

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        row = event.option_index
        if not 0 <= row < len(self._rows):
            return
        ci, ti = self._rows[row]
        if ti == DIVIDER:
            return
        if ti is None:
            if not _always_open(self._groups[ci][0]):   # Etc 는 접히지 않는다
                self._toggle(ci, row)
            return
        tool = self._groups[ci][1][ti]
        if self.app.select_tool(tool):   # 새 창으로 열렸으면 홈에 안내만 잠깐 표시
            self.query_one("#status-line", StatusBar).flash(f"Opened in new window: {tool.name}")

    def on_key(self, event: events.Key) -> None:
        if is_key_for(event.key, ACTION_QUIT):
            event.stop()
            self.app.exit()
