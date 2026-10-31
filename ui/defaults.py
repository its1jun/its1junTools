"""화면에 보이는 문구의 최후 기본값. 도구별 override 는 Tool.texts[키]."""
DEFAULT_FILE_EMPTY_TEXT = "Press Enter to Select File..."
DEFAULT_CYCLE_EMPTY_TEXT = "No Options Available"
DEFAULT_BUTTON_LABEL = "RUN"
DEFAULT_TOGGLE_LABEL_OFF = "OFF"
DEFAULT_TOGGLE_LABEL_ON = "ON"

DEFAULT_STATUS_READY_TEXT = "Ready"
DEFAULT_STATUS_RUNNING_TEXT = "Running"
DEFAULT_STATUS_DONE_TEXT = "Done"
DEFAULT_STATUS_CANCELLED_TEXT = "Cancelled"
DEFAULT_STATUS_CANCELLING_TEXT = "Cancelling"
DEFAULT_STATUS_ERROR_PREFIX = "Error "
DEFAULT_STATUS_TEXT_MAX_LEN = 60

# {nav_keys} {enter_key} {output_key} {logs_key} {quit_key} 자리표시자 유지할 것
DEFAULT_CONTROLS_NAV_LINE = "[{nav_keys}] Navigate Fields | [{enter_key}] Select/Run"
DEFAULT_CONTROLS_OUTPUT_ITEM = "[{output_key}] Open Output Dir"
DEFAULT_CONTROLS_LOGS_ITEM = "[{logs_key}] View Internal Logs"
DEFAULT_CONTROLS_CANCEL_LINE = "[{quit_key}] Cancel Running Task"
DEFAULT_CONTROLS_EXIT_LINE = "[{quit_key}] Back"
DEFAULT_CONTROLS_CLOSE_LINE = "[{quit_key}] Close Window"   # 도구 전용 새 창일 때

DEFAULT_TOOL_SELECTOR_TITLE = "SELECT A TOOL"


def text(tool, key: str, default):
    """tool.texts 에 key 가 있으면 그 값, 없으면 default."""
    texts = getattr(tool, "texts", None) or {}
    return texts.get(key, default)
