"""프로젝트 전체 키 매핑의 유일한 출처. 키를 바꾸려면 이 파일만 고친다."""
from typing import Dict, Optional, Tuple

from ui.platform_utils import layout_char_to_latin

ACTION_QUIT = "quit"                # 종료 / 작업 취소 / 뒤로
ACTION_CANCEL = "cancel"            # 모달 취소
ACTION_CLOSE = "close"              # 로그 화면 닫기
ACTION_ENTER = "enter"
ACTION_OPEN_LOGS = "open_logs"
ACTION_OPEN_OUTPUT_DIR = "open_output_dir"
ACTION_TAB = "tab"
ACTION_UP = "up"
ACTION_DOWN = "down"
ACTION_LEFT = "left"
ACTION_RIGHT = "right"
ACTION_SAVE_LOG = "save_log"

KEYMAP: Dict[str, Tuple[str, ...]] = {
    ACTION_QUIT: ("escape", "q"),
    ACTION_CANCEL: ("escape", "q"),
    ACTION_CLOSE: ("escape", "q", "slash"),
    ACTION_ENTER: ("enter", "return"),
    ACTION_OPEN_LOGS: ("slash",),
    ACTION_OPEN_OUTPUT_DIR: ("o",),
    ACTION_TAB: ("tab",),
    ACTION_UP: ("up",),
    ACTION_DOWN: ("down",),
    ACTION_LEFT: ("left",),
    ACTION_RIGHT: ("right",),
    ACTION_SAVE_LOG: ("s",),
}

DIRECTION_ACTIONS = (ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT)
DIRECTION_DELTA = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}

_KEY_LABELS = {
    "escape": "ESC", "enter": "ENTER", "return": "ENTER", "slash": "/",
    "up": "↑", "down": "↓", "left": "←", "right": "→", "tab": "TAB",
}


def keys_for(action: str) -> Tuple[str, ...]:
    return KEYMAP[action]


def is_key_for(event_key: str, action: str) -> bool:
    return event_key in KEYMAP[action]


def action_for_key(event_key: str, candidates: Tuple[str, ...]) -> Optional[str]:
    for action in candidates:
        if event_key in KEYMAP[action]:
            return action
    return None


def key_label(*key_groups: Tuple[str, ...]) -> str:
    seen = []
    for group in key_groups:
        for key in group:
            label = _KEY_LABELS.get(key, key.upper())
            if label not in seen:
                seen.append(label)
    return "/".join(seen)


def action_label(*actions: str) -> str:
    return key_label(*(keys_for(a) for a in actions))


# 비영문 글자 -> 같은 위치의 영문 키. IME/자판이 영문이 아니어도 단축키(Q/O/S 등)가 먹게 한다.
# (Input 필드 편집 중에는 적용하지 않는다: ui/app.py)
# 1순위: OS 키보드 배열에서 동적으로 계산 (platform_utils.layout_char_to_latin) -> 언어 제한 없음
# 2순위: 배열에 없는 IME 조합 글자용 보조 표 (_FALLBACK_TABLES). 언어를 늘리려면 표 1개만 추가한다.
_HANGUL_TO_LATIN = {   # 한글 2벌식 (IME 가 자모를 직접 만들어서 배열 조회가 안 될 수 있음)
    "ㅂ": "q", "ㅈ": "w", "ㄷ": "e", "ㄱ": "r", "ㅅ": "t", "ㅛ": "y", "ㅕ": "u", "ㅑ": "i", "ㅐ": "o", "ㅔ": "p",
    "ㅁ": "a", "ㄴ": "s", "ㅇ": "d", "ㄹ": "f", "ㅎ": "g", "ㅗ": "h", "ㅓ": "j", "ㅏ": "k", "ㅣ": "l",
    "ㅋ": "z", "ㅌ": "x", "ㅊ": "c", "ㅍ": "v", "ㅠ": "b", "ㅜ": "n", "ㅡ": "m",
    # Shift 를 누른 쌍자음/이중모음 (나머지는 Shift 여부와 글자가 같다)
    "ㅃ": "Q", "ㅉ": "W", "ㄸ": "E", "ㄲ": "R", "ㅆ": "T", "ㅒ": "O", "ㅖ": "P",
}
_FALLBACK_TABLES = (_HANGUL_TO_LATIN,)


def is_non_latin_key(key: str) -> bool:
    """한 글자짜리 비ASCII 키인가 (= 영문이 아닌 입력 상태에서 들어온 글자)."""
    return len(key) == 1 and not key.isascii()


def to_latin_key(key: str) -> str:
    """비영문 글자 키면 같은 위치의 영문 키로, 아니면(또는 못 찾으면) 그대로."""
    if not is_non_latin_key(key):
        return key
    latin = layout_char_to_latin(key)
    if latin:
        return latin
    for table in _FALLBACK_TABLES:
        if key in table:
            return table[key]
    return key
