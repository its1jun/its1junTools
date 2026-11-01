# AGENT

프로젝트 파일 트리는 ARCHITECTURE.md 참고. 이 문서는 AI/개발자가 지켜야 할 구조·규칙 문서.

## 의존 방향 (역방향 import 금지)
tools -> core <- ui
            ^      |
            +- runner <-+      (ui -> runner -> core)

- tools/ 는 core 만 import. ui, textual, runner 금지.
- core/ 는 계약 파일 (Textual 금지). 수정은 별도 작업으로 분리.
- runner.py 는 core 만 import (Textual 금지).
- ui/ 는 core, runner 를 import. 개별 tool 은 registry 경유로만 접근.
- 화면끼리 import 금지. 이동은 app.open_screen("이름", ...) 문자열로만.

## 파일 역할
main.py                  진입점. 인자 없음 = 홈 / `--tool <id> --parent-pid <pid>` = 도구 전용 새 창
registry.py              tools/ 자동 탐색 (모듈의 `tool` 변수, `_` 시작 파일 제외) + group_by_category() (홈의 카테고리 묶음/정렬)
runner.py                작업 스레드 실행 / 취소 / progress 쓰로틀 / 이벤트 전달
core/models.py           Tool, Field (순수 데이터), CATEGORY_ETC. Tool.category = 홈의 카테고리 이름
core/events.py           JobState, JobEvent
core/context.py          Context: log / progress / sleep / check_cancel / confirm
core/errors.py           CancelledError
core/logbuffer.py        LogBuffer
ui/app.py                ToolsApp, open_screen(), 도구를 새 창으로 열기/추적/종료, 부모 감시,
                         메인 종료 시 Logs 폴더 정리
ui/theme.tcss            모든 색/테두리/간격 (전체 흰색, 이중선은 제목 박스만)
ui/keymap.py             키 매핑 단일 출처
ui/defaults.py           문구 기본값 (Tool.texts 로 도구별 override)
ui/platform_utils.py     폴더 열기, 파일 선택 대화상자(pick_files_native, tkinter; 단일/다중), IME 영문 강제(force_ime_english, Windows), 새 터미널 창 열기(spawn_tool_window), 프로세스 생존 확인 등 OS 유틸
ui/screens/__init__.py   SCREENS = {"이름": 화면클래스} 등록 표
ui/screens/home.py       홈: 카테고리를 펼치고 접는 도구 목록 (화면 1개. 제목/상태줄/안내줄 고정 + 목록 스크롤)
ui/screens/form.py       도구 화면: 필드 폼 + 상태줄 + 안내줄, 실행/취소 연결
ui/screens/log.py        로그 모달 (↑/↓·마우스 휠 스크롤 / 저장 / 폴더 열기. 좌우 키 페이지 이동 없음)
ui/screens/confirm.py    ctx.confirm() 용 예/아니오 모달
ui/fields/               필드 타입 1개 = 파일 1개 (input/file/cycle/button/toggle)
ui/widgets/              status_bar, controls_bar, flash_line
tools/                   도구 1개 = 파일 1개
tools/debug.py           UI 점검용 도구 (필드 5종/진행률/로그/확인창/에러/취소). 빼려면 `_debug.py` 로 이름 변경

## 규칙
- 작업 -> UI 통신은 JobEvent 한 경로뿐 (log / progress / error / state)
- 작업 중 사용자 입력은 ctx.confirm() 하나만 허용
- 새 도구   = tools/xxx.py 1개 (`tool = Tool(...)`, `category=` 로 홈의 카테고리 지정)
- 새 카테고리 = 도구의 `category="새이름"` 만 쓰면 끝 (등록 표/코드 수정 없음)
- 새 필드   = ui/fields/xxx.py 1개 + ui/fields/__init__.py FIELD_TYPES 1줄
- 새 화면   = ui/screens/xxx.py 1개 + ui/screens/__init__.py SCREENS 1줄
- 키/문구 변경은 keymap.py / defaults.py 에서만

