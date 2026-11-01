# ARCHITECTURE

프로젝트 트리 구조. 역할/규칙/동작 설명은 [AGENT.md](AGENT.md) 참고.

```
its1junTools/
├── main.py                 진입점 (홈 / --tool <id> --parent-pid <pid>)
├── registry.py             tools/ 자동 탐색
├── runner.py               작업 스레드 실행 / 취소 / 이벤트 전달
├── AGENT.md                구조·규칙 문서 (AI 필독)
├── ARCHITECTURE.md         트리 구조 (이 파일)
│
├── core/                   계약 파일 (Textual 금지)
│   ├── __init__.py
│   ├── models.py           Tool, Field
│   ├── events.py           JobState, JobEvent
│   ├── context.py          Context (log / progress / sleep / check_cancel / confirm)
│   ├── errors.py           CancelledError
│   └── logbuffer.py        LogBuffer
│
├── tools/                  도구 1개 = 파일 1개
│   ├── __init__.py
│   ├── _template.py        새 도구 템플릿 (`_` 시작 = 탐색 제외)
│   └── debug.py            UI 점검용 도구
│
└── ui/                     Textual UI
    ├── __init__.py
    ├── app.py              ToolsApp, open_screen(), 새 창 관리
    ├── keymap.py           키 매핑 단일 출처
    ├── defaults.py         문구 기본값
    ├── platform_utils.py   OS 유틸 (폴더 열기, 파일 선택, IME, 새 창)
    ├── theme.tcss          색 / 테두리 / 간격
    │
    ├── screens/            화면
    │   ├── __init__.py     SCREENS 등록 표
    │   ├── home.py         도구 선택
    │   ├── form.py         도구 화면 (필드 폼)
    │   ├── log.py          로그 모달
    │   └── confirm.py      예/아니오 모달
    │
    ├── fields/             필드 타입 1개 = 파일 1개
    │   ├── __init__.py     FIELD_TYPES 등록
    │   ├── base.py
    │   ├── input.py
    │   ├── file.py
    │   ├── cycle.py
    │   ├── toggle.py
    │   └── button.py
    │
    └── widgets/            공용 위젯
        ├── __init__.py
        ├── status_bar.py
        ├── controls_bar.py
        └── flash_line.py
```

## 런타임 생성 폴더 (저장소에는 없음)
- `Output/` 전 도구 공유 출력 폴더
- `Logs/` 로그 저장 폴더 (메인 종료 시 삭제)
