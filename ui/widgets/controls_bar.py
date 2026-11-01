from ui.defaults import (
    DEFAULT_CONTROLS_CANCEL_LINE, DEFAULT_CONTROLS_CLOSE_LINE, DEFAULT_CONTROLS_EXIT_LINE, DEFAULT_CONTROLS_LOGS_ITEM,
    DEFAULT_CONTROLS_NAV_LINE, DEFAULT_CONTROLS_OUTPUT_ITEM, text,
)
from ui.keymap import (
    ACTION_DOWN, ACTION_ENTER, ACTION_LEFT, ACTION_OPEN_LOGS, ACTION_OPEN_OUTPUT_DIR,
    ACTION_QUIT, ACTION_RIGHT, ACTION_UP, action_label,
)
from .flash_line import FlashLine


def build_controls_text(tool, has_output: bool, running: bool, standalone: bool = False) -> str:
    nav = text(tool, "CONTROLS_NAV_LINE", DEFAULT_CONTROLS_NAV_LINE).format(
        nav_keys=action_label(ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT),
        enter_key=action_label(ACTION_ENTER),
    )
    lines = [nav]

    parts = []
    if has_output:
        parts.append(text(tool, "CONTROLS_OUTPUT_ITEM", DEFAULT_CONTROLS_OUTPUT_ITEM)
                     .format(output_key=action_label(ACTION_OPEN_OUTPUT_DIR)))
    parts.append(text(tool, "CONTROLS_LOGS_ITEM", DEFAULT_CONTROLS_LOGS_ITEM)
                 .format(logs_key=action_label(ACTION_OPEN_LOGS)))
    lines.append(" | ".join(parts))

    quit_key = action_label(ACTION_QUIT)
    exit_default = DEFAULT_CONTROLS_CLOSE_LINE if standalone else DEFAULT_CONTROLS_EXIT_LINE
    tpl = (text(tool, "CONTROLS_CANCEL_LINE", DEFAULT_CONTROLS_CANCEL_LINE) if running
           else text(tool, "CONTROLS_EXIT_LINE", exit_default))
    lines.append(tpl.format(quit_key=quit_key))
    return "\n".join(lines)


class ControlsBar(FlashLine):
    def __init__(self, tool, has_output: bool, standalone: bool = False, **kwargs):
        super().__init__(build_controls_text(tool, has_output, False, standalone), **kwargs)
        self._tool = tool
        self._has_output = has_output
        self._standalone = standalone

    def set_running(self, running: bool) -> None:
        self.set_base(build_controls_text(self._tool, self._has_output, running, self._standalone))
