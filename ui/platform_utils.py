import os
import platform
import shlex
import shutil
import subprocess
import sys
from typing import Optional

_SYSTEM = platform.system()


def _project_root() -> str:
    ui_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(ui_dir)


def get_project_subdir(name: str) -> str:
    """프로젝트 루트(ui/ 의 상위 폴더) 기준 하위 폴더 경로. 생성은 호출부 책임."""
    return os.path.join(_project_root(), name)


def open_in_explorer(path: str) -> bool:
    try:
        if _SYSTEM == "Windows":
            os.startfile(path)
        elif _SYSTEM == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- 파일 선택 대화상자
# tkinter 를 별도 프로세스로 띄운다 (TUI 이벤트 루프와 분리, 창 안 얼음). 결과는 stdout(UTF-8, 줄바꿈 구분)으로 받는다.
_PICK_SCRIPT = r"""
import sys
import tkinter as tk
from tkinter import filedialog

multi, start, title = sys.argv[1] == "multi", sys.argv[2], sys.argv[3]
exts = sys.argv[4:]
root = tk.Tk()
root.attributes("-topmost", True)
root.withdraw()
types = [("All Files", "*.*")]
if exts:
    types.insert(0, ("Allowed Files", " ".join("*" + e for e in exts)))
ask = filedialog.askopenfilenames if multi else filedialog.askopenfilename
result = ask(title=title, initialdir=start, filetypes=types, parent=root)
if isinstance(result, str):   # 단일 선택 / 일부 Tk 버전의 다중 선택 문자열 결과
    result = root.tk.splitlist(result) if multi else ([result] if result else [])
root.destroy()
sys.stdout.buffer.write("\n".join(result).encode("utf-8"))
"""


def pick_files_native(start_dir: str, allowed_ext: tuple = (), multi: bool = False):
    """OS 기본 파일 선택 대화상자 (tkinter.filedialog). 블로킹이므로 워커 스레드에서 호출할 것.

    반환: (성공 여부, 경로 리스트). 사용자가 취소하면 (True, []), 대화상자를 못 열면 (False, []).
    multi=False 이면 리스트 길이는 최대 1.
    """
    title = "Select Files" if multi else "Select File"
    start = start_dir if os.path.isdir(start_dir) else os.path.expanduser("~")
    cmd = [sys.executable, "-c", _PICK_SCRIPT, "multi" if multi else "single", start, title, *allowed_ext]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=env)
    except Exception:
        return False, []
    if proc.returncode != 0:
        return False, []   # tkinter 없음 등
    out = proc.stdout.decode("utf-8", errors="replace")
    return True, [os.path.normpath(line) for line in out.split("\n") if line.strip()]


# ---------------------------------------------------------------- IME (Windows)
CAN_FORCE_IME = _SYSTEM == "Windows"
_IME_API = None


