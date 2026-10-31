from ui.defaults import DEFAULT_CYCLE_EMPTY_TEXT
from .base import FieldWidget


class CycleField(FieldWidget):
    TYPE = "cycle"

    def __init__(self, spec):
        super().__init__(spec)
        self.options = list(spec.options)
        self.idx = 0

    @property
    def value(self) -> str:
        if self.options and 0 <= self.idx < len(self.options):
            return self.options[self.idx]
        return ""

    def render(self):
        if self.options:
            return self.boxed(self.value)
        text = self.spec.placeholder or self.spec.empty_text or DEFAULT_CYCLE_EMPTY_TEXT
        return self.boxed(text, dim=True)

    def activate(self) -> None:
        if self.options:
            self.idx = (self.idx + 1) % len(self.options)
            self.refresh()
            self.post_message(self.Changed(self))

    def apply_dependency(self, source_value) -> bool:
        """depends_on 필드의 현재 값으로 옵션을 다시 계산. 값이 바뀌었으면 True."""
        spec = self.spec
        if not (spec.depends_on and spec.options_map):
            return False
        new = list(spec.options_map.get(source_value, spec.options_map.get("default", [])))
        old = self.value
        self.options = new
        self.idx = new.index(old) if old in new else 0
        self.refresh()
        return self.value != old
