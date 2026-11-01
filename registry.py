"""tools/ 폴더를 탐색해 각 모듈의 `tool` 변수(core.Tool)를 수집한다."""
import importlib
import pkgutil
import sys

import tools
from core import CATEGORY_ETC, Tool


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


def group_by_category(tools: list) -> list:
    """도구를 카테고리별로 묶는다 -> [(카테고리 이름, [Tool, ...]), ...].

    카테고리와 그 안의 도구는 모두 이름순(대소문자 무시). Etc(CATEGORY_ETC)만 예외로 항상 맨 아래.
    category 가 비어 있으면 Etc 로 본다. 표시 이름은 처음 등장한 철자를 쓴다.
    """
    groups = {}   # 정규화한 이름 -> [표시 이름, [Tool, ...]]
    for t in tools:
        name = (t.category or "").strip() or CATEGORY_ETC
        groups.setdefault(name.casefold(), [name, []])[1].append(t)
    etc = CATEGORY_ETC.casefold()
    keys = sorted(groups, key=lambda k: (k == etc, k))
    return [(groups[k][0], sorted(groups[k][1], key=lambda t: t.name.casefold())) for k in keys]
