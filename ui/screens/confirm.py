"""작업 중 ctx.confirm() 이 띄우는 예/아니오 모달."""
from textual import events
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Static

from ui.keymap import ACTION_CANCEL, ACTION_ENTER, action_label, is_key_for


class ConfirmScreen(Screen[bool]):
    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self):
        with Container(id="confirm-box"):
            yield Static(self.message, id="confirm-message", markup=False)
            yield Static(
                f"[{action_label(ACTION_ENTER)}] Yes | [{action_label(ACTION_CANCEL)}] No",
                id="confirm-controls", markup=False,
            )

    def on_mount(self) -> None:
        self.query_one("#confirm-box").border_title = "CONFIRM"

    def on_key(self, event: events.Key) -> None:
        event.stop()
        event.prevent_default()
        if is_key_for(event.key, ACTION_ENTER):
            self.dismiss(True)
        elif is_key_for(event.key, ACTION_CANCEL):
            self.dismiss(False)