## 동작 규칙 (기존 프로젝트에서 유지)
- 프로그램은 사용자의 명시적 키(ESC/Q)로만 종료/이동한다. 작업이 끝나도 자동 종료 없음.
- ESC/Q: 작업 중이면 취소 / 대기 중이면 뒤로(홈) / 홈이면 종료.
- 한글은 Input 편집 중에만 입력된다: 그 외에는 IME 를 영문으로 되돌린다 (Windows).
  타이머 폴링(0.3초 등)은 쓰지 않는다. 이벤트 시점에만 1회 호출한다:
  앱 시작 / 터미널 창 포커스 복귀(AppFocus) / Input 편집 종료(_stop) / 편집 중 아닐 때 비영문 글자 입력 감지(언어 무관).
  새 폴링 타이머를 추가하지 말 것 (유휴 시 CPU/ctypes 호출 0 이 목표).
  (안 먹는 환경 대비 보조: keymap.to_latin_key 가 비영문 글자 키를 같은 위치의 영문 키로 바꿔 처리.
   1순위 OS 키보드 배열 조회(platform_utils.layout_char_to_latin, 언어 무관) / 2순위 keymap._FALLBACK_TABLES
   보조 표(IME 조합 글자용, 현재 한글). 언어별 분기/하드코딩을 늘리지 말고 표 1개만 추가할 것)
- 키보드가 기본. 필드(ui/fields)는 마우스 좌클릭 = 포커스 + ENTER (mouse=True).
- 로그 저장(S)은 세션 한정: 종료 시 Logs 폴더 삭제.

## 카테고리 (홈 화면)
- 홈은 카테고리를 펼치고 접는 목록 (시작 시 Etc 를 뺀 카테고리는 접힘, ENTER = 펼침/접기, 도구 줄 ENTER = 새 창으로 열기. Etc 는 항상 펼쳐져 있고 접히지 않음). 도구는 `Tool.category` 로 자기 카테고리를 정한다 (기본값 `Etc`).
- 현재 카테고리: Converter (형식 변환) / Downloader (내려받기) / Editor (내용 편집) / Etc (기타).
- 카테고리와 그 안의 도구는 이름순 정렬. `Etc` 만 예외로 항상 카테고리 목록 맨 아래.
- 같은 카테고리는 철자를 통일할 것 (대소문자/앞뒤 공백은 같은 그룹으로 묶이지만, `Image`/`Images` 는 다른 그룹).
- 도구 이름에는 매체를 포함한다 (예: `Image Convert`, `Video Convert`). 카테고리는 동작 기준이라 이름만으로 구분돼야 한다.
- 정렬/묶기 규칙은 registry.group_by_category 한 곳에서만 바꾼다.

## Output 폴더 (전 도구 공유) -- AI 필독
- 출력 폴더는 프로젝트 루트의 `Output/` 하나뿐이다. 모든 도구가 같이 쓴다.
- 도구는 `output_dir_name="Output"` 만 쓴다. `Debug_Output`, `<도구명>_Output` 같은 도구별 폴더명을 만들지 말 것.
- 새 도구도 `Output/` 에 저장한다. 파일명 충돌이 날 수 있으면 파일명에 도구 id 나 타임스탬프를 붙여 구분한다 (폴더를 나누지 않는다).
- `O` 키는 모든 도구에서 같은 `Output/` 폴더를 연다.

## 새 창 동작
- 홈에서 도구를 고르면 새 터미널 창에서 `main.py --tool <id> --parent-pid <메인 PID>` 가 열린다.
  새 창을 못 열면(터미널 없음/GUI 없음 등) 현재 창에서 연다.
- 도구 창에서 ESC/Q: 작업 중이면 취소 / 대기 중이면 창 닫기 (홈이 없으므로 '뒤로' 대신 종료).
- 메인이 종료되면 새 창도 닫힌다. 두 겹으로 보장한다:
  1) 메인이 on_unmount 에서 자기가 연 프로세스를 terminate
  2) 도구 창이 1초마다 parent-pid 생존을 확인하고 사라졌으면 스스로 종료
     (메인이 강제 종료/크래시되어 1)이 실행되지 못한 경우, 터미널이 프로세스를 대신 띄워서 1)이 안 먹는 경우)
- Windows 에서 os.kill(pid, 0) 은 프로세스를 죽이므로 생존 확인은 platform_utils.is_process_alive 만 쓴다.
- Logs 폴더 정리는 메인만 한다 (도구 창들이 같은 폴더를 공유하므로).
