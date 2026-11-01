"""도구 정의용 순수 데이터. (Textual import 금지)"""
from dataclasses import dataclass, field
from typing import Callable, Optional


CATEGORY_ETC = "Etc"   # 분류 없음. 홈의 카테고리 목록에서 항상 맨 아래에 놓인다


@dataclass
class Field:
    key: str
    type: str = "input"        # "input" | "file" | "cycle" | "button" | "toggle"
    label: str = ""
    default: str = ""          # input 초기값
    placeholder: str = ""      # 값이 없을 때 회색으로 보이는 안내문
    empty_text: str = ""       # file/cycle: 값도 placeholder도 없을 때 문구
    options: list = field(default_factory=list)       # cycle 정적 옵션
    depends_on: Optional[str] = None                  # cycle 동적: 기준 필드 key
    options_map: dict = field(default_factory=dict)   # {기준값: [옵션]}, "default" 키 허용
    label_off: str = ""        # toggle
    label_on: str = ""         # toggle
    multi: bool = False        # file: True면 여러 파일 선택 (값 = 경로 리스트), False면 1개 (값 = 경로 문자열)


@dataclass
class Tool:
    id: str
    name: str
    description: str = ""
    # Field 하나 = 한 줄, [Field, Field] = 한 줄에 2개 (3개 이상이면 2개씩 자동 줄바꿈)
    fields: list = field(default_factory=list)
    # run(config: dict, ctx: Context). config = {key: 값} + "_pressed": 눌린 버튼 key
    run: Optional[Callable] = None
    run_label: str = ""                 # 자동 추가되는 실행 버튼 문구 (button 필드가 없을 때)
    allowed_ext: tuple = ()             # 파일 선택 대화상자 확장자 필터 (이 도구의 모든 file 필드), 예: (".mp4",)
    output_dir_name: Optional[str] = None   # 지정하면 O 키로 이 폴더를 연다. 값은 항상 "Output" (전 도구 공유)
    # 이 도구만의 문구 override. 키 목록은 ui/defaults.py 의 이름과 동일
    # (STATUS_READY_TEXT, STATUS_RUNNING_TEXT, STATUS_ERROR_PREFIX, STATUS_CANCELLING_TEXT,
    #  STATUS_DONE_TEXT, STATUS_CANCELLED_TEXT, STATUS_TEXT_MAX_LEN, CONTROLS_*)
    texts: dict = field(default_factory=dict)
    # 홈의 카테고리 이름. 새 카테고리 = 여기에 새 이름을 쓰기만 하면 된다 (별도 등록 없음).
    # 예: "Converter" / "Editor" / "Downloader" / "Etc". 대소문자·앞뒤 공백은 무시하고 같은 그룹으로 묶는다.
    category: str = CATEGORY_ETC
