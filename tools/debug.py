"""UI 점검용 도구. 필드 5종 / 동적 옵션 / 진행률 / 로그 / 확인창 / 에러 / 취소를 한 화면에서 시험한다.

점검 방법 (각 버튼을 눌러 본다)
  PROGRESS   상태줄 스피너 + 퍼센트 + 중간 취소 (진행 중 ESC/Q -> Cancelled)
  CONFIRM    ctx.confirm() 모달 (ENTER=Yes / ESC,Q=No) -> 결과가 로그에 남는다
  ERROR      예외 -> 상태줄에 긴 에러문이 잘려서 표시, 로그에 traceback
  LOG x60    로그 60줄 -> 로그 화면(/) 페이지 이동(←/→), 저장(S)

필드 점검: 한글 기본값(전각 폭), 파일 선택(단일/다중), cycle, toggle, 의존 cycle(6 -> 7).
`/` 로그 화면, `O` 출력 폴더 열기. 목록에서 빼려면 파일 이름을 `_debug.py` 로 바꾼다.

규칙: tools/ 는 core 만 import 한다. ui / textual / runner import 금지.
"""
from core import Field, Tool


def _config_summary(config: dict) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in config.items() if k != "_pressed")


def run(config, ctx):
    pressed = config.get("_pressed")
    ctx.log(f"[DEBUG] pressed={pressed}")
    ctx.log(f"[DEBUG] config: {_config_summary(config)}")

    if pressed == "btn_progress":
        ctx.progress(None, "waiting (indeterminate)...")
        ctx.sleep(1.0)
        for i in range(1, 11):
            ctx.sleep(0.3)               # 취소되면 CancelledError
            ctx.progress(i * 10, f"step {i}/10")
        ctx.log("[DEBUG] progress demo finished")

    elif pressed == "btn_confirm":
        answer = ctx.confirm("Debug confirm: continue?")
        ctx.log(f"[DEBUG] confirm answer: {answer}")

    elif pressed == "btn_error":
        raise RuntimeError("Intentional debug error. " + "very-long-message " * 8)

    elif pressed == "btn_logs":
        for i in range(1, 61):
            ctx.log(f"[DEBUG] log line {i:02d}")
        ctx.log("[DEBUG] 60 lines written: open the log screen with '/'")

    else:
        ctx.log(f"[DEBUG] unknown button: {pressed}")


tool = Tool(
    id="debug",
    name="Debug",                # 홈 목록의 이름 줄 / 도구 창 제목
    description="UI Check",      # 홈 목록의 설명 줄 (비우면 표시 안 함)
    fields=[
        Field("text", "input", "1. Input:", default="한글 입력 Test", placeholder="type something..."),
        Field("file", "file", "2. File:", placeholder="press Enter to browse"),
        Field("files", "file", "3. Files (multi):", multi=True, placeholder="press Enter to browse"),
        [
            Field("mode", "cycle", "4. Cycle:", options=["Fast", "Balanced", "Quality"]),
            Field("flag", "toggle", "5. Toggle:", label_off="OFF", label_on="ON"),
        ],
        [
            Field("kind", "cycle", "6. Kind:", options=["Video", "Audio", "Other"]),
            Field("preset", "cycle", "7. Preset:", depends_on="kind",
                  options_map={"Video": ["1080p", "720p", "480p"],
                               "Audio": ["320k", "128k"],
                               "default": ["(none)"]}),
        ],
        [
            Field("btn_progress", "button", "PROGRESS"),
            Field("btn_confirm", "button", "CONFIRM"),
        ],
        [
            Field("btn_error", "button", "ERROR"),
            Field("btn_logs", "button", "LOG x60"),
        ],
    ],
    run=run,
    category="Etc",                 # 홈의 카테고리 (Converter / Editor / Downloader / Etc)
    output_dir_name="Output",       # 모든 도구가 공유하는 폴더 (AGENT.md 참고),
    texts={"STATUS_READY_TEXT": "Ready (debug)"},
)
