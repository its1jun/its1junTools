from core import Field
from .base import FieldWidget
from .button import ButtonField
from .cycle import CycleField
from .file import FileField
from .input import InputField
from .toggle import ToggleField

# 새 필드 타입 = fields/xxx.py 1개 + 여기에 1줄
FIELD_TYPES = {
    "input": InputField,
    "file": FileField,
    "cycle": CycleField,
    "button": ButtonField,
    "toggle": ToggleField,
}


def create_field(spec: Field) -> FieldWidget:
    cls = FIELD_TYPES.get(spec.type)
    if cls is None:
        return ButtonField(Field(key=f"error-{spec.key}", type="button",
                                 label=f"[UNKNOWN TYPE: {spec.type}]"))
    return cls(spec)
