from textual.widgets import Static


class FlashLine(Static):
    """기본 텍스트를 보여주다가, flash()로 잠깐 다른 메시지를 보이고 원복하는 한 줄/여러 줄."""

    def __init__(self, text: str = "", **kwargs):
        super().__init__(text, markup=False, **kwargs)
        self._base = text
        self._timer = None

    def set_base(self, text: str) -> None:
        self._base = text
        if self._timer is None:
            self.update(text)

    def flash(self, message: str, duration: float = 2.0) -> None:
        if self._timer is not None:
            self._timer.stop()
        self.update(message)
        self._timer = self.set_timer(duration, self._restore)

    def _restore(self) -> None:
        self._timer = None
        self.update(self._base)
