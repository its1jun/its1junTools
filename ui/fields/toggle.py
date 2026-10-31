from ui.defaults import DEFAULT_TOGGLE_LABEL_OFF, DEFAULT_TOGGLE_LABEL_ON
from .base import FieldWidget


class ToggleField(FieldWidget):
    """Enter 로 OFF/ON 전환. 값은 현재 라벨 문자열."""
    TYPE = "toggle"

    def __init__(self, spec):
        super().__init__(spec)
        self.is_on = False

    @property
    def value(self) -> str:
        if self.is_on:
            return self.spec.label_on or DEFAULT_TOGGLE_LABEL_ON
        return self.spec.label_off or DEFAULT_TOGGLE_LABEL_OFF

    def render(self):
        return self.boxed(self.value)

    def activate(self) -> None:
        self.is_on = not self.is_on
        self.refresh()
        self.post_message(self.Changed(self))
