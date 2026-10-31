import os

from ui.defaults import DEFAULT_FILE_EMPTY_TEXT
from .base import FieldWidget


class FileField(FieldWidget):
    """파일 선택 필드. spec.multi 가 False 면 값 = 경로 문자열, True 면 값 = 경로 리스트."""
    TYPE = "file"

    def __init__(self, spec):
        super().__init__(spec)
        self._paths: list = []

    @property
    def value(self):
        if self.spec.multi:
            return list(self._paths)
        return self._paths[0] if self._paths else ""

    @property
    def paths(self) -> list:
        return list(self._paths)

    def set_value(self, value) -> None:
        if isinstance(value, str):
            value = [value] if value else []
        paths = list(value)
        self._paths = paths if self.spec.multi else paths[:1]
        self.refresh()
        self.post_message(self.Changed(self))

    def render(self):
        if self._paths:
            if len(self._paths) > 1:
                return self.boxed(f"{len(self._paths)} files selected")
            first = self._paths[0]
            return self.boxed(os.path.basename(first.rstrip("/\\")) or first)
        text = self.spec.placeholder or self.spec.empty_text or DEFAULT_FILE_EMPTY_TEXT
        return self.boxed(text, dim=True)

    def activate(self) -> None:
        self.post_message(self.Browse(self))
