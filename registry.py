"""tools/ 폴더를 탐색해 각 모듈의 `tool` 변수(core.Tool)를 수집한다."""
import importlib
import pkgutil
import sys

import tools
from core import Tool


def discover() -> list:
    found = []
    for m in sorted(pkgutil.iter_modules(tools.__path__), key=lambda x: x.name):
        if m.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"tools.{m.name}")
        except Exception as e:
            print(f"[WARNING] Skipping tools/{m.name}.py: {e}", file=sys.stderr)
            continue
        t = getattr(mod, "tool", None)
        if isinstance(t, Tool):
            found.append(t)
        else:
            print(f"[WARNING] tools/{m.name}.py has no `tool` (core.Tool)", file=sys.stderr)
    return found
