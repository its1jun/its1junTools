"""Textual App. 화면 등록(SCREENS)과 이동만 담당한다.

실행 모드 두 가지
- 메인 모드  : 홈(도구 선택) 화면. 도구를 고르면 새 터미널 창에서 그 도구를 연다.
- 도구 모드  : `main.py --tool <id> --parent-pid <pid>` 로 열린 새 창. 홈 없이 도구 화면만 보여주고,
               메인 프로그램(parent-pid)이 사라지면 스스로 종료해서 창이 같이 닫히게 한다.
"""
import argparse
import os
import shutil
import sys

from textual import events
from textual.app import App

from core import Tool
from ui.keymap import is_non_latin_key, to_latin_key
from ui.platform_utils import (
    CAN_FORCE_IME, force_ime_english, get_project_subdir, is_process_alive, spawn_tool_window,
)
from ui.screens import SCREENS
from ui.screens.log import LOG_DIR_NAME

PARENT_CHECK_INTERVAL = 1.0   # 도구 모드: 메인 프로그램 생존 확인 주기(초)
CHILD_EXIT_WAIT = 1.0         # 메인 종료 시 새 창 프로세스를 기다리는 최대 시간(초)


class ToolsApp(App):
    CSS_PATH = "theme.tcss"

    def __init__(self, tools: list, single_tool: Tool = None, parent_pid: int = None):
        super().__init__()
        self.tools = tools
        self.single_tool = single_tool   # 지정되면 도구 모드 (홈 없음)
        self.parent_pid = parent_pid
        self._children: list = []        # 메인이 연 새 창 프로세스들

    def on_mount(self) -> None:
        self._force_ime()   # IME 강제는 타이머 없이 이벤트로만 한다 (아래 _force_ime 설명 참고)
        if self.single_tool is None:
            self.open_screen("home")
            return
        self.title = self.single_tool.name
        self.open_screen("form", self.single_tool, standalone=True)
        if self.parent_pid:
            self.set_interval(PARENT_CHECK_INTERVAL, self._check_parent)

    def _force_ime(self) -> None:
        """한글은 Input 편집 중에만 허용: 그 외에는 IME 를 영문 상태로 유지한다.

        주기적 폴링은 하지 않는다. 다음 시점에만 1회 호출한다 (이벤트 기반):
          1) 앱 시작 직후
          2) 터미널 창이 포커스를 되찾을 때 (on_app_focus)
          3) Input 편집이 끝날 때 (ui/fields/input.py 의 _stop)
          4) 편집 중이 아닌데 비영문 글자(한글/키릴/그리스 등 언어 무관)가 들어올 때 (on_event)
             -> 그 키는 영문으로 변환 + IME 도 영문으로
        """
        if CAN_FORCE_IME and not getattr(self.focused, "editing", False):
            force_ime_english()

    def on_app_focus(self, event: events.AppFocus) -> None:
        self._force_ime()

    async def on_event(self, event: events.Event) -> None:
        """Input 편집 중이 아닐 때 비영문 글자(언어 무관)가 들어오면 같은 자판 위치의 영문 키로 바꿔 처리하고,
        동시에 IME 를 영문으로 전환한다. (변환 못 하는 글자라도 IME 전환은 시도한다)"""
        if isinstance(event, events.Key) and not getattr(self.focused, "editing", False) \
                and is_non_latin_key(event.key):
            latin = to_latin_key(event.key)
            if latin != event.key:
                event.key = latin
                event.character = latin
            self._force_ime()   # 영문이 아닌 입력 상태가 감지된 순간에만 (이후 키는 영문으로 들어온다)
        await super().on_event(event)

    def open_screen(self, name: str, *args, callback=None, **kwargs) -> None:
        """이름으로 화면을 연다. 모달 결과는 callback(result)로 받는다."""
        self.push_screen(SCREENS[name](*args, **kwargs), callback)

    def select_tool(self, tool: Tool) -> bool:
        """도구를 새 터미널 창에서 연다. 새 창을 못 열면 현재 창에서 연다. 새 창으로 열었으면 True."""
        proc = spawn_tool_window(tool.id, os.getpid())
        if proc is None:
            self.notify("Could not open a new terminal window. Opened in this window.",
                        severity="warning")
            self.open_screen("form", tool)
            return False
        self._children = [p for p in self._children if p.poll() is None]
        self._children.append(proc)
        return True

    def go_back(self) -> None:
        """도구 화면에서 ESC/Q: 도구 모드면 창을 닫고(앱 종료), 아니면 홈으로 돌아간다."""
        if self.single_tool is not None:
            self.exit()
        else:
            self.pop_screen()

    # ---------------------------------------------------------------- 새 창 수명 관리
    def _check_parent(self) -> None:
        if not is_process_alive(self.parent_pid):
            self.exit()

    def _close_child_windows(self) -> None:
        alive = [p for p in self._children if p.poll() is None]
        for p in alive:
            try:
                p.terminate()
            except Exception:
                pass
        for p in alive:
            try:
                p.wait(timeout=CHILD_EXIT_WAIT)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

    def on_unmount(self) -> None:
        self._close_child_windows()
        if self.single_tool is None:
            # 로그 저장(S)은 세션 동안만 유효한 임시 보관용 -> 메인 종료 시 Logs 폴더 정리
            # (새 창들이 같은 폴더를 공유하므로 정리는 메인만 한다)
            shutil.rmtree(get_project_subdir(LOG_DIR_NAME), ignore_errors=True)


def run() -> None:
    from registry import discover

    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", help="도구 id: 홈 없이 이 도구만 연다 (새 창 모드)")
    parser.add_argument("--parent-pid", type=int, help="이 PID 가 사라지면 종료")
    args = parser.parse_args()

    tools = discover()
    single = None
    if args.tool:
        single = next((t for t in tools if t.id == args.tool), None)
        if single is None:
            print(f"[ERROR] Unknown tool id: {args.tool}", file=sys.stderr)
            input("Press Enter to close...")
            return
    ToolsApp(tools, single, args.parent_pid).run(mouse=True)   # 필드는 마우스 좌클릭 = ENTER