def _load_ime_api():
    """user32 / imm32 / kernel32 함수를 한 번만 로드해서 시그니처를 지정한다 (64비트 핸들 대응)."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32")
    imm32 = ctypes.WinDLL("imm32")
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.GetConsoleWindow.restype = wintypes.HWND
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    imm32.ImmGetDefaultIMEWnd.argtypes = [wintypes.HWND]
    imm32.ImmGetDefaultIMEWnd.restype = wintypes.HWND
    user32.SendMessageTimeoutW.argtypes = [
        wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
        wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t),
    ]
    user32.SendMessageTimeoutW.restype = wintypes.LPARAM
    return ctypes, user32, imm32, kernel32


def force_ime_english() -> None:
    """이 터미널 창이 맨 앞일 때, IME 가 한글(열림) 상태면 영문(닫힘)으로 바꾼다.

    Windows 전용, 그 외 OS 에서는 아무것도 안 한다. 실패해도 조용히 무시한다.
    (다른 프로그램의 IME 를 건드리지 않도록 맨 앞 창이 이 터미널일 때만 동작)
    """
    global _IME_API
    if not CAN_FORCE_IME:
        return
    try:
        if _IME_API is None:
            _IME_API = _load_ime_api()
        ctypes, user32, imm32, kernel32 = _IME_API
        console = kernel32.GetConsoleWindow()
        if not console:
            return
        foreground = user32.GetForegroundWindow()
        # conhost 는 콘솔 창 자체가, Windows Terminal 은 콘솔 창의 최상위 소유자가 맨 앞 창이다
        if not foreground or foreground not in (console, user32.GetAncestor(console, 3)):   # 3 = GA_ROOTOWNER
            return
        ime = imm32.ImmGetDefaultIMEWnd(foreground)
        if not ime:
            return
        WM_IME_CONTROL, IMC_GETOPENSTATUS, IMC_SETOPENSTATUS, SMTO_ABORTIFHUNG = 0x0283, 0x0005, 0x0006, 0x0002
        result = ctypes.c_size_t(0)
        if user32.SendMessageTimeoutW(ime, WM_IME_CONTROL, IMC_GETOPENSTATUS, 0,
                                      SMTO_ABORTIFHUNG, 100, ctypes.byref(result)) and result.value:
            user32.SendMessageTimeoutW(ime, WM_IME_CONTROL, IMC_SETOPENSTATUS, 0,
                                       SMTO_ABORTIFHUNG, 100, ctypes.byref(result))
    except Exception:
        pass


# ---------------------------------------------------------------- 키보드 배열 기반 문자 -> 영문 변환 (Windows)
_LAYOUT_API = None
_VK_OEM_2 = 0xBF   # US 배열의 '/' 키 위치


def _load_layout_api():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32")
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetKeyboardLayout.argtypes = [wintypes.DWORD]
    user32.GetKeyboardLayout.restype = ctypes.c_void_p
    user32.VkKeyScanExW.argtypes = [wintypes.WCHAR, ctypes.c_void_p]
    user32.VkKeyScanExW.restype = ctypes.c_short
    return ctypes, wintypes, user32


def layout_char_to_latin(ch: str) -> Optional[str]:
    """현재 키보드 배열에서 ch 를 만드는 물리 키를 찾아, 그 키 위치의 영문(US 배열) 문자를 돌려준다.

    언어별 표를 두지 않고 OS 의 키보드 배열 정보를 그대로 쓴다 (러시아어/그리스어/아랍어/히브리어 등).
    Windows 전용. 못 찾거나 다른 OS 면 None. 영문자(a-z)/숫자/'/' 키만 변환한다 (단축키용).
    한글/일본어/중국어처럼 IME 가 만드는 글자는 배열에 없어 None 이 될 수 있다 -> keymap 의 보조 표가 처리.
    """
    global _LAYOUT_API
    if _SYSTEM != "Windows" or len(ch) != 1:
        return None
    try:
        if _LAYOUT_API is None:
            _LAYOUT_API = _load_layout_api()
        ctypes, wintypes, user32 = _LAYOUT_API
        thread = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
        scan = user32.VkKeyScanExW(ch, user32.GetKeyboardLayout(thread))
        if scan == -1:
            return None
        vk, shift = scan & 0xFF, bool(scan & 0x100)
        if 0x41 <= vk <= 0x5A:   # A-Z
            return chr(vk) if shift else chr(vk).lower()
        if 0x30 <= vk <= 0x39 and not shift:   # 0-9
            return chr(vk)
        if vk == _VK_OEM_2 and not shift:
            return "/"
    except Exception:
        pass
    return None


# ---------------------------------------------------------------- 프로세스 생존 확인
def is_process_alive(pid: int) -> bool:
    """pid 프로세스가 살아 있는지. (Windows 에서 os.kill(pid, 0) 은 프로세스를 죽이므로 쓰지 않는다.)"""
    if not pid or pid <= 0:
        return False
    if _SYSTEM == "Windows":
        import ctypes
        from ctypes import wintypes

        SYNCHRONIZE = 0x00100000
        WAIT_TIMEOUT = 0x00000102
        ERROR_ACCESS_DENIED = 5
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k32.WaitForSingleObject.restype = wintypes.DWORD
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = k32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            return ctypes.get_last_error() == ERROR_ACCESS_DENIED   # 접근 거부 = 존재는 함
        try:
            return k32.WaitForSingleObject(handle, 0) == WAIT_TIMEOUT
        finally:
            k32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


# ---------------------------------------------------------------- 새 터미널 창
# (실행파일, 명령 앞에 붙는 인자). 위에서부터 PATH 에 있는 첫 번째를 사용한다.
_LINUX_TERMINALS = (
    ("gnome-terminal", ["--"]),
    ("konsole", ["-e"]),
    ("xfce4-terminal", ["-x"]),
    ("kitty", []),
    ("alacritty", ["-e"]),
    ("xterm", ["-e"]),
    ("x-terminal-emulator", ["-e"]),
)


def _applescript_quote(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def spawn_tool_window(tool_id: str, parent_pid: int) -> Optional[subprocess.Popen]:
    """새 터미널 창에서 `main.py --tool <id>` 를 실행한다. 창을 못 열면 None.

    새 창 프로세스는 parent_pid(= 메인 프로그램)가 사라지면 스스로 종료한다 (ui/app.py).
    """
    root = _project_root()
    cmd = [sys.executable, os.path.join(root, "main.py"),
           "--tool", tool_id, "--parent-pid", str(parent_pid)]
    try:
        if _SYSTEM == "Windows":
            # 표준 입출력을 리다이렉트하면 새 콘솔의 TUI 가 깨지므로 하지 않는다.
            return subprocess.Popen(cmd, cwd=root, creationflags=subprocess.CREATE_NEW_CONSOLE)

        quiet = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)

        if _SYSTEM == "Darwin":
            shell_cmd = f"cd {shlex.quote(root)} && {shlex.join(cmd)}; exit"
            script = ('tell application "Terminal"\n'
                      "activate\n"
                      f'do script "{_applescript_quote(shell_cmd)}"\n'
                      "end tell")
            return subprocess.Popen(["osascript", "-e", script], **quiet)

        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            return None
        for exe, prefix in _LINUX_TERMINALS:
            path = shutil.which(exe)
            if path:
                return subprocess.Popen([path, *prefix, *cmd], cwd=root, **quiet)
        return None
    except Exception:
        return None
