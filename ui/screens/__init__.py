# 화면 등록 표: 새 화면 = screens/xxx.py 1개 + 여기에 1줄.
# 화면끼리는 서로 import 하지 않고, app.open_screen("이름", ...) 으로만 이동한다.
from .confirm import ConfirmScreen
from .form import FormScreen
from .home import HomeScreen
from .log import LogScreen

SCREENS = {
    "home": HomeScreen,
    "form": FormScreen,
    "log": LogScreen,
    "confirm": ConfirmScreen,
}
