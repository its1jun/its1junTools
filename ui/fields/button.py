from ui.defaults import DEFAULT_BUTTON_LABEL
from .base import FieldWidget


class ButtonField(FieldWidget):
    TYPE = "button"
    IS_VALUE = False

    def render(self):
        return self.boxed(self.spec.label or DEFAULT_BUTTON_LABEL)

    def activate(self) -> None:
        self.post_message(self.Submit(self))
